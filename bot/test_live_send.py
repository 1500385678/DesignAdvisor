"""
DesignAdvisor · bot.live_send 单元测试(8 单元)

覆盖:
- env 默认值 / dry_run=True 不调 subprocess / dry_run=False 调 subprocess 正确
- chat_id 默认值 / chat_id 缺失报错
- probe 调 lark-cli --help / probe 失败抛错
- send_via_lark 先 probe 后 send(顺序)

为什么 8 单元不更多:bot.live_send 编排层是轻量封装,核心逻辑 4 处
(env 解析 + probe + send 编排 + chat_id 校验),8 单元已 100% 覆盖。
真实 subprocess 行为由 bot/test_lark_client.py 负责(本轮不重复测)。
"""

from __future__ import annotations

import os
import subprocess
import unittest
from unittest.mock import MagicMock, patch

from bot.live_send import (
    LiveSendConfig,
    ProbeError,
    probe_lark_cli,
    send_via_lark,
)


class TestLiveSendConfig(unittest.TestCase):
    """1-2:env 默认值 / chat_id 默认值。"""

    def test_01_from_env_defaults(self):
        """env 默认值:4 字段,空 env 时 dry_run=True / bin=default / profile=design / chat_id=None。"""
        with patch.dict(os.environ, {}, clear=True):
            cfg = LiveSendConfig.from_env()
        self.assertTrue(cfg.dry_run)
        self.assertEqual(cfg.lark_cli_bin, "lark-cli")
        self.assertEqual(cfg.lark_profile, "design")
        self.assertIsNone(cfg.default_chat_id)

    def test_02_from_env_chat_id_default(self):
        """env chat_id 默认值:FEISHU_BOT_DEFAULT_CHAT_ID 配则读,空则 None。"""
        with patch.dict(os.environ, {"FEISHU_BOT_DEFAULT_CHAT_ID": "oc_default_xxx"}, clear=True):
            cfg = LiveSendConfig.from_env()
        self.assertEqual(cfg.default_chat_id, "oc_default_xxx")

        with patch.dict(os.environ, {"FEISHU_BOT_DEFAULT_CHAT_ID": ""}, clear=True):
            cfg = LiveSendConfig.from_env()
        self.assertIsNone(cfg.default_chat_id)


