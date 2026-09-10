"""
DesignAdvisor · 飞书 bot webhook 路由(Phase 0 #4 飞书 bot 闭环)

FastAPI 路由:
- POST /api/v1/bot/webhook   飞书事件回调(URL 验签 + 消息接收 + 异步回消息)
- GET  /api/v1/bot/health    健康检查(支持 dry_run 检测 / 路径就位)

触发链:
  飞书 server  → POST /api/v1/bot/webhook
                → bot.signature.verify(body, headers)  ← HMAC-SHA256 验签
                → parse 事件 → 提取 message_text + chat_id + sender
                → search_handler.dispatch(message_text)  ← 放线程池,避免自死锁
                → lark_client.send_text(chat_id, reply)
                → 200 OK(飞书要求 5s 内回 200,业务用 lark_client.send_text 异步回)

注意:search_handler 内部用 urllib 同步调本机后端(127.0.0.1:8000),
uvicorn 单进程单线程下,webhook handler 在事件循环里同步自调会死锁,
所以用 starlette.concurrency.run_in_threadpool 把 dispatch 包成线程调用。

不做什么(留待 Phase 1):
- 私聊 vs 群消息区分(本轮统一入口,都走 search_handler.dispatch)
- 消息去重(同 message_id 重发检测,留待 Phase 1 切真发后)

命中日志(0911 新增):每条 webhook 落 1 行 JSONL 到 ./data/bot_hit_log.jsonl(env-gated),
纯本地不上报,失败不阻塞主流程;为 5 设计师 dogfood 验收做审计面。
"""

from __future__ import annotations

import os
import re
import time
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from bot.search_handler import dispatch
from bot.lark_client import send_text, _dry_run
from bot.signature import SignatureConfig, SignatureError, verify as verify_signature
from bot.ratelimit import RateLimitConfig, RateLimiter, get_default_limiter
from bot.hit_log import HitLogConfig, get_default_hitlog

router = APIRouter(prefix="/api/v1/bot", tags=["bot"])


# 命中数 best-effort 解析(reply 形如 "🎨 资产库 · button · 5 命中 ...")
_HIT_RE = re.compile(r"·\s*(\d+)\s*命中")


def _parse_hit_count(reply: Optional[str]) -> Optional[int]:
    """从 reply 文本里 best-effort 解析命中数,失败返回 None。"""
    if not reply:
        return None
    m = _HIT_RE.search(reply)
    return int(m.group(1)) if m else None


def _record_hit(
    *,
    chat_id: Optional[str],
    sender: Optional[str],
    text: str,
    ok: bool,
    note: str,
    echo: Optional[str] = None,
    reply: Optional[str] = None,
    dry_run: bool,
    event_type: Optional[str] = None,
    t0: float,
) -> None:
    """集中打命中日志(失败不阻塞主流程,纯本地不上报)。

    字段:ts / chat_id / sender / text / ok / note / echo / reply_len / dry_run / event_type
    隐含字段(从 reply 提取):hit=N(便于事后 grep "5 设计师问了几次"等)
    隐含字段(从 t0 算):latency_ms(整条 webhook 处理耗时,毫秒)
    """
    cfg = HitLogConfig.from_env()
    if not cfg.enabled:
        return
    hit_count = _parse_hit_count(reply)
    extra_note = note
    if hit_count is not None:
        extra_note = f"{note} hit={hit_count}"
    extra_note = f"{extra_note} latency_ms={int((time.monotonic() - t0) * 1000)}"
    log = get_default_hitlog(cfg)
    log.record(log.now_event(
        chat_id=chat_id or None,
        sender=sender,
        text=text or "",
        ok=ok,
        note=extra_note,
        echo=echo,
        reply_len=len(reply) if reply else 0,
        dry_run=dry_run,
        event_type=event_type,
    ))


class WebhookResponse(BaseModel):
    ok: bool
    echo: Optional[str] = None
    reply_preview: Optional[str] = None
    dry_run: bool
    note: str = ""


class HealthResponse(BaseModel):
    status: str
    module: str
    version: str
    dry_run: bool
    lark_bin: str
    lark_profile: str
    signature_enabled: bool
    rate_limit_enabled: bool
    rate_limit_rps: float
    rate_limit_burst: float
    rate_limit_active_chats: int
    hit_log_enabled: bool
    note: str = ""


