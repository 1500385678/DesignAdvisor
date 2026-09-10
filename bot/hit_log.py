"""
DesignAdvisor · 飞书 bot 命中日志(Phase 0 #4 飞书 bot 增强 - 命中日志埋点)

为 5 设计师 dogfood 验收准备的基础设施 —— 纯本地 JSONL 落盘:
- 不上报、不外发,纯本地 append-only 文件
- 用途:事后回看 dogfood 期"设计师问了什么 / 命中几条 / 限流拒几条 / 验签拒几条"
- 默认关闭(本地开发不会被噪声淹没),FEISHU_BOT_HIT_LOG_ENABLED=1 启用
- 路径默认 ./data/bot_hit_log.jsonl(项目 data/ 目录,自动 mkdir -p)

字段(每条 JSON 一行,key 字典序固定便于 diff):
- ts         ISO 8601 本地时间(精确到毫秒,带时区)
- chat_id    飞书 chat_id(可空)
- sender     飞书 sender open_id(可空)
- text       飞书消息原文
- ok         True / False(整条 webhook 处理是否 ok)
- note       short tag,形如 "sig=off ratelimit=ok hit=5 card lark_rc=0"
- echo       业务 echo 文本(关键词)
- reply_len  命中回复长度(字符数)
- dry_run    True / False
- event_type 飞书事件类型(message / url_verification / ...)

触发链:
  bot/webhook.py → HitLog.record(event) → 1 行 JSONL append
  写失败返回 False,绝不阻塞主流程(命中日志是 dogfood 审计面,不是 SLA 路径)
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class HitLogConfig:
    """命中日志配置(env-gated,默认关闭,2 env 变量)。"""
    enabled: bool
    path: Path

    @classmethod
    def from_env(cls) -> "HitLogConfig":
        enabled_raw = os.getenv("FEISHU_BOT_HIT_LOG_ENABLED", "0")
        enabled = enabled_raw not in ("0", "", "false", "False", "FALSE", "no", "No")
        path_str = os.getenv("FEISHU_BOT_HIT_LOG_PATH", "./data/bot_hit_log.jsonl")
        return cls(enabled=enabled, path=Path(path_str))


class HitLog:
    """命中日志写入器(append-only JSONL,失败不抛异常)。"""

    def __init__(self, cfg: HitLogConfig):
        self.cfg = cfg

    def record(self, event: Dict[str, Any]) -> bool:
        """写 1 条 JSONL。返回 True=写入成功 / False=跳过或失败(永不抛异常)。"""
        if not self.cfg.enabled:
            return False
        try:
            self.cfg.path.parent.mkdir(parents=True, exist_ok=True)
            line = json.dumps(event, ensure_ascii=False, sort_keys=True)
            with self.cfg.path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
            return True
        except Exception:
            # 命中日志写失败不阻塞主流程
            return False

    def now_event(
        self,
        *,
        chat_id: Optional[str],
        sender: Optional[str],
        text: str,
        ok: bool,
        note: str,
        echo: Optional[str] = None,
        reply_len: int = 0,
        dry_run: bool = True,
        event_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """构造 1 条标准事件 dict(供 record() 消费)。"""
        return {
            "ts": datetime.now().astimezone().isoformat(timespec="milliseconds"),
            "chat_id": chat_id or "",
            "sender": sender or "",
            "text": text,
            "ok": ok,
            "note": note,
            "echo": echo or "",
            "reply_len": reply_len,
            "dry_run": dry_run,
            "event_type": event_type or "",
        }


def get_default_hitlog(cfg: Optional[HitLogConfig] = None) -> HitLog:
    """获取 HitLog 实例(env 每次重读,便于运行时切 enabled)。"""
    return HitLog(cfg or HitLogConfig.from_env())


if __name__ == "__main__":
    # CLI 调试入口:python -m bot.hit_log '{"text":"button","ok":true,"note":"hit=5"}'
    if len(sys.argv) < 2:
        print("usage: python -m bot.hit_log '<json-event>'", file=sys.stderr)
        sys.exit(2)
    cfg = HitLogConfig.from_env()
    if not cfg.enabled:
        print("FEISHU_BOT_HIT_LOG_ENABLED=0, set to 1 to enable", file=sys.stderr)
        sys.exit(0)
    try:
        event = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(f"invalid json: {e}", file=sys.stderr)
        sys.exit(2)
    log = get_default_hitlog(cfg)
    ok = log.record(event)
    print(f"recorded ok={ok} → {cfg.path}")
    sys.exit(0 if ok else 1)