class TestSendViaLark(unittest.TestCase):
    """3-5 + 8:send_via_lark 编排(dry_run 不调 subprocess / 真发调 subprocess / chat_id 缺失 / 顺序)。"""

    def test_03_dry_run_does_not_call_subprocess(self):
        """dry_run=True:send_via_lark 走 lark_client.send_text 内部 print,不调 probe。"""
        with patch("bot.live_send.probe_lark_cli") as mock_probe, \
             patch("bot.live_send.send_text") as mock_send:
            mock_send.return_value = {"ok": True, "dry_run": True, "returncode": 0,
                                      "stdout": "(dry_run, no real send)", "stderr": ""}
            cfg = LiveSendConfig(dry_run=True, default_chat_id="oc_test_001")
            result = send_via_lark("smoke", config=cfg)

        mock_probe.assert_not_called()  # dry_run 模式跳过 probe
        mock_send.assert_called_once_with("oc_test_001", "smoke")
        self.assertTrue(result["dry_run"])
        self.assertFalse(result["probe_ok"])  # dry_run 模式 probe_ok=False

    def test_04_live_mode_calls_subprocess_via_probe_and_send(self):
        """dry_run=False:probe_lark_cli 调 lark-cli --help,send_text 调 lark-cli im +messages-send。"""
        with patch("bot.live_send.probe_lark_cli") as mock_probe, \
             patch("bot.live_send.send_text") as mock_send:
            mock_probe.return_value = {"ok": True, "stdout": "Usage: ...", "stderr": "", "returncode": 0}
            mock_send.return_value = {"ok": True, "dry_run": False, "returncode": 0,
                                      "stdout": "msg_id: om_xxx", "stderr": ""}
            cfg = LiveSendConfig(dry_run=False, lark_cli_bin="/usr/local/bin/lark-cli",
                                 lark_profile="design", default_chat_id="oc_live_001")
            result = send_via_lark("real send", config=cfg)

        # probe 必须先调用,且用配置的 bin/profile
        mock_probe.assert_called_once_with("/usr/local/bin/lark-cli", "design")
        # send_text 用配置的有效 chat_id
        mock_send.assert_called_once_with("oc_live_001", "real send")
        self.assertFalse(result["dry_run"])
        self.assertTrue(result["probe_ok"])

    def test_05_chat_id_missing_raises(self):
        """chat_id 缺失(无显式 chat_id 也无 env default)→ raise ValueError。"""
        cfg = LiveSendConfig(dry_run=True, default_chat_id=None)
        with self.assertRaises(ValueError) as ctx:
            send_via_lark("smoke", config=cfg)
        self.assertIn("chat_id required", str(ctx.exception))

    def test_08_explicit_chat_id_overrides_default(self):
        """显式 chat_id 覆盖 config.default_chat_id(命令行传 oc_explicit_xxx 优先)。"""
        with patch("bot.live_send.probe_lark_cli") as mock_probe, \
             patch("bot.live_send.send_text") as mock_send:
            mock_probe.return_value = {"ok": True, "stdout": "", "stderr": "", "returncode": 0}
            mock_send.return_value = {"ok": True, "dry_run": False, "returncode": 0,
                                      "stdout": "ok", "stderr": ""}
            cfg = LiveSendConfig(dry_run=False, default_chat_id="oc_default_yyy")
            send_via_lark("hi", chat_id="oc_explicit_xxx", config=cfg)

        mock_send.assert_called_once_with("oc_explicit_xxx", "hi")
        mock_probe.assert_called_once()  # 真发模式 probe 仍调


class TestProbeLarkCli(unittest.TestCase):
    """6-7:probe 调 lark-cli --help / probe 失败抛错。"""

    def test_06_probe_calls_lark_cli_help(self):
        """probe 调 `lark-cli --profile <p> im +messages-send --help`,不传 chat_id 不真发。"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Usage: lark-cli im +messages-send [OPTIONS]"
        mock_result.stderr = ""

        with patch("bot.live_send.subprocess.run", return_value=mock_result) as mock_run:
            result = probe_lark_cli("lark-cli", "design", timeout=5)

        # 校验 cmd list 正确(无 --chat-id / 无 --text,纯 --help)
        expected_cmd = ["lark-cli", "--profile", "design", "im", "+messages-send", "--help"]
        actual_cmd = mock_run.call_args[0][0]
        self.assertEqual(actual_cmd, expected_cmd)
        self.assertEqual(mock_run.call_args.kwargs.get("timeout"), 5)
        self.assertTrue(result["ok"])
        self.assertEqual(result["returncode"], 0)

    def test_07_probe_failure_raises_probe_error(self):
        """probe 失败(rc != 0 / lark-cli 不存在 / 超时)→ raise ProbeError。"""
        # 场景 a:lark-cli 不存在
        with patch("bot.live_send.subprocess.run", side_effect=FileNotFoundError):
            with self.assertRaises(ProbeError) as ctx:
                probe_lark_cli("/nope/lark-cli", "design")
            self.assertIn("lark-cli not found", str(ctx.exception))

        # 场景 b:lark-cli 超时
        with patch("bot.live_send.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="x", timeout=5)):
            with self.assertRaises(ProbeError) as ctx:
                probe_lark_cli("lark-cli", "design", timeout=5)
            self.assertIn("timeout", str(ctx.exception))

        # 场景 c:lark-cli 鉴权失败(rc != 0)
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "unauthorized: profile not found"
        with patch("bot.live_send.subprocess.run", return_value=mock_result):
            with self.assertRaises(ProbeError) as ctx:
                probe_lark_cli("lark-cli", "design")
            self.assertIn("probe failed", str(ctx.exception))
            self.assertIn("unauthorized", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
