"""
DesignAdvisor · 评审飞书通知模块 单元测试 (0920 切第四刀 完整版)

覆盖:
- ReviewNotifierConfig.from_env 4 件套(env off / on 但缺 chat_id / on 全配 / on true 大小写)
- render_review_created_card / render_review_transitioned_card / render_review_decided_card
  三件卡片 schema 校验(msg_type + card.header + card.elements + 5 elements 段)
- ReviewNotifier 5 路径(notify disabled → skipped / notify unknown event → error /
  notify created with dry_run → ok=True dry_run / notify transitioned with chat_id → ok=True /
  notify decided with chat_id → ok=True)
- 0920 新增:verify send_card 真发路径(补丁 send_card,断言被调 1 次,返回 dict 含 msg_type=interactive)

跑法:cd _DesignLib/DesignWeb && python -m pytest bot/test_notify_reviews.py -v

变更(0920 vs 0917):
- 移除 _card_to_text_fallback 纯文本降级相关测试(TestCardToTextFallback 整段删)
- TestReviewNotifier 测试 mock 目标从 send_text 改成 send_card
- 新增 test_notify_sends_card_not_text 验证走 send_card 路径(0920 完整版契约)
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from bot.notify_reviews import (
    EVENT_CREATED,
    EVENT_DECIDED,
    EVENT_TRANSITIONED,
    SUPPORTED_EVENTS,
    ReviewNotifier,
    ReviewNotifierConfig,
    render_review_created_card,
    render_review_decided_card,
    render_review_transitioned_card,
)


# ---------- ReviewNotifierConfig.from_env ----------

class TestNotifierConfig:
    def test_from_env_disabled_default(self, monkeypatch):
        """默认 FEISHU_REVIEW_NOTIFY_ENABLED 未设 → enabled=False。"""
        monkeypatch.delenv("FEISHU_REVIEW_NOTIFY_ENABLED", raising=False)
        monkeypatch.delenv("FEISHU_REVIEW_NOTIFY_CHAT_ID", raising=False)
        cfg = ReviewNotifierConfig.from_env()
        assert cfg.enabled is False
        assert cfg.chat_id == ""

    def test_from_env_enabled_but_no_chat_id(self, monkeypatch):
        """enabled=1 但 chat_id 缺失 → enabled=False(双保险,避免误发)。"""
        monkeypatch.setenv("FEISHU_REVIEW_NOTIFY_ENABLED", "1")
        monkeypatch.delenv("FEISHU_REVIEW_NOTIFY_CHAT_ID", raising=False)
        cfg = ReviewNotifierConfig.from_env()
        assert cfg.enabled is False
        assert cfg.chat_id == ""

    def test_from_env_fully_configured(self, monkeypatch):
        """enabled=1 + chat_id 配齐 → enabled=True。"""
        monkeypatch.setenv("FEISHU_REVIEW_NOTIFY_ENABLED", "1")
        monkeypatch.setenv("FEISHU_REVIEW_NOTIFY_CHAT_ID", "oc_review_xxx")
        cfg = ReviewNotifierConfig.from_env()
        assert cfg.enabled is True
        assert cfg.chat_id == "oc_review_xxx"

    def test_from_env_case_insensitive_true(self, monkeypatch):
        """enabled="True" / "true" 都算开(env 大小写宽容)。"""
        for val in ("True", "true", "TRUE"):
            monkeypatch.setenv("FEISHU_REVIEW_NOTIFY_ENABLED", val)
            monkeypatch.setenv("FEISHU_REVIEW_NOTIFY_CHAT_ID", "oc_x")
            assert ReviewNotifierConfig.from_env().enabled is True


# ---------- 卡片渲染 ----------

class TestRenderCards:
    def _fake_review(self) -> dict:
        return {
            "id": "rev_test_001",
            "title": "登录页按钮风格统一",
            "priority": "high",
            "status": "in_review",
            "creator": "zhangyong",
            "reviewers": ["alice", "bob"],
            "last_actor": "alice",
        }

    def test_render_created_card_schema(self):
        """created 卡片:msg_type + header.title + 5 elements(div×3 + note + action)。"""
        card = render_review_created_card(self._fake_review())
        assert card["msg_type"] == "interactive"
        # header.title 是 _header() 工厂输出的 nested dict {"tag":"plain_text","content":...}
        assert "登录页按钮风格统一" in card["card"]["header"]["title"]["content"]
        elements = card["card"]["elements"]
        # 3 div + 1 note + 1 action = 5
        assert len(elements) == 5
        assert elements[0]["tag"] == "div"
        assert elements[-1]["tag"] == "action"
        assert "rev_test_001" in card["card"]["elements"][0]["text"]["content"]

    def test_render_transitioned_card_with_from_to(self):
        """transitioned 卡片:from/to 状态文案 + 操作人 + 5 elements。"""
        review = self._fake_review()
        card = render_review_transitioned_card(review, "draft", "in_review")
        assert card["msg_type"] == "interactive"
        elements = card["card"]["elements"]
        # 从 card 文本里验证 from → to 出现在某个 div
        joined = " ".join(e.get("text", {}).get("content", "") for e in elements if e["tag"] == "div")
        assert "📝 草稿" in joined
        assert "👀 评审中" in joined
        assert "alice" in joined  # last_actor
        assert len(elements) == 5

    def test_render_decided_card_with_decision_voter(self):
        """decided 卡片:决策文案 + 投票人 + 5 elements。"""
        card = render_review_decided_card(self._fake_review(), "approved", "alice")
        assert card["msg_type"] == "interactive"
        elements = card["card"]["elements"]
        joined = " ".join(e.get("text", {}).get("content", "") for e in elements if e["tag"] == "div")
        assert "✅ 赞成" in joined
        assert "alice" in joined
        assert len(elements) == 5


# ---------- ReviewNotifier.notify 5 路径(0920 切第四刀 完整版) ----------

class TestReviewNotifier:
    def _make_review(self) -> dict:
        return {
            "id": "rev_test_002",
            "title": "色彩令牌对齐",
            "priority": "medium",
            "status": "in_review",
            "creator": "bob",
            "reviewers": ["alice"],
            "last_actor": "bob",
        }

    def test_notify_disabled_skipped(self, monkeypatch):
        """enabled=False → skipped=True, 不调 send_card。"""
        monkeypatch.setenv("FEISHU_REVIEW_NOTIFY_ENABLED", "0")
        monkeypatch.setenv("FEISHU_REVIEW_NOTIFY_CHAT_ID", "oc_x")
        notifier = ReviewNotifier.from_env()
        with patch("bot.notify_reviews.send_card") as mock_send:
            result = notifier.notify(EVENT_CREATED, self._make_review())
        assert result["ok"] is True
        assert result["skipped"] is True
        assert result["event_type"] == EVENT_CREATED
        assert result["send_result"] is None
        mock_send.assert_not_called()

    def test_notify_unknown_event_error(self, monkeypatch):
        """未知 event_type → ok=False + error 描述, 不调 send_card。"""
        monkeypatch.setenv("FEISHU_REVIEW_NOTIFY_ENABLED", "1")
        monkeypatch.setenv("FEISHU_REVIEW_NOTIFY_CHAT_ID", "oc_x")
        notifier = ReviewNotifier.from_env()
        with patch("bot.notify_reviews.send_card") as mock_send:
            result = notifier.notify("bogus_event", self._make_review())
        assert result["ok"] is False
        assert result["skipped"] is False
        assert "unknown event_type" in result["error"]
        assert "bogus_event" in result["error"]
        mock_send.assert_not_called()

    def test_notify_created_sends_card(self, monkeypatch):
        """enabled=True + dry_run=1 → send_card 返 ok=True dry_run=True, notifier 转 ok。

        0920 切第四刀 完整版契约:notify() 内部走 send_card 路径(不再是 send_text)。
        """
        monkeypatch.setenv("FEISHU_REVIEW_NOTIFY_ENABLED", "1")
        monkeypatch.setenv("FEISHU_REVIEW_NOTIFY_CHAT_ID", "oc_dryrun_xxx")
        monkeypatch.setenv("FEISHU_BOT_DRY_RUN", "1")
        notifier = ReviewNotifier.from_env()
        with patch(
            "bot.notify_reviews.send_card",
            return_value={"ok": True, "dry_run": True, "stdout": "(dry_run)", "stderr": "", "returncode": 0},
        ) as mock_send:
            result = notifier.notify(EVENT_CREATED, self._make_review())
        assert result["ok"] is True
        assert result["skipped"] is False
        assert result["chat_id"] == "oc_dryrun_xxx"
        # 0920 关键断言:send_card 被调 1 次,且 chat_id 正确,card_dict 是 created 卡片
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args.args[0] == "oc_dryrun_xxx"
        card_dict = call_args.args[1]
        assert card_dict["msg_type"] == "interactive"
        # 渲染 created 卡片,header.template=blue
        assert card_dict["card"]["header"]["template"] == "blue"
        # send_result 由 send_card 内部 dry_run 返回
        assert result["send_result"]["dry_run"] is True

    def test_notify_transitioned_sends_card(self, monkeypatch):
        """enabled=True + transitioned 事件 → send_card 调 1 次,card 是 orange 模板。"""
        monkeypatch.setenv("FEISHU_REVIEW_NOTIFY_ENABLED", "1")
        monkeypatch.setenv("FEISHU_REVIEW_NOTIFY_CHAT_ID", "oc_tx_xxx")
        monkeypatch.setenv("FEISHU_BOT_DRY_RUN", "1")
        notifier = ReviewNotifier.from_env()
        with patch(
            "bot.notify_reviews.send_card",
            return_value={"ok": True, "dry_run": True, "stdout": "", "stderr": "", "returncode": 0},
        ) as mock_send:
            result = notifier.notify(
                EVENT_TRANSITIONED,
                self._make_review(),
                from_status="draft",
                to_status="in_review",
            )
        assert result["ok"] is True
        assert result["event_type"] == EVENT_TRANSITIONED
        assert result["send_result"]["dry_run"] is True
        mock_send.assert_called_once()
        # 校验卡片 header 模板(transitioned 用 orange)
        card_dict = mock_send.call_args.args[1]
        assert card_dict["card"]["header"]["template"] == "orange"

    def test_notify_decided_sends_card(self, monkeypatch):
        """enabled=True + decided 事件 → send_card 调 1 次,card 是 green 模板。"""
        monkeypatch.setenv("FEISHU_REVIEW_NOTIFY_ENABLED", "1")
        monkeypatch.setenv("FEISHU_REVIEW_NOTIFY_CHAT_ID", "oc_de_xxx")
        monkeypatch.setenv("FEISHU_BOT_DRY_RUN", "1")
        notifier = ReviewNotifier.from_env()
        with patch(
            "bot.notify_reviews.send_card",
            return_value={"ok": True, "dry_run": True, "stdout": "", "stderr": "", "returncode": 0},
        ) as mock_send:
            result = notifier.notify(
                EVENT_DECIDED,
                self._make_review(),
                decision="approved",
                voter="alice",
            )
        assert result["ok"] is True
        assert result["event_type"] == EVENT_DECIDED
        assert result["send_result"]["dry_run"] is True
        mock_send.assert_called_once()
        # 校验卡片 header 模板(decided 用 green)
        card_dict = mock_send.call_args.args[1]
        assert card_dict["card"]["header"]["template"] == "green"

    def test_notify_sends_card_not_text(self, monkeypatch):
        """0920 切第四刀 关键回归:enabled=True 时 notify() 调 send_card,绝不走 send_text。

        防御性测试:即便 send_text 在 bot.lark_client 仍存在,notify() 内部也不会调它。
        """
        monkeypatch.setenv("FEISHU_REVIEW_NOTIFY_ENABLED", "1")
        monkeypatch.setenv("FEISHU_REVIEW_NOTIFY_CHAT_ID", "oc_def_xxx")
        notifier = ReviewNotifier.from_env()
        with patch(
            "bot.notify_reviews.send_card",
            return_value={"ok": True, "dry_run": True, "stdout": "", "stderr": "", "returncode": 0},
        ) as mock_card, patch(
            "bot.lark_client.send_text",
            return_value={"ok": True, "dry_run": True, "stdout": "", "stderr": "", "returncode": 0},
        ) as mock_text:
            notifier.notify(EVENT_CREATED, self._make_review())
        mock_card.assert_called_once()
        mock_text.assert_not_called()


# ---------- 顶层常量 ----------

def test_supported_events_constant():
    """SUPPORTED_EVENTS 恰好 3 件,顺序无关(用 set 校验)。"""
    assert SUPPORTED_EVENTS == {EVENT_CREATED, EVENT_TRANSITIONED, EVENT_DECIDED}
    assert len(SUPPORTED_EVENTS) == 3