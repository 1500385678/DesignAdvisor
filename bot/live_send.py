"""
DesignAdvisor · 飞书 bot 切真发入口(Phase 0 #4 飞书 bot 增强第 4 步)

职责:在 `bot.lark_client` 之上加一层"试运行前自检 + 真发编排",确保:
1. lark-cli 可用 + profile 配对(probe_lark_cli 调 --help,无副作用)
2. 显式开启 dry_run=0 才真发(默认 dry_run=1 仍只 print,防误发)
3. 编排顺序:先 probe 后 send(probe 失败直接抛,不发消息)

为什么不在 lark_client.py 里加:lark_client 是底层 subprocess 包装,
live_send 是"试运行编排"层,职责分离,便于切真发前后两阶段维护。

为什么不做异步 / 队列:飞书 webhook 是低频(每 chat_id 1 rps),同步够用。

环境变量:
- FEISHU_BOT_DRY_RUN        → 0=真发,1=dry_run(默认 1,试运行前显式设 0)
- LARK_CLI_BIN              → lark-cli 可执行路径(默认 lark-cli,假设在 PATH)
- LARK_PROFILE              → lark-cli profile 名(默认 design,36 行业约定)
- FEISHU_BOT_DEFAULT_CHAT_ID → 真发时默认 chat_id(留空则 CLI 必须显式传)

不做什么(留待 Phase 1):
- 多 chat_id 广播(本轮 1 条 1 chat)
- 重试 / 死信(probe 失败直接 raise,人工介入)
- 卡片切真发(`bot/card.py` 仍是 dry_run,卡片走 lark SDK 在 Phase 1 切)
"""

from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass
from typing import Optional

from bot.lark_client import send_text


@dataclass
class LiveSendConfig:
    """切真发编排配置(env 派生)。"""

    dry_run: bool = True
    lark_cli_bin: str = "lark-cli"
    lark_profile: str = "design"
    default_chat_id: Optional[str] = None

    @classmethod
    def from_env(cls) -> "LiveSendConfig":
        """从 env 读 4 个变量,默认值与 lark_client.py 对齐。"""
        return cls(
            dry_run=os.getenv("FEISHU_BOT_DRY_RUN", "1") not in ("0", "false", "False", ""),
            lark_cli_bin=os.getenv("LARK_CLI_BIN", "lark-cli"),
            lark_profile=os.getenv("LARK_PROFILE", "design"),
            default_chat_id=os.getenv("FEISHU_BOT_DEFAULT_CHAT_ID") or None,
        )


class ProbeError(RuntimeError):
    """lark-cli probe 失败(鉴权/不存在/超时)。"""


def probe_lark_cli(bin_path: str, profile: str, timeout: int = 5) -> dict:
    """调 `lark-cli --profile <p> im +messages-send --help` 做"无副作用鉴权校验"。

    为什么用 --help:lark-cli 子命令的 --help 输出鉴权错误会直接走 stderr,
    不发任何消息,不会污染飞书会话;不写 lark-cli 自带 dry_run 子命令,
    走标准 --help 是最稳的"连通性"探针。

    Args:
        bin_path: lark-cli 可执行路径
        profile:  lark-cli profile 名
        timeout:  超时秒数(默认 5s)

    Returns:
        dict: {"ok": bool, "stdout": str, "stderr": str, "returncode": int}

    Raises:
        ProbeError: lark-cli 不存在 / 超时 / 非 0 returncode
    """
    cmd = [bin_path, "--profile", profile, "im", "+messages-send", "--help"]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
    except FileNotFoundError as e:
        raise ProbeError(f"lark-cli not found at {bin_path}, set LARK_CLI_BIN env") from e
    except subprocess.TimeoutExpired as e:
        raise ProbeError(f"lark-cli probe timeout ({timeout}s)") from e

    if result.returncode != 0:
        raise ProbeError(
            f"lark-cli probe failed: rc={result.returncode} stderr={result.stderr.strip()[:200]}"
        )

    return {
        "ok": True,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }


def send_via_lark(text: str, chat_id: Optional[str] = None, *, config: Optional[LiveSendConfig] = None) -> dict:
    """切真发编排入口(先 probe 后 send)。

    Args:
        text:    消息内容(1-1500 字符,超长 lark_client 内部截断)
        chat_id: 飞书 open_chat_id(oc_xxx),留空从 config.default_chat_id 读
        config:  显式配置,None 则 from_env() 取

    Returns:
        dict: lark_client.send_text() 的返回值 + 1 字段 probe_ok

    Raises:
        ProbeError: 真发模式(dry_run=False)下 probe 失败
        ValueError: chat_id 缺失
    """
    if config is None:
        config = LiveSendConfig.from_env()

    effective_chat_id = chat_id or config.default_chat_id
    if not effective_chat_id:
        raise ValueError(
            "chat_id required: pass chat_id=... or set FEISHU_BOT_DEFAULT_CHAT_ID env"
        )

    probe_ok = False
    if not config.dry_run:
        # 真发前先 probe(防 lark-cli 不通时把 webhook 流程搞挂)
        probe_lark_cli(config.lark_cli_bin, config.lark_profile)
        probe_ok = True

    result = send_text(effective_chat_id, text)
    result["probe_ok"] = probe_ok
    return result


# ---------- CLI 调试 ----------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法:python -m bot.live_send <text...>")
        print("示例:FEISHU_BOT_DRY_RUN=1 python -m bot.live_send 'smoke test'")
        print("     FEISHU_BOT_DRY_RUN=0 python -m bot.live_send 'real send'")
        print("     FEISHU_BOT_DEFAULT_CHAT_ID=oc_xxx python -m bot.live_send 'hello'")
        sys.exit(1)

    text = " ".join(sys.argv[1:])
    try:
        result = send_via_lark(text)
    except (ProbeError, ValueError) as e:
        print(f"[bot.live_send] error: {e}", file=sys.stderr)
        sys.exit(2)
    print(result)
