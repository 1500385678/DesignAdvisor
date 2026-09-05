"""
DesignAdvisor · 飞书 bot 业务分发器(Phase 0 #4 飞书 bot 闭环核心)

职责:把飞书消息文本解析为命令,委托给本地后端,返回 1-3 条简版卡片文本。

支持的命令(本期 v0.1):
- help                  → 命令清单
- asset <关键词>       → 走 /api/v1/assets/search?q=
- dp <关键词>           → 走 /api/v1/dp/search?q=
- 裸关键词(无前缀)     → 默认走 asset 搜索(更常用)

输出格式(飞书消息 / 调试字符串):
- 命中 0:  "🔍 资产库 · button · 0 命中 · 试试:登录 主色 auth"
- 命中 N:  "🎨 资产库 · button · 5 命中
             ★ comp-button-primary-v0.1.0 (button, approved) score=18 命中:id×2,tags×1
             ★ comp-button-secondary-v0.1.0 (button, approved) score=14 命中:tags×1
             …"

不做什么(留待 Phase 1):
- 飞书卡片(本轮只回文本)
- 群 / 私聊区分(本轮统一入口)
- 命令限流 / 去重
"""

from __future__ import annotations

import os
from typing import Any, List, Tuple, Union

# 飞书消息最大长度(防截断)
FEISHU_MAX_LEN = 1500
# 卡片展示数量上限
HITS_DISPLAY_LIMIT = 3
# 支持的 format 取值
SUPPORTED_FORMATS = ("text", "card")


# ---------- 命令路由 ----------

def parse_command(text: str) -> Tuple[str, str]:
    """解析飞书消息文本,返回 (命令, 关键词)。

    规则:
    - "help" / "帮助" / "?" → ("help", "")
    - "asset 按钮" / "a 按钮" → ("asset", "按钮")
    - "dp 简约" / "知识 简约" → ("dp", "简约")
    - 裸 "按钮" → ("asset", "按钮")  ← 默认走资产,设计师用得多
    - 空白 / None → ("help", "")
    """
    if not text:
        return "help", ""
    s = text.strip()
    lower = s.lower()
    if lower in ("help", "帮助", "?", "？", "h"):
        return "help", ""
    # 显式前缀
    for prefix in ("asset ", "a ", "资产 ", "组件 "):
        if lower.startswith(prefix):
            return "asset", s[len(prefix):].strip()
    for prefix in ("dp ", "知识 ", "哲学 ", "规范 "):
        if lower.startswith(prefix):
            return "dp", s[len(prefix):].strip()
    # 裸关键词 → 默认 asset
    return "asset", s


# ---------- 后端调用(本地 HTTP) ----------

def _backend_base() -> str:
    """本地后端基址,默认 http://127.0.0.1:8000(用 127.0.0.1 避免 macOS localhost IPv6 解析问题)。"""
    return os.getenv("DESIGNADVISOR_API", "http://127.0.0.1:8000")


def _call_assets_search(q: str) -> dict:
    """调本地 /api/v1/assets/search?q=,返回 dict。

    失败 / 后端未启动:返回空 dict(由调用方降级为友好提示)。
    """
    try:
        import urllib.request
        import urllib.parse
        import json

        url = f"{_backend_base()}/api/v1/assets/search?q={urllib.parse.quote(q)}&limit=10"
        with urllib.request.urlopen(url, timeout=3) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return {}


def _call_dp_search(q: str) -> List[dict]:
    """调本地 /api/v1/dp/search?q=,返回 [dp, ...]。

    失败 / 后端未启动:返回空 list。
    """
    try:
        import urllib.request
        import urllib.parse
        import json

        url = f"{_backend_base()}/api/v1/dp/search?q={urllib.parse.quote(q)}"
        with urllib.request.urlopen(url, timeout=3) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return []


# ---------- 渲染(命中 → 飞书消息文本) ----------

