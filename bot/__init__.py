"""
DesignAdvisor · 飞书 bot 模块 (Phase 0 #4 闭环 + 飞书 bot 增强 1-3/3)

四个子模块:
- search_handler:命令分发(支持 asset / dp / help / search + format=text|card)
- lark_client:lark-cli 包装(subprocess 调用,dry_run 离线测试)
- webhook:FastAPI 路由接收飞书事件(URL 验签 / 限流 / 解析 / 路由)
- signature:X-Lark-Signature HMAC-SHA256 验签(env-gated,dry_run 模式静默跳过)
- ratelimit:每 chat_id 独立 token bucket(env-gated,默认 1 rps / burst 3)

触发流程:
  飞书群消息 → /api/v1/bot/webhook → bot.signature.verify
       ↓
  bot.ratelimit.acquire(chat_id) → 拒 → 200 + rate_limited note
       ↓
  search_handler.dispatch → 本地 /api/v1/assets/search 或 /api/v1/dp/search
       ↓
  lark_client.send_text → 飞书群回消息(text 或 card)
"""

__version__ = "0.3.0"
