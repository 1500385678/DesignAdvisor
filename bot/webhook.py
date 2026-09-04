"""
DesignAdvisor · 飞书 bot webhook 路由(Phase 0 #4 飞书 bot 闭环)

FastAPI 路由:
- POST /api/v1/bot/webhook   飞书事件回调(URL 验签 + 消息接收 + 异步回消息)
- GET  /api/v1/bot/health    健康检查(支持 dry_run 检测 / 路径就位)

触发链:
  飞书 server  → POST /api/v1/bot/webhook
                → parse 事件 → 提取 message_text + chat_id + sender
                → search_handler.dispatch(message_text)  ← 放线程池,避免自死锁
                → lark_client.send_text(chat_id, reply)
                → 200 OK(飞书要求 5s 内回 200,业务用 lark_client.send_text 异步回)

注意:search_handler 内部用 urllib 同步调本机后端(127.0.0.1:8000),
uvicorn 单进程单线程下,webhook handler 在事件循环里同步自调会死锁,
所以用 starlette.concurrency.run_in_threadpool 把 dispatch 包成线程调用。

不做什么(留待 Phase 1):
- 飞书 URL 验签加密逻辑(本轮只校验有 body 即可,真接入 lark-cli 后再补)
- 私聊 vs 群消息区分(本轮统一入口,都走 search_handler.dispatch)
- 消息去重 / 限流(Phase 0 试运行,流量低)
- 卡片 / 富文本(本轮只回纯文本,简洁)
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from bot.search_handler import dispatch
from bot.lark_client import send_text, _dry_run

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
    return HealthResponse(
        status="ok",
        module="bot",
        version="0.1.0",
        dry_run=_dry_run(),
        lark_bin=os.getenv("LARK_CLI_BIN", "lark-cli"),
        lark_profile=os.getenv("LARK_PROFILE", "design"),
        note=(
            "Phase 0 #4 飞书 bot 雏形闭环"
            + (" · dry_run=1(默认,只 print 不真发)" if _dry_run() else " · dry_run=0(真发,谨慎)")
        ),
    )


@router.post(
    "/webhook",
    response_model=WebhookResponse,
    summary="飞书事件回调",
)
async def webhook(request: Request) -> WebhookResponse:
    """飞书事件回调入口。

    1. 读 JSON body(飞书 v2 schema:header.event_type + event.message)
    2. 解析 message_text / chat_id
    3. search_handler.dispatch(message_text) 算出 reply
    4. lark_client.send_text(chat_id, reply) 同步发(超时风险由 send_text 内部 10s 兜底)
    5. 返回 200(飞书 5s 内要求回 200,这里就是同步发,5s 内能完成;流量大后改异步)
    """
    try:
        payload = await request.json()
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

    # URL 验签占位(真接入 lark-cli 后这里会校验 encrypt / token)
    # 当前 Phase 0 只接 dry_run 测试,跳过验签

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
        ),
    )