def _extract_message(payload: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """从飞书事件 payload 提取 message_text / chat_id / sender。

    兼容两种飞书 schema:
    - 旧版 v1: payload.event.message.text + chat_id
    - 新版 v2: payload.header.event_type + payload.event.message.chat_id

    返回:{"text": str|None, "chat_id": str|None, "sender": str|None, "event_type": str|None}
    """
    text: Optional[str] = None
    chat_id: Optional[str] = None
    sender: Optional[str] = None
    event_type: Optional[str] = None

    # v2 风格(payload.header.event_type)
    header = payload.get("header") or {}
    event_type = header.get("event_type")

    event = payload.get("event") or {}
    msg = event.get("message") or {}
    sender_obj = event.get("sender") or {}

    # 文本可能在 message.content.text(JSON 字符串)或 message.text
    content = msg.get("content")
    if isinstance(content, dict):
        text = content.get("text")
    elif isinstance(content, str):
        text = content
    if not text:
        text = msg.get("text")

    chat_id = msg.get("chat_id")
    sender = sender_obj.get("sender_id", {}).get("open_id") if isinstance(sender_obj, dict) else None

    return {
        "text": text,
        "chat_id": chat_id,
        "sender": sender,
        "event_type": event_type or payload.get("type"),
    }


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="飞书 bot 健康检查",
)
def health() -> HealthResponse:
    sig_cfg = SignatureConfig.from_env()
    rl_cfg = RateLimitConfig.from_env()
    rl_stats = get_default_limiter(rl_cfg).stats()
    hit_cfg = HitLogConfig.from_env()
    return HealthResponse(
        status="ok",
        module="bot",
        version="0.4.1",
        dry_run=_dry_run(),
        lark_bin=os.getenv("LARK_CLI_BIN", "lark-cli"),
        lark_profile=os.getenv("LARK_PROFILE", "design"),
        signature_enabled=sig_cfg.enabled,
        rate_limit_enabled=rl_cfg.enabled,
        rate_limit_rps=rl_cfg.rps,
        rate_limit_burst=rl_cfg.burst,
        rate_limit_active_chats=rl_stats["active_chat_ids"],
        hit_log_enabled=hit_cfg.enabled,
        note=(
            "Phase 0 #4 飞书 bot 雏形闭环"
            + (" · dry_run=1(默认,只 print 不真发)" if _dry_run() else " · dry_run=0(真发,谨慎)")
            + (
                " · signature=on(已配 FEISHU_BOT_VERIFY_TOKEN,webhook 验签生效)"
                if sig_cfg.enabled
                else " · signature=off(未配 FEISHU_BOT_VERIFY_TOKEN,跳过验签,本地 dry_run 友好)"
            )
            + (
                f" · ratelimit=on(rps={rl_cfg.rps},burst={rl_cfg.burst},每 chat_id 独立 token bucket)"
                if rl_cfg.enabled
                else " · ratelimit=off(未启用,流量大时建议开启)"
            )
            + (
                f" · hitlog=on({hit_cfg.path},纯本地 JSONL,狗粮 dogfood 审计面)"
                if hit_cfg.enabled
                else " · hitlog=off(未启用,5 设计师 dogfood 时建议开启)"
            )
        ),
    )


