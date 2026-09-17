"""
DesignAdvisor · 飞书 lark-cli 包装(Phase 0 #4 飞书 bot 闭环 + 0918 切第四刀 send_card)

职责:把"给飞书发消息"这件事封成 Python 函数,内部用 subprocess 调 lark-cli。

为什么不用 lark SDK 直接 HTTP:与 36 行业其它 agent 的飞书通道保持一致
(参考 27 设计 跨工程 `feishu-channel.yaml` 配置),统一走 lark-cli 子进程,
便于复用 `lark-cli --profile design im +messages-send ...` 的标准调用。

环境变量:
- FEISHU_BOT_DRY_RUN=1     → 离线模式,只 print 不真发(默认开,Phase 0 试运行)
- LARK_CLI_BIN             → lark-cli 可执行路径(默认 lark-cli,假设在 PATH)
- LARK_PROFILE             → lark-cli profile 名(默认 design,与 36 行业约定一致)

两个发送函数(2026-09-18 切第四刀 send_card 新增):
- send_text(chat_id, text)          → 纯文本(已就位,Phase 0 试运行 + 0917 stub 复用)
- send_card(chat_id, card_dict)     → 飞书交互卡片(0918 新增,对齐 lark-cli
                                       `--msg-type interactive --content <card_json>`,
                                       envelope 内的 msg_type/card 拆开用)
- 调用方按需选 text 或 card;卡片渲染由 bot/card.py + bot/notify_reviews.py render_*_card
  生成 dict,send_card 只负责投递,不渲染

不做什么(留待 Phase 1+):
- 异步 / 队列(本轮同步调,飞书 webhook 是低频,够用)
- 重试 / 限流(lark-cli 失败直接 raise,调用方决定重试策略)
- 卡片交互回调(URL 跳转不算,本轮只静态渲染)
- 多模板切换(本轮透传 dict,template 由 render_*_card 决定)
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
from typing import Any, Dict, List, Optional


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


# ---------- send_card(0918 切第四刀 新增) ----------


def send_card(chat_id: str, card_dict: Dict[str, Any]) -> Dict[str, Any]:
    """给飞书 chat_id 发一张交互卡片。

    Args:
        chat_id:   飞书 open_chat_id(oc_xxx)
        card_dict: 飞书卡片 dict(与 `bot/card.py` / `bot/notify_reviews.py` 的
                   `render_*_card()` 输出对齐),形如:
                   {
                       "msg_type": "interactive",
                       "card": {
                           "header": {"title": ..., "template": ...},
                           "elements": [...],
                       },
                   }

    Returns:
        dict: {"ok": bool, "stdout": str, "stderr": str, "dry_run": bool, "returncode": int}
        - 与 send_text 返回结构一致,调用方可统一处理
        - ok=False 的常见原因:chat_id 空 / card_dict 非法 / JSON 序列化失败 /
          lark-cli 不存在 / 10s timeout

    行为:
    - dry_run=1(默认):print 命令 + JSON 预览,不真发
    - dry_run=0:subprocess.run(["lark-cli", "--profile", profile, "im", "+messages-send",
                                 "--chat-id", chat_id, "--msg-type", msg_type,
                                 "--content", card_json])
    - msg_type 默认从 card_dict["msg_type"] 取(目前固定 "interactive"),
      透传 future 其它类型(share_chat 等)
    - content 取 card_dict["card"] 序列化(剥掉外层 msg_type envelope,
      对齐 lark-cli --content 是 message 内层 content 字段的语义)

    为什么从 envelope 剥 card 体:
    飞书消息 API 顶层结构是 {"msg_type": ..., "content": <inner>},
    `lark-cli im +messages-send --msg-type <t> --content <c>` 的语义是把 msg_type 和
    inner content 分开传,所以 envelope 里的 msg_type / card 必须拆开,避免重复设置 msg_type。

    不做什么(留待 Phase 1+):
    - 异步队列(本轮同步调,评审事件低频,够用)
    - 重试 / 限流(lark-cli 失败直接返 ok=False,调用方决定)
    - 卡片交互回调(URL 跳转不算,本轮只静态渲染)
    - JSON schema 校验(透传,schema 由 render_*_card 保证,本函数只负责投递)
    """
    if not chat_id:
        return {"ok": False, "stderr": "chat_id is required", "dry_run": _dry_run()}

    if not isinstance(card_dict, dict) or "card" not in card_dict:
        return {
            "ok": False,
            "stderr": f"card_dict 必须是含 'card' 字段的 dict,got={type(card_dict).__name__}",
            "dry_run": _dry_run(),
        }

    msg_type = card_dict.get("msg_type", "interactive")
    card_body = card_dict["card"]

    try:
        card_json = json.dumps(card_body, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        return {
            "ok": False,
            "stderr": f"card_dict 序列化失败:{exc}",
            "dry_run": _dry_run(),
        }

    profile = _lark_profile()
    bin_path = _lark_bin()

    # 组命令(subprocess list 形式,避免 shell 注入)
    cmd: List[str] = [
        bin_path,
        "--profile", profile,
        "im", "+messages-send",
        "--chat-id", chat_id,
        "--msg-type", msg_type,
        "--content", card_json,
    ]

    if _dry_run():
        # 离线模式:只 print 命令 + JSON 预览,不真发
        preview = card_json if len(card_json) <= 200 else card_json[:200] + "…"
        print(f"[bot.dry_run] $ {' '.join(shlex.quote(c) for c in cmd)}")
        print(f"[bot.dry_run] → chat_id={chat_id} msg_type={msg_type} card_json({len(card_json)}字):{preview}")
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
