"""
DesignAdvisor · 飞书 webhook URL 验签(Phase 0 #4 飞书 bot 增强第 2 步)

职责:校验飞书 server 回调的 X-Lark-Signature 头,避免 webhook 被恶意调用。

为什么需要:
- webhook 是公开 URL(无 auth),任何人都能 POST,刷消息、注入指令
- 飞书通过 X-Lark-Signature 头携带 HMAC-SHA256(timestamp + nonce + body, secret)
- 校验通过 = 消息来自飞书,信任

算法(参考 https://open.feishu.cn/document/server-docs/event-subscription-guide):
1. 从 header 读 X-Lark-Signature / X-Lark-Request-Timestamp / X-Lark-Request-Nonce
2. 拼字符串:timestamp + nonce + encrypt_key + body
3. HMAC-SHA256(secret, 拼串) -> hex digest
4. base64 解码 X-Lark-Signature -> 字节,与 hex digest 比对(用 hmac.compare_digest 防时序)

环境变量:
- FEISHU_BOT_VERIFY_TOKEN  飞书后台配置的事件订阅 "Verification Token"(也作为 HMAC secret)
                         未设置 = 跳过验签(Phase 0 dry_run 模式,本地 curl 干跑不受影响)

设计选择:
- 未设 secret 时静默跳过(allow_by_default=True),保持现有 dry_run 测试链路不破
- 失败时 raise SignatureError(401),由 webhook.py 转成 401 JSON 响应
- 时间戳偏移校验(±5min)防 replay,默认开启,可关
- 纯函数:verify(body_bytes, headers, secret) -> bool,无 IO,易单测
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
from dataclasses import dataclass
from typing import Optional


# 默认时间戳容差(秒),5 分钟与飞书侧建议一致
DEFAULT_TIMESTAMP_TOLERANCE = 300


class SignatureError(Exception):
    """验签失败异常(webhook 转 401)。"""
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class SignatureConfig:
    """验签配置(从 env 读一次,后续只读)。

    Attributes:
        secret:            飞书后台 Verification Token(同时作为 HMAC secret)
        timestamp_tolerance: 允许的时间戳偏移(秒),<=0 表示不校验
    """
    secret: Optional[str]
    timestamp_tolerance: int = DEFAULT_TIMESTAMP_TOLERANCE

    @property
    def enabled(self) -> bool:
        """是否启用验签(secret 非空)。"""
        return bool(self.secret)

    @classmethod
    def from_env(cls) -> "SignatureConfig":
        """从环境变量构造。

        Returns:
            SignatureConfig(secret=None, tolerance=300) 当 FEISHU_BOT_VERIFY_TOKEN 未设
            SignatureConfig(secret=xxx, tolerance=300) 当设置时
        """
        import os
        secret = os.getenv("FEISHU_BOT_VERIFY_TOKEN", "").strip() or None
        tol_str = os.getenv("FEISHU_BOT_TIMESTAMP_TOLERANCE", "").strip()
        try:
            tolerance = int(tol_str) if tol_str else DEFAULT_TIMESTAMP_TOLERANCE
        except ValueError:
            tolerance = DEFAULT_TIMESTAMP_TOLERANCE
        return cls(secret=secret, timestamp_tolerance=tolerance)


def verify(
    body: bytes,
    signature_b64: str,
    timestamp: str,
    nonce: str,
    config: SignatureConfig,
    now: Optional[float] = None,
) -> bool:
    """校验飞书 webhook 签名。

    Args:
        body:          HTTP 请求体(原始 bytes,非 parsed dict)
        signature_b64: X-Lark-Signature 头(base64 编码)
        timestamp:     X-Lark-Request-Timestamp 头(秒级字符串)
        nonce:         X-Lark-Request-Nonce 头
        config:        SignatureConfig(含 secret + tolerance)
        now:           当前时间(秒),测试时可注入

    Returns:
        True 验签通过 / 未启用 / 跳过;False 验签失败

    Raises:
        SignatureError: 验签逻辑异常(secret 缺失、header 缺失、时间戳过期、签名不匹配)

    行为:
    - config.enabled = False → 直接 return True(向后兼容 dry_run 模式)
    - 时间戳超过 tolerance → raise SignatureError("timestamp out of range")
    - base64 decode 失败 / 签名不匹配 → raise SignatureError
    """
    if not config.enabled:
        return True

    if not signature_b64:
        raise SignatureError("missing X-Lark-Signature header")
    if not timestamp:
        raise SignatureError("missing X-Lark-Request-Timestamp header")
    if not nonce:
        raise SignatureError("missing X-Lark-Request-Nonce header")

    # 时间戳偏移校验(防 replay)
    if config.timestamp_tolerance > 0:
        try:
            ts = float(timestamp)
        except ValueError:
            raise SignatureError(f"invalid timestamp format: {timestamp!r}")
        current = now if now is not None else time.time()
        if abs(current - ts) > config.timestamp_tolerance:
            raise SignatureError(
                f"timestamp out of range: {timestamp} vs now={current:.0f} "
                f"tolerance={config.timestamp_tolerance}s"
            )

    # 拼串:timestamp + nonce + secret + body(飞书官方顺序)
    to_sign = f"{timestamp}{nonce}{config.secret}".encode("utf-8") + body

    # HMAC-SHA256 → hex digest
    digest_hex = hmac.new(
        config.secret.encode("utf-8"),
        to_sign,
        hashlib.sha256,
    ).hexdigest()

    # base64 解码 X-Lark-Signature,与 hex digest 比对
    try:
        signature_bytes = base64.b64decode(signature_b64)
    except Exception as e:
        raise SignatureError(f"invalid base64 signature: {e}")

    # 飞书返回的是 hex digest 字符串(ASCII bytes),与新计算的 hex digest 对比
    expected_bytes = digest_hex.encode("ascii")
    if not hmac.compare_digest(signature_bytes, expected_bytes):
        raise SignatureError("signature mismatch")

    return True


# ---------- CLI 调试 ----------

if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("用法:")
        print("  生成签名:python -m bot.signature gen <secret> <timestamp> <nonce> <body>")
        print("  验签测试:python -m bot.signature check <secret> <body>")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "gen":
        if len(sys.argv) < 6:
            print("gen 需要 4 个参数:secret timestamp nonce body")
            sys.exit(1)
        secret, ts, nonce, body = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
        to_sign = f"{ts}{nonce}{secret}".encode("utf-8") + body.encode("utf-8")
        digest = hmac.new(secret.encode("utf-8"), to_sign, hashlib.sha256).hexdigest()
        sig_b64 = base64.b64encode(digest.encode("ascii")).decode("ascii")
        print(json.dumps({"signature": sig_b64, "timestamp": ts, "nonce": nonce}, ensure_ascii=False))
    elif cmd == "check":
        if len(sys.argv) < 4:
            print("check 需要 2 个参数:secret body")
            sys.exit(1)
        secret, body = sys.argv[2], sys.argv[3]
        config = SignatureConfig(secret=secret)
        try:
            ok = verify(
                body.encode("utf-8"),
                sys.argv[4] if len(sys.argv) > 4 else "",
                sys.argv[5] if len(sys.argv) > 5 else str(int(time.time())),
                sys.argv[6] if len(sys.argv) > 6 else "nonce",
                config,
            )
            print(json.dumps({"ok": ok}, ensure_ascii=False))
        except SignatureError as e:
            print(json.dumps({"ok": False, "reason": e.reason}, ensure_ascii=False))
    else:
        print(f"unknown cmd: {cmd}")
        sys.exit(1)
