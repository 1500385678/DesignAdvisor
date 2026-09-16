"""
DesignAdvisor · 评审飞书通知模块 (Phase 1 #2 设计评审模块 切第四刀 · v0.1 stub)

职责:把 `api/reviews.py` 的评审事件(创建 / 状态转移 / 决策投票)推送到飞书群,
     复用 `bot/lark_client.send_text` 做底层发送,dry_run 模式默认开。

事件类型(3 件,对应评审协作的 3 个 PATCH/POST 触发点):
- "created"      评审创建(POST /api/v1/reviews 成功 → 通知评审人 + 关注群)
- "transitioned" 状态机转移(PATCH /api/v1/reviews/{id}/transition 成功 → 通知变更)
- "decided"      决策投票(PATCH /api/v1/reviews/{id}/decision 成功 → 通知投票结果)

为什么独立模块(不塞进 webhook.py / lark_client.py):
- webhook.py 走的是"飞书 → 我们"的入站链路,本模块走"我们 → 飞书"的出站链路,
  关注点分离,未来加 5 设计师 dogfood 时方便接事件总线 / 异步队列
- 评审事件有自己的领域结构(评审 / 资产 / 决策 / 优先级),不复用 search_handler 的
  text / dp / help 三件套

调用入口:
- `ReviewNotifier.from_env()`:从环境变量构造(env-gated,缺 FEISHU_REVIEW_NOTIFY_CHAT_ID
  时 `enabled=False` 静默跳过,避免试运行阶段误发)
- `notifier.notify(event_type, review)`:3 事件统一入口,内部按 event_type 路由到
  各自的 render → send_text → return ok/err dict

卡片渲染(0917 stub):本轮只出 3 件骨架渲染函数(返回 plain dict),
  复用 `bot/card._header / _div_md / _note / _action_button` 工厂,保证视觉风格一致;
  真正飞书卡片 schema 留待 0918+ 切第四刀补 `render_*_card()` 完整版本。

环境变量:
- FEISHU_REVIEW_NOTIFY_ENABLED   是否启用评审通知(默认 0;切真发前显式设 1)
- FEISHU_REVIEW_NOTIFY_CHAT_ID   接收通知的飞书群 oc_xxx(必填,未配 enabled=False)
- FEISHU_BOT_DRY_RUN             复用 bot lark_client 的 dry_run 开关(默认 1)

不做什么(留待切第四刀完整版):
- 真实事件埋点(api/reviews.py 6 端点返回点埋 notify 调用,本轮不接)
- 异步队列(本轮同步调 send_text,评审事件低频,够用)
- 卡片交互回调(URL 跳转不算,本轮只静态渲染)
- 评审 SLA / 截止时间告警(Phase 1 #3)
- 多群分发(不同优先级 → 不同群,本轮单群)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from bot.card import _action_button, _div_md, _header, _note
from bot.lark_client import send_text

# ---------- 支持的 3 种事件类型 ----------

EVENT_CREATED = "created"
EVENT_TRANSITIONED = "transitioned"
EVENT_DECIDED = "decided"

SUPPORTED_EVENTS = {EVENT_CREATED, EVENT_TRANSITIONED, EVENT_DECIDED}


# ---------- 配置 ----------

@dataclass
class ReviewNotifierConfig:
    """评审通知器配置(env-gated,缺关键 env 时 enabled=False 静默跳过)。"""

    enabled: bool = False
    chat_id: str = ""
    # dry_run 复用 bot/lark_client 的全局开关,本模块不再独立 env,避免双源

    @classmethod
    def from_env(cls) -> "ReviewNotifierConfig":
        """从环境变量构造(默认 enabled=False,试运行阶段安全)。"""
        enabled_raw = os.getenv("FEISHU_REVIEW_NOTIFY_ENABLED", "0")
        chat_id = os.getenv("FEISHU_REVIEW_NOTIFY_CHAT_ID", "")
        enabled = enabled_raw.lower() in ("1", "true") and bool(chat_id)
        return cls(enabled=enabled, chat_id=chat_id)


# ---------- 评审卡片渲染(0917 stub) ----------

# 优先级中文 + emoji 映射(对齐 api/reviews.py _REVIEW_PRIORITIES)
_PRIORITY_LABEL = {
    "low": "🟢 低",
    "medium": "🟡 中",
    "high": "🟠 高",
    "blocker": "🔴 阻塞",
}

# 状态中文 + emoji 映射(对齐 api/reviews.py _REVIEW_STATUSES,前端配色一致)
_STATUS_LABEL = {
    "draft": "📝 草稿",
    "in_review": "👀 评审中",
    "approved": "✅ 已通过",
    "rejected": "❌ 已驳回",
    "deprecated": "🗑 已弃用",
    "archived": "📦 已归档",
}

# 决策中文 + emoji 映射(对齐 api/reviews.py _REVIEW_DECISIONS)
_DECISION_LABEL = {
    "pending": "⏳ 待投",
    "approved": "✅ 赞成",
    "rejected_with_reason": "❌ 驳回(有理由)",
    "request_changes": "🔁 需要修改",
}


def _review_url(review_id: str, web_base: str = "http://127.0.0.1:3000") -> str:
    """评审详情页 Web URL(底部按钮跳转用)。"""
    return f"{web_base}/reviews/{review_id}"


def render_review_created_card(review: Dict[str, Any]) -> Dict[str, Any]:
    """评审创建事件卡片(0917 stub:返回 dict,内容字段齐,留待切第四刀接 lark_client.send_card)。

    Args:
        review: /api/v1/reviews/{id} 详情 dict,字段含
                id / title / priority / status / reviewers / creator / asset_id / created_at

    Returns:
        飞书 interactive card dict(对齐 bot/card.py schema,msg_type + card.header + card.elements)
    """
    rid = review.get("id", "?")
    title = review.get("title", "(无标题)")
    priority = _PRIORITY_LABEL.get(review.get("priority", ""), review.get("priority", ""))
    creator = review.get("creator", "?")
    reviewers = review.get("reviewers", []) or []
    reviewer_str = ", ".join(reviewers) if reviewers else "(未指定评审人)"

    header_title = f"📥 新评审 · {title}"
    elements = [
        _div_md(f"**评审 ID** `{rid}` · {priority}"),
        _div_md(f"**发起人** {creator}"),
        _div_md(f"**评审人** {reviewer_str}"),
        _note("评审已创建,请评审人在 Web 端投票或转移状态。"),
        _action_button("🔗 打开评审详情", _review_url(rid)),
    ]
    return {
        "msg_type": "interactive",
        "card": {"header": _header(header_title, template="blue"), "elements": elements},
    }


def render_review_transitioned_card(review: Dict[str, Any], from_status: str, to_status: str) -> Dict[str, Any]:
    """评审状态转移事件卡片(0917 stub)。

    Args:
        review:      /api/v1/reviews/{id} 详情 dict
        from_status: 转移前状态(合法路径)
        to_status:   转移后状态

    Returns:
        飞书 interactive card dict
    """
    rid = review.get("id", "?")
    title = review.get("title", "(无标题)")
    from_lbl = _STATUS_LABEL.get(from_status, from_status)
    to_lbl = _STATUS_LABEL.get(to_status, to_status)
    actor = review.get("last_actor", "?")  # PATCH /transition 成功后写入

    header_title = f"🔄 状态变更 · {title}"
    elements = [
        _div_md(f"**评审 ID** `{rid}`"),
        _div_md(f"**变更** {from_lbl} → **{to_lbl}**"),
        _div_md(f"**操作人** {actor}"),
        _note("状态机已记录到 transitions_log(append-only 审计可追)。"),
        _action_button("🔗 查看评审", _review_url(rid)),
    ]
    return {
        "msg_type": "interactive",
        "card": {"header": _header(header_title, template="orange"), "elements": elements},
    }


def render_review_decided_card(review: Dict[str, Any], decision: str, voter: str) -> Dict[str, Any]:
    """评审决策投票事件卡片(0917 stub)。

    Args:
        review:   /api/v1/reviews/{id} 详情 dict
        decision: 决策值(approved / rejected_with_reason / request_changes / pending)
        voter:    投票人

    Returns:
        飞书 interactive card dict
    """
    rid = review.get("id", "?")
    title = review.get("title", "(无标题)")
    decision_lbl = _DECISION_LABEL.get(decision, decision)

    header_title = f"🗳 新投票 · {title}"
    elements = [
        _div_md(f"**评审 ID** `{rid}`"),
        _div_md(f"**投票人** {voter}"),
        _div_md(f"**决策** **{decision_lbl}**"),
        _note("投票已追加到 decisions_log(append-only,同评审人多次按 latest 一次)。"),
        _action_button("🔗 查看评审进度", _review_url(rid)),
    ]
    return {
        "msg_type": "interactive",
        "card": {"header": _header(header_title, template="green"), "elements": elements},
    }


# ---------- 通知主入口 ----------

class ReviewNotifier:
    """评审飞书通知器(env-gated,enabled=False 时所有 notify 调用返回 skipped=True)。"""

    def __init__(self, config: Optional[ReviewNotifierConfig] = None):
        self.config = config or ReviewNotifierConfig.from_env()

    @classmethod
    def from_env(cls) -> "ReviewNotifier":
        """便利工厂:从 env 直接构造。"""
        return cls(ReviewNotifierConfig.from_env())

    def notify(
        self,
        event_type: str,
        review: Dict[str, Any],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """统一入口:3 事件 → render 卡片 → send_text → return 结果 dict。

        Args:
            event_type: "created" | "transitioned" | "decided"
            review:     /api/v1/reviews/{id} 详情 dict
            **kwargs:   transitioned 需 from_status/to_status;decided 需 decision/voter

        Returns:
            dict: {"ok": bool, "skipped": bool, "event_type": str, "chat_id": str,
                   "send_result": dict | None}
            - enabled=False → ok=True, skipped=True(默认安全)
            - 未知 event_type → ok=False, skipped=False, error="unknown event_type"
            - send_text 失败 → ok=False, send_result={...}
        """
        if not self.config.enabled:
            return {
                "ok": True,
                "skipped": True,
                "event_type": event_type,
                "chat_id": self.config.chat_id,
                "send_result": None,
                "reason": "FEISHU_REVIEW_NOTIFY_ENABLED off",
            }

        if event_type not in SUPPORTED_EVENTS:
            return {
                "ok": False,
                "skipped": False,
                "event_type": event_type,
                "chat_id": self.config.chat_id,
                "send_result": None,
                "error": f"unknown event_type: {event_type!r}, expected one of {sorted(SUPPORTED_EVENTS)}",
            }

        # 选 render
        if event_type == EVENT_CREATED:
            card = render_review_created_card(review)
        elif event_type == EVENT_TRANSITIONED:
            card = render_review_transitioned_card(
                review,
                from_status=kwargs.get("from_status", ""),
                to_status=kwargs.get("to_status", ""),
            )
        else:  # EVENT_DECIDED
            card = render_review_decided_card(
                review,
                decision=kwargs.get("decision", ""),
                voter=kwargs.get("voter", ""),
            )

        # 卡片序列化 + 走 send_text(0917 stub:卡片暂以纯文本 fallback,留待切第四刀接 send_card)
        text = _card_to_text_fallback(card, event_type, review, kwargs)
        send_result = send_text(self.config.chat_id, text)

        return {
            "ok": bool(send_result.get("ok")),
            "skipped": False,
            "event_type": event_type,
            "chat_id": self.config.chat_id,
            "send_result": send_result,
        }


def _card_to_text_fallback(
    card: Dict[str, Any],
    event_type: str,
    review: Dict[str, Any],
    kwargs: Dict[str, Any],
) -> str:
    """把卡片降级为 send_text 的纯文本(0917 stub 用,留待切第四刀接 lark_client.send_card 真发卡片)。

    Args:
        card:       本模块 render_*_card 返回的 dict
        event_type: created / transitioned / decided
        review:     评审详情
        kwargs:     透传给 render 的额外参数

    Returns:
        适合飞书纯文本消息的字符串(title + body + 链接)
    """
    rid = review.get("id", "?")
    title = review.get("title", "(无标题)")
    url = _review_url(rid)

    if event_type == EVENT_CREATED:
        priority = _PRIORITY_LABEL.get(review.get("priority", ""), review.get("priority", ""))
        reviewers = review.get("reviewers", []) or []
        reviewer_str = ", ".join(reviewers) if reviewers else "(未指定)"
        return (
            f"📥 新评审 · {title}\n"
            f"评审 ID {rid} · {priority}\n"
            f"发起人 {review.get('creator', '?')}\n"
            f"评审人 {reviewer_str}\n"
            f"🔗 {url}"
        )
    if event_type == EVENT_TRANSITIONED:
        from_lbl = _STATUS_LABEL.get(kwargs.get("from_status", ""), kwargs.get("from_status", ""))
        to_lbl = _STATUS_LABEL.get(kwargs.get("to_status", ""), kwargs.get("to_status", ""))
        return (
            f"🔄 状态变更 · {title}\n"
            f"评审 ID {rid}\n"
            f"{from_lbl} → {to_lbl}\n"
            f"操作人 {review.get('last_actor', '?')}\n"
            f"🔗 {url}"
        )
    # EVENT_DECIDED
    decision_lbl = _DECISION_LABEL.get(kwargs.get("decision", ""), kwargs.get("decision", ""))
    return (
        f"🗳 新投票 · {title}\n"
        f"评审 ID {rid}\n"
        f"投票人 {kwargs.get('voter', '?')}\n"
        f"决策 {decision_lbl}\n"
        f"🔗 {url}"
    )


# ---------- CLI 调试入口 ----------

if __name__ == "__main__":
    import json
    import sys

    notifier = ReviewNotifier.from_env()
    fake_review = {
        "id": "rev_demo_001",
        "title": "登录页按钮风格统一",
        "priority": "high",
        "status": "in_review",
        "creator": "zhangyong",
        "reviewers": ["alice", "bob"],
        "last_actor": "alice",
    }

    if len(sys.argv) > 1 and sys.argv[1] in SUPPORTED_EVENTS:
        event = sys.argv[1]
        result = notifier.notify(
            event,
            fake_review,
            **{k: v for k, v in zip(sys.argv[2::2], sys.argv[3::2])},
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"用法:python -m bot.notify_reviews <{ '|'.join(sorted(SUPPORTED_EVENTS)) }> [k v ...]")
        print(f"示例:FEISHU_BOT_DRY_RUN=1 python -m bot.notify_reviews decided decision approved voter alice")
        print(f"notifier.config = {notifier.config}")
