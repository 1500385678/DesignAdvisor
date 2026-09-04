"""
DesignAdvisor · 飞书 bot 模块 (Phase 0 #4 闭环)

三个子模块:
- search_handler:命令分发(支持 asset / dp / help / search)
- lark_client:lark-cli 包装(subprocess 调用,dry_run 离线测试)
- webhook:FastAPI 路由接收飞书事件(验签 / 解析 / 路由)

触发流程:
  飞书群消息 → /api/v1/bot/webhook → search_handler.dispatch
       ↓
  本地 /api/v1/assets/search 或 /api/v1/dp/search
       ↓
  lark_client.send_text → 飞书群回消息
"""

__version__ = "0.1.0"
