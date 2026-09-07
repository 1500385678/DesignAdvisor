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
- 消息去重 / 限流(Phase 0 试运行,流量低)
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from bot.search_handler import dispatch
from bot.lark_client import send_text, _dry_run
from bot.signature import SignatureConfig, SignatureError, verify as verify_signature

router = APIRouter(prefix="/api/v1/bot", tags=["bot"])


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
    return HealthResponse(
        status="ok",
        module="bot",
        version="0.1.0",
        dry_run=_dry_run(),
        lark_bin=os.getenv("LARK_CLI_BIN", "lark-cli"),
        lark_profile=os.getenv("LARK_PROFILE", "design"),
        signature_enabled=sig_cfg.enabled,
        note=(
            "Phase 0 #4 飞书 bot 雏形闭环"
            + (" · dry_run=1(默认,只 print 不真发)" if _dry_run() else " · dry_run=0(真发,谨慎)")
            + (
                " · signature=on(已配 FEISHU_BOT_VERIFY_TOKEN,webhook 验签生效)"
                if sig_cfg.enabled
                else " · signature=off(未配 FEISHU_BOT_VERIFY_TOKEN,跳过验签,本地 dry_run 友好)"
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
    """
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
            return WebhookResponse(
                ok=False,
                dry_run=_dry_run(),
                note=f"signature failed: {e.reason}",
            )

    # 3) 解析 JSON body
    try:
        import json
        payload = json.loads(body_bytes) if body_bytes else {}
    except Exception:
        return WebhookResponse(
            ok=False,
            dry_run=_dry_run(),
            note="invalid json body",
        )

    if not isinstance(payload, dict):
        return WebhookResponse(
            ok=False,
            dry_run=_dry_run(),
            note="payload is not a dict",
        )

    msg = _extract_message(payload)
    text = msg["text"] or ""
    chat_id = msg["chat_id"] or ""

    if not text:
        return WebhookResponse(
            ok=True,
            dry_run=_dry_run(),
            note=f"no text in event (event_type={msg['event_type']})",
        )

    if not chat_id:
        # 测试 / 调试用:支持 query 传 chat_id(便于 curl 干跑)
        chat_id = request.query_params.get("chat_id", "")

    # 业务分发(放线程池,避免单线程事件循环自调本地后端的死锁)
    reply = await run_in_threadpool(dispatch, text)

    # 回消息
    send_result: Dict[str, Any] = {"ok": False, "dry_run": _dry_run()}
    if chat_id:
        # lark_client.send_text 内部调 subprocess,在事件循环里也会阻塞,一并放线程池
        send_result = await run_in_threadpool(send_text, chat_id, reply)
    else:
        send_result = {
            "ok": False,
            "stdout": "",
            "stderr": "no chat_id, skip send_text (set ?chat_id=oc_xxx for testing)",
            "dry_run": _dry_run(),
        }

    return WebhookResponse(
        ok=send_result.get("ok", False),
        echo=text,
        reply_preview=reply[:200] if reply else None,
        dry_run=_dry_run(),
        note=(
            f"event_type={msg['event_type'] or '?'} "
            f"sender={msg['sender'] or '?'} "
            f"lark_rc={send_result.get('returncode', '?')}"
            + (f" · sig=on" if sig_cfg.enabled else f" · sig=off(dry_run)")
        ),
    )
