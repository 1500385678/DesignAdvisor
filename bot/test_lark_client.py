"""
DesignAdvisor · bot.lark_client 单元测试 (0918 切第四刀 - send_card 真发卡片函数)

覆盖 send_card 4 件(对齐 0918 计划 §验收标准 "bot/test_lark_client.py 4 件"):
1. env 默认 dry_run=1       →  不调 subprocess, 返回 ok=True dry_run=True
2. env 配齐 FEISHU_BOT_DRY_RUN=0  →  dry_run=False, 调 subprocess
3. 真发 subprocess cmd 形状   →  含 --msg-type interactive + --content <card_json> + chat_id
4. chat_id 缺失返 ok=False   →  stderr 含 "chat_id" 提示, 不调 subprocess

为什么 4 件不更多:send_card 是 send_text 的镜像(同 dry_run 模式 + 同 subprocess 模式),
  核心差异在 cmd 形状(多 --msg-type + 把 card 体当 --content),4 件正好覆盖
  env 矩阵 + cmd 形状 + 入参校验 3 维,无需更多边界。
  真发失败处理(FileNotFoundError / TimeoutExpired)与 send_text 共享同模式,本轮不重复测。

跑法:cd _DesignLib/DesignWeb && python -m pytest bot/test_lark_client.py -v
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from bot.lark_client import send_card


def _fake_card() -> dict:
    """构造一张测试用卡片(envelope + card 体对齐 bot/card.py render_*_card 输出)。"""
    return {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": "📥 测试卡片"},
                "template": "blue",
            },
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": "**评审 ID** rev_test_001"}},
                {"tag": "note", "elements": [{"tag": "plain_text", "content": "测试 note 行"}]},
            ],
        },
    }


# ---------- send_card 4 件 ----------

class TestSendCardDryRunDefault:
    """1:env 默认 dry_run=1 → 不调 subprocess, 返回 ok=True dry_run=True。"""

    def test_env_default_no_subprocess(self, monkeypatch):
        """FEISHU_BOT_DRY_RUN 未设 → dry_run=True, ok=True, subprocess.run 未被调。"""
        monkeypatch.delenv("FEISHU_BOT_DRY_RUN", raising=False)
        with patch("bot.lark_client.subprocess.run") as mock_run:
            result = send_card("oc_dryrun_001", _fake_card())
        assert result["ok"] is True
        assert result["dry_run"] is True
        assert result["returncode"] == 0
        assert "no real send" in result["stdout"]
        mock_run.assert_not_called()


class TestSendCardDryRunOff:
    """2:env FEISHU_BOT_DRY_RUN=0 → dry_run=False, 调 subprocess.run。"""

    def test_env_dry_run_off_calls_subprocess(self, monkeypatch):
        """FEISHU_BOT_DRY_RUN=0 → dry_run=False, subprocess.run 被调 1 次。"""
        monkeypatch.setenv("FEISHU_BOT_DRY_RUN", "0")
        fake_return = type(
            "R",
            (),
            {"returncode": 0, "stdout": '{"code":0,"msg":"ok"}', "stderr": ""},
        )()
        with patch("bot.lark_client.subprocess.run", return_value=fake_return) as mock_run:
            result = send_card("oc_realsend_001", _fake_card())
        assert result["ok"] is True
        assert result["dry_run"] is False
        assert result["returncode"] == 0
        assert mock_run.call_count == 1


class TestSendCardSubprocessCmdShape:
    """3:真发 cmd 形状校验 — 含 --msg-type interactive + --content <card_json> + chat_id。"""

    def test_real_send_cmd_shape(self, monkeypatch):
        """dry_run=0 时 cmd 列表结构:[lark-cli, --profile, design, im, +messages-send,
        --chat-id, oc_xxx, --msg-type, interactive, --content, <card_json>]。

        并校验 --content 是合法 JSON, card.header.template / card.elements[0].tag 对得上。
        """
        monkeypatch.setenv("FEISHU_BOT_DRY_RUN", "0")
        fake_return = type(
            "R",
            (),
            {"returncode": 0, "stdout": '{"code":0}', "stderr": ""},
        )()
        with patch("bot.lark_client.subprocess.run", return_value=fake_return) as mock_run:
            result = send_card("oc_cmd_001", _fake_card())

        assert result["ok"] is True
        assert mock_run.call_count == 1
        cmd = mock_run.call_args[0][0]

        # 校验 cmd 列表形状(每 2 元素一组)
        assert cmd[0] == "lark-cli"
        assert cmd[1:3] == ["--profile", "design"]
        assert cmd[3:5] == ["im", "+messages-send"]
        assert cmd[5:7] == ["--chat-id", "oc_cmd_001"]
        assert cmd[7:9] == ["--msg-type", "interactive"]
        assert cmd[9] == "--content"

        # 校验 --content 是合法 JSON,且剥了 envelope(直接是 card 体,不含 msg_type)
        content_json = cmd[10]
        parsed = json.loads(content_json)
        assert "msg_type" not in parsed, "send_card 应剥掉 envelope, --content 只含 card 体"
        assert parsed["header"]["template"] == "blue"
        assert parsed["elements"][0]["tag"] == "div"
        assert "评审 ID" in parsed["elements"][0]["text"]["content"]


class TestSendCardChatIdRequired:
    """4:chat_id 缺失 → ok=False + stderr 提示, 不调 subprocess。"""

    def test_chat_id_empty_returns_error(self, monkeypatch):
        """chat_id="" → ok=False, stderr 含 'chat_id', subprocess.run 未被调。"""
        monkeypatch.delenv("FEISHU_BOT_DRY_RUN", raising=False)
        with patch("bot.lark_client.subprocess.run") as mock_run:
            result = send_card("", _fake_card())
        assert result["ok"] is False
        assert "chat_id" in result["stderr"]
        mock_run.assert_not_called()


if __name__ == "__main__":
    # 单文件入口
    import subprocess
    import sys
    cmd = [sys.executable, "-m", "pytest", __file__, "-v"]
    print("用 pytest 跑:", " ".join(cmd))
    raise SystemExit(subprocess.call(cmd))
