"""
DesignAdvisor · 飞书 bot 模块 (Phase 0 #4 闭环 + 飞书 bot 增强 1-5/5 + Phase 1 #2 评审通知 v0.1 完整版)

七个子模块:
- search_handler:命令分发(支持 asset / dp / help / search + format=text|card)
- lark_client:lark-cli 包装(subprocess 调用,dry_run 离线测试,send_text + send_card 双函数)
- webhook:FastAPI 路由接收飞书事件(URL 验签 / 限流 / 命中日志 / 解析 / 路由)
- signature:X-Lark-Signature HMAC-SHA256 验签(env-gated,dry_run 模式静默跳过)
- ratelimit:每 chat_id 独立 token bucket(env-gated,默认 1 rps / burst 3)
- live_send:切真发入口(probe_lark_cli + send_via_lark,先 probe 后 send)
- hit_log:命中日志(env-gated,纯本地 JSONL,5 设计师 dogfood 审计面)
- notify_reviews:评审飞书通知 v0.1 完整版(Phase 1 #2 切第四刀 0920 闭环,3 事件 created/transitioned/decided,直发 send_card 真卡片,api/reviews.py 3 端点埋点 + try/except 非阻塞)

触发流程:
  飞书群消息 → /api/v1/bot/webhook → bot.signature.verify
       ↓
  bot.ratelimit.acquire(chat_id) → 拒 → 200 + rate_limited note
       ↓
  search_handler.dispatch → 本地 /api/v1/assets/search 或 /api/v1/dp/search
       ↓
  lark_client.send_text → 飞书群回消息(text 或 card)
       ↓
  bot.hit_log.record(每条 webhook 落 1 行 JSONL,env-gated)

试运行切真发流程:
  配置 LARK_PROFILE + FEISHU_BOT_VERIFY_TOKEN + FEISHU_BOT_DRY_RUN=0
       ↓
  bot.live_send.probe_lark_cli(bin, profile) → --help 探活
       ↓
  bot.live_send.send_via_lark(text, chat_id) → 真正发飞书
"""

__version__ = "0.6.0"  # 0920 +notify_reviews v0.1 完整版(Phase 1 #2 切第四刀 闭环,send_card + api/reviews.py 端点埋点)
