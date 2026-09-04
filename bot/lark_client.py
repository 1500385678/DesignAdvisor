"""
DesignAdvisor · 飞书 lark-cli 包装(Phase 0 #4 飞书 bot 闭环)

职责:把"给飞书发消息"这件事封成 Python 函数,内部用 subprocess 调 lark-cli。

为什么不用 lark SDK 直接 HTTP:与 36 行业其它 agent 的飞书通道保持一致
(参考 27 设计 跨工程 `feishu-channel.yaml` 配置),统一走 lark-cli 子进程,
便于复用 `lark-cli --profile design im +messages-send ...` 的标准调用。

环境变量:
- FEISHU_BOT_DRY_RUN=1     → 离线模式,只 print 不真发(默认开,Phase 0 试运行)
- LARK_CLI_BIN             → lark-cli 可执行路径(默认 lark-cli,假设在 PATH)
- LARK_PROFILE             → lark-cli profile 名(默认 design,与 36 行业约定一致)

不做什么(留待 Phase 1):
- 卡片 / 富文本(本轮只发纯文本,适配飞书消息体最简)
- 异步 / 队列(本轮同步调,飞书 webhook 是低频,够用)
- 重试 / 限流(lark-cli 失败直接 raise,调用方决定重试策略)
"""

from __future__ import annotations

import os
import shlex
import subprocess
from typing import List, Optional


def _dry_run() -> bool:
    """是否 dry_run 模式(默认开,Phase 0 试运行,真发前显式设 FEISHU_BOT_DRY_RUN=0)。"""
    return os.getenv("FEISHU_BOT_DRY_RUN", "1") not in ("0", "false", "False", "")


def _lark_bin() -> str:
    return os.getenv("LARK_CLI_BIN", "lark-cli")


def _lark_profile() -> str:
    return os.getenv("LARK_PROFILE", "design")


def send_text(chat_id: str, text: str) -> dict:
    """给飞书 chat_id 发一条文本消息。

    Args:
        chat_id: 飞书 open_chat_id(oc_xxx)
        text:    纯文本内容(支持 \\n,1-1500 字符)

    Returns:
        dict: {"ok": bool, "stdout": str, "stderr": str, "dry_run": bool, "returncode": int}

    行为:
    - dry_run=1(默认):print 命令,不真发
    - dry_run=0:subprocess.run(["lark-cli", "--profile", profile, "im", "+messages-send",
                                  "--chat-id", chat_id, "--text", text])
    """
    if not chat_id:
        return {"ok": False, "stderr": "chat_id is required", "dry_run": _dry_run()}

    # 截断保护
    if len(text) > 1500:
        text = text[:1497] + "…"

    profile = _lark_profile()
    bin_path = _lark_bin()

    # 组命令(subprocess list 形式,避免 shell 注入)
    cmd: List[str] = [
        bin_path,
        "--profile", profile,
        "im", "+messages-send",
        "--chat-id", chat_id,
        "--text", text,
    ]

    if _dry_run():
        # 离线模式:只 print 命令 + 文本预览,不真发
        preview = text if len(text) <= 200 else text[:200] + "…"
        print(f"[bot.dry_run] $ {' '.join(shlex.quote(c) for c in cmd)}")
        print(f"[bot.dry_run] → chat_id={chat_id} text({len(text)}字):{preview}")
        return {
            "ok": True,
            "stdout": "(dry_run, no real send)",
            "stderr": "",
            "dry_run": True,
            "returncode": 0,
        }

    # 真发
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "dry_run": False,
            "returncode": result.returncode,
        }
    except FileNotFoundError:
        return {
            "ok": False,
            "stdout": "",
            "stderr": f"lark-cli not found at {bin_path}, set LARK_CLI_BIN env",
            "dry_run": False,
            "returncode": 127,
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "stdout": "",
            "stderr": "lark-cli timeout (10s)",
            "dry_run": False,
            "returncode": 124,
        }


# ---------- CLI 调试 ----------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("用法:python -m bot.lark_client <chat_id> <text...>")
        print("示例:FEISHU_BOT_DRY_RUN=1 python -m bot.lark_client oc_xxx 'hello'")
        sys.exit(1)
    cid = sys.argv[1]
    text = " ".join(sys.argv[2:])
    result = send_text(cid, text)
    print(result)
