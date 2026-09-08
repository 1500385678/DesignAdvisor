"""
DesignAdvisor · 飞书 bot 限流 (Phase 0 #4 飞书 bot 增强第 3 步 - 限流)

设计:每 chat_id 独立 token bucket,in-memory 状态(thread-safe)。

为什么是 token bucket 而非滑动窗口:
- 飞书用户偶发连发(1 条 / 5s)时,token bucket 允许"蓄满一波放 1 次"友好;
  滑动窗口会把"刚好跨过窗口边界的连发"误判通过,体验更差。
- token bucket 实现简单(O(1) 状态 / O(1) acquire),无 GC 压力。

为什么 in-memory:
- Phase 0 单 uvicorn 进程,进程内 dict 足够;切真发后用户量大,再切 Redis(INCR + EXPIRE)。
- 飞书 bot 试运行阶段 chat_id 数量 < 100,内存占用 < 10KB,无需持久化。

三个 env 变量:
- FEISHU_BOT_RATE_LIMIT_RPS    每秒补充 token 数(默认 1.0,0=关闭限流)
- FEISHU_BOT_RATE_LIMIT_BURST  桶容量(默认 3,即允许瞬时连发 3 条)
- FEISHU_BOT_RATE_LIMIT_ENABLED 1=启用,0=关闭(默认 1)

典型用法:
    cfg = RateLimitConfig.from_env()
    limiter = RateLimiter(cfg)
    allowed, retry_after = limiter.acquire("oc_xxx")
    if not allowed:
        return WebhookResponse(ok=False, note=f"rate limited: retry after {retry_after:.1f}s")
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Dict, Tuple


class RateLimitError(Exception):
    """限流配置或调用异常(预留,目前 config 解析失败抛 ValueError 不归本类)。"""


@dataclass(frozen=True)
class RateLimitConfig:
    """限流配置(env 注入)。"""

    enabled: bool
    rps: float       # 每秒补充 token 数(0=关闭)
    burst: float     # 桶容量(单 chat_id 瞬时允许的连发数)

    @classmethod
    def from_env(cls) -> "RateLimitConfig":
        """从环境变量读取,未配时按默认(rps=1.0, burst=3, enabled=True)。"""
        try:
            rps = float(os.getenv("FEISHU_BOT_RATE_LIMIT_RPS", "1.0"))
        except (TypeError, ValueError):
            rps = 1.0
        try:
            burst = float(os.getenv("FEISHU_BOT_RATE_LIMIT_BURST", "3"))
        except (TypeError, ValueError):
            burst = 3.0
        enabled_raw = os.getenv("FEISHU_BOT_RATE_LIMIT_ENABLED", "1").strip().lower()
        enabled = enabled_raw not in ("0", "false", "no", "off", "")

        # rps <= 0 视为关闭(允许显式 0 关闭,即使 enabled=1)
        if rps <= 0:
            enabled = False

        # burst < 1 容错:1 是最小有意义的桶容量
        if burst < 1:
            burst = 1.0

        return cls(enabled=enabled, rps=rps, burst=burst)


class RateLimiter:
    """线程安全的 in-memory token bucket 限流器(每 chat_id 独立桶)。"""

    def __init__(self, cfg: RateLimitConfig) -> None:
        self.cfg = cfg
        self._buckets: Dict[str, Tuple[float, float]] = {}
        # buckets: {chat_id: (tokens, last_refill_ts)}
        self._lock = threading.Lock()

    def _refill(self, tokens: float, last_ts: float, now: float) -> float:
        """根据时间差补充 token,返回补充后的 token 数(不超过 burst)。"""
        if self.cfg.rps <= 0:
            return tokens
        elapsed = max(0.0, now - last_ts)
        new_tokens = tokens + elapsed * self.cfg.rps
        return min(new_tokens, self.cfg.burst)

    def acquire(self, chat_id: str, now: float | None = None) -> Tuple[bool, float]:
        """尝试获取 1 个 token。

        Args:
            chat_id: 飞书会话 ID(oc_xxx),作为桶 key。
            now: 外部可注入时间(测试用),默认 time.time()。

        Returns:
            (allowed, retry_after):
            - allowed=True  → 桶里 ≥ 1 token,本次放行(扣 1 token),retry_after=0
            - allowed=False → 桶空,retry_after = 还需多少秒才能攒够 1 token

        Note:cfg.enabled=False 时永远返回 (True, 0.0),零开销。
        """
        if not self.cfg.enabled:
            return True, 0.0

        if not chat_id:
            # 防御:无 chat_id 不计入限流(交给上层逻辑处理)
            return True, 0.0

        if now is None:
            now = time.time()

        with self._lock:
            tokens, last_ts = self._buckets.get(chat_id, (self.cfg.burst, now))
            tokens = self._refill(tokens, last_ts, now)

            if tokens >= 1.0:
                self._buckets[chat_id] = (tokens - 1.0, now)
                return True, 0.0

            # 桶空:还需要 (1 - tokens) / rps 秒才够 1 token
            self._buckets[chat_id] = (tokens, now)
            retry_after = (1.0 - tokens) / self.cfg.rps if self.cfg.rps > 0 else 0.0
            return False, retry_after

    def reset(self, chat_id: str | None = None) -> None:
        """重置桶(测试 / 手动清空用)。

        chat_id=None 时清空所有桶。
        """
        with self._lock:
            if chat_id is None:
                self._buckets.clear()
            else:
                self._buckets.pop(chat_id, None)

    def stats(self) -> Dict[str, int]:
        """返回当前活跃 chat_id 数(供 /bot/health 暴露)。"""
        with self._lock:
            return {"active_chat_ids": len(self._buckets)}


# 进程级单例(供 webhook handler 复用,避免每个请求都构造)
_default_limiter: RateLimiter | None = None
_default_lock = threading.Lock()


def get_default_limiter(cfg: RateLimitConfig | None = None) -> RateLimiter:
    """获取进程级默认 limiter(惰性构造,cfg=None 时按 env 读)。"""
    global _default_limiter
    if _default_limiter is None:
        with _default_lock:
            if _default_limiter is None:
                _default_limiter = RateLimiter(cfg or RateLimitConfig.from_env())
    return _default_limiter


def reset_default_limiter() -> None:
    """重置进程级单例(测试用)。"""
    global _default_limiter
    with _default_lock:
        _default_limiter = None