@router.post(
    "/webhook",
    response_model=WebhookResponse,
    summary="飞书事件回调",
    responses={
        200: {"description": "正常处理 / dry_run 模式"},
        401: {"description": "URL 验签失败"},
    },
)
async def webhook(request: Request) -> WebhookResponse:
    """飞书事件回调入口。

    1. 读 raw body + headers(验签需要原始 bytes,不能先 await request.json)
    2. bot.signature.verify(body, X-Lark-Signature/...) HMAC-SHA256 验签
       失败 → 返回 401 SignatureError(注:FastAPI 仍走 200,业务层面 ok=False 标记)
    3. 解析 message_text / chat_id(飞书 v2 schema:header.event_type + event.message)
    4. search_handler.dispatch(message_text) 算出 reply
    5. lark_client.send_text(chat_id, reply) 同步发(超时风险由 send_text 内部 10s 兜底)
    6. 返回 200(飞书 5s 内要求回 200,这里就是同步发,5s 内能完成;流量大后改异步)

    验签策略:
    - 未配 FEISHU_BOT_VERIFY_TOKEN → 静默跳过(向后兼容 dry_run / 本地 curl 干跑)
    - 已配 → 严格校验 timestamp 偏移 + HMAC-SHA256 签名
    - 验签失败 → WebhookResponse(ok=False, note="signature failed: <reason>")

    命中日志(0911 新增):每个 return 前调 _record_hit,env-gated,纯本地不上报。
    """
    t0 = time.monotonic()
    dry_run = _dry_run()

    # 1) 读 raw body(验签需要 bytes)
    body_bytes = await request.body()

    # 2) URL 验签(读 env 一次,每次请求都重新构造以便 env 改动即时生效)
    sig_cfg = SignatureConfig.from_env()
    if sig_cfg.enabled:
        sig_b64 = request.headers.get("X-Lark-Signature", "")
        ts = request.headers.get("X-Lark-Request-Timestamp", "")
        nonce = request.headers.get("X-Lark-Request-Nonce", "")
        try:
            verify_signature(body_bytes, sig_b64, ts, nonce, sig_cfg)
        except SignatureError as e:
            resp = WebhookResponse(
                ok=False,
                dry_run=dry_run,
                note=f"signature failed: {e.reason}",
            )
            _record_hit(
                chat_id=None, sender=None, text="",
                ok=False, note=f"sig=deny reason={e.reason}",
                dry_run=dry_run, event_type=None, t0=t0,
            )
            return resp

    # 3) 解析 JSON body
    try:
        import json
        payload = json.loads(body_bytes) if body_bytes else {}
    except Exception:
        resp = WebhookResponse(
            ok=False,
            dry_run=dry_run,
            note="invalid json body",
        )
        _record_hit(
            chat_id=None, sender=None, text="",
            ok=False, note="parse=invalid_json",
            dry_run=dry_run, event_type=None, t0=t0,
        )
        return resp

    if not isinstance(payload, dict):
        resp = WebhookResponse(
            ok=False,
            dry_run=dry_run,
            note="payload is not a dict",
        )
        _record_hit(
            chat_id=None, sender=None, text="",
            ok=False, note="parse=not_dict",
            dry_run=dry_run, event_type=None, t0=t0,
        )
        return resp

    msg = _extract_message(payload)
    text = msg["text"] or ""
    chat_id = msg["chat_id"] or ""

    if not text:
        resp = WebhookResponse(
            ok=True,
            dry_run=dry_run,
            note=f"no text in event (event_type={msg['event_type']})",
        )
        _record_hit(
            chat_id=chat_id or None, sender=msg.get("sender"),
            text="", ok=True, note="empty_text",
            dry_run=dry_run, event_type=msg.get("event_type"), t0=t0,
        )
        return resp

    if not chat_id:
        # 测试 / 调试用:支持 query 传 chat_id(便于 curl 干跑)
        chat_id = request.query_params.get("chat_id", "")

    # 限流(每 chat_id 独立 token bucket,超限直接拒,不进业务分发)
    rl_cfg = RateLimitConfig.from_env()
    if rl_cfg.enabled and chat_id:
        limiter = get_default_limiter(rl_cfg)
        allowed, retry_after = await run_in_threadpool(limiter.acquire, chat_id)
        if not allowed:
            resp = WebhookResponse(
                ok=False,
                echo=text,
                dry_run=dry_run,
                note=f"rate limited: retry after {retry_after:.1f}s (rps={rl_cfg.rps}, burst={rl_cfg.burst})",
            )
            _record_hit(
                chat_id=chat_id or None, sender=msg.get("sender"),
                text=text, ok=False, echo=text,
                note=f"ratelimit=deny retry={retry_after:.1f}s",
                dry_run=dry_run, event_type=msg.get("event_type"), t0=t0,
            )
            return resp

    # 业务分发(放线程池,避免单线程事件循环自调本地后端的死锁)
    reply = await run_in_threadpool(dispatch, text)

    # 回消息
    send_result: Dict[str, Any] = {"ok": False, "dry_run": dry_run}
    if chat_id:
        # lark_client.send_text 内部调 subprocess,在事件循环里也会阻塞,一并放线程池
        send_result = await run_in_threadpool(send_text, chat_id, reply)
    else:
        send_result = {
            "ok": False,
            "stdout": "",
            "stderr": "no chat_id, skip send_text (set ?chat_id=oc_xxx for testing)",
            "dry_run": dry_run,
        }

    resp = WebhookResponse(
        ok=send_result.get("ok", False),
        echo=text,
        reply_preview=reply[:200] if reply else None,
        dry_run=dry_run,
        note=(
            f"event_type={msg['event_type'] or '?'} "
            f"sender={msg['sender'] or '?'} "
            f"lark_rc={send_result.get('returncode', '?')}"
            + (f" · sig=on" if sig_cfg.enabled else f" · sig=off(dry_run)")
        ),
    )
    _record_hit(
        chat_id=chat_id or None, sender=msg.get("sender"),
        text=text, ok=send_result.get("ok", False), echo=text,
        reply=reply, dry_run=dry_run,
        note=(
            f"event={msg['event_type'] or '?'} "
            f"lark_rc={send_result.get('returncode', '?')} "
            + ("sig=on" if sig_cfg.enabled else "sig=off(dry_run)")
        ),
        event_type=msg.get("event_type"), t0=t0,
    )
    return resp