def _render_asset_hits(query: str, data: dict) -> str:
    """渲染资产搜索结果(命中 → 飞书消息文本)。

    命中 0:友好提示
    命中 N:取前 3 条,每条一行 `★ id (kind, status) score=N 命中:fields×K`
    """
    if not data:
        return (
            f"🔍 资产库 · {query} · 后端未响应\n"
            f"  请确认 uvicorn api.main:app --port 8000 已启动"
        )
    total = data.get("total", 0)
    matched = data.get("matched", 0)
    if matched == 0:
        return (
            f"🔍 资产库 · {query} · 0 命中(总池 {total} 件)\n"
            f"  试试:登录 主色 auth 按钮 卡片"
        )
    assets = data.get("assets", [])[:HITS_DISPLAY_LIMIT]
    lines: List[str] = [f"🎨 资产库 · {query} · {matched}/{total} 命中"]
    for a in assets:
        mfields = ",".join(a.get("matched_fields", [])) or "?"
        lines.append(
            f"  ★ {a['id']} ({a['kind']}, {a['status']}) "
            f"score={a['score']} 命中:{mfields}"
        )
    if matched > HITS_DISPLAY_LIMIT:
        lines.append(f"  …还有 {matched - HITS_DISPLAY_LIMIT} 条,Web 看全部")
    return "\n".join(lines)


def _render_dp_hits(query: str, dps: List[dict]) -> str:
    """渲染 DP 搜索结果(命中 → 飞书消息文本)。"""
    if not dps:
        return (
            f"🔍 设计哲学 · {query} · 后端未响应\n"
            f"  请确认 uvicorn api.main:app --port 8000 已启动"
        )
    if not dps:
        return (
            f"🔍 设计哲学 · {query} · 0 命中\n"
            f"  试试:简约 用户体验 思想 DP-01"
        )
    lines: List[str] = [f"📚 设计哲学 · {query} · {len(dps)} 命中"]
    for dp in dps[:HITS_DISPLAY_LIMIT]:
        lines.append(f"  ★ {dp['id']} {dp['title']} [{dp['category']}] src={dp['source']}")
    return "\n".join(lines)


# ---------- 入口 ----------

def dispatch(text: str, format: str = "text") -> Union[str, dict]:
    """飞书 bot 消息分发入口。

    Args:
        text:   飞书消息原始文本(含 @bot 前缀也可,parse_command 已 strip 处理)
        format: 输出格式,可选 "text"(默认,纯文本,Phase 0 试运行)或 "card"
                (飞书交互卡片 dict,Phase 1 切真发时由 lark_client.send_card 投递)

    Returns:
        - format="text" → 纯文本(可能含多行 / emoji,1-3 条简版文本卡片)
        - format="card" → 飞书 interactive card dict(msg_type=interactive + card)
    """
    if format not in SUPPORTED_FORMATS:
        format = "text"

    cmd, keyword = parse_command(text)

    # 卡片化:help / 0 命中 / 后端未响应 都走 bot/card.py 渲染(Phase 1 飞书切真发时复用)
    if format == "card":
        from bot.card import (
            render_asset_card, render_dp_card, render_help_card,
        )
        if cmd == "help":
            return render_help_card()
        if not keyword:
            # 关键词缺失,降级为 help 卡片(更友好,纯文本会回 ⚠️)
            return render_help_card()
        if cmd == "asset":
            data = _call_assets_search(keyword)
            return render_asset_card(keyword, data)
        if cmd == "dp":
            dps = _call_dp_search(keyword)
            return render_dp_card(keyword, dps)
        return render_help_card()  # 未知命令降级 help 卡片

    if cmd == "help":
        return (
            "🤖 DesignAdvisor · 飞书 bot 命令清单\n"
            "  help             · 本清单\n"
            "  asset <关键词>   · 搜设计资产(组件/页面/令牌/参考)\n"
            "  dp <关键词>      · 搜设计哲学规范(24 条)\n"
            "  <关键词>         · 默认走 asset\n"
            "  示例:asset 按钮 / dp 简约 / 登录"
        )
    if not keyword:
        return "⚠️ 请提供关键词(例:asset 按钮 / dp 简约)"

    if cmd == "asset":
        data = _call_assets_search(keyword)
        return _render_asset_hits(keyword, data)
    if cmd == "dp":
        dps = _call_dp_search(keyword)
        return _render_dp_hits(keyword, dps)

    return f"⚠️ 未知命令:{cmd}"


# ---------- CLI 调试 ----------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法:python -m bot.search_handler '<消息文本>'")
        print("示例:python -m bot.search_handler 'asset button'")
        sys.exit(1)
    print(dispatch(sys.argv[1]))
