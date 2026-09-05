"""
DesignAdvisor · 飞书 bot 交互卡片渲染器(Phase 1 #4 飞书 bot 增强 · 卡片化)

职责:把 search_handler 的命中结果(资产 / DP)渲染为飞书交互卡片 JSON dict,
     lark_client 真发时直接序列化为 message body 投递(留待 Phase 1 切真发时接)。

为什么是卡片(不只是文本):
- 命中结果 1-3 条带 ★ + score + 命中字段,纯文本堆叠在小屏/折叠场景可读性差
- 卡片"title + div 列表 + 底部 action 链接"三段式,视觉层级清晰
- 底部"查看全部"按钮直跳 Web /assets?q=,把飞书群当轻量入口,Web 当完整工作台

飞书 interactive card schema 参考:
https://open.larkoffice.com/document/uAjLw4CM/ukzMukzMukzM/feishu-cards/card-structure
本模块只生成"msg_type=interactive + card"体,真正发到飞书由 lark_client.send_card
(本轮 dry_run,只 print 不真发;Phase 1 切真发时接 lark-cli --card / lark SDK)。

支持的卡片形态:
- render_asset_card(query, search_resp)        → 资产搜索结果卡片
- render_dp_card(query, dp_list)               → DP 搜索结果卡片
- render_help_card()                           → 命令清单卡片
- render_no_match_card(query)                  → 0 命中友好提示卡片
- render_backend_down_card(query)              → 后端未响应卡片

不做什么(留待 Phase 1):
- 卡片交互回调(URL 跳转不算,本轮只静态渲染)
- 多模板切换(本轮统一 blue 模板)
- 富文本 markdown 复杂排版(本轮 plain_text + lark_md 够用)
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

# ---------- 配置 ----------

# 卡片展示数量上限(和 search_handler._render_asset_hits 保持一致,卡片化后也只前 3 条)
HITS_DISPLAY_LIMIT = 3

# Web 端基础地址(用于"查看全部"跳转链接)
WEB_BASE = os.getenv("DESIGNADVISOR_WEB", "http://127.0.0.1:3000")


# ---------- 通用组件工厂 ----------

def _header(title: str, template: str = "blue") -> Dict[str, Any]:
    """卡片头部(标题 + 模板色)。"""
    return {
        "title": {"tag": "plain_text", "content": title},
        "template": template,
    }


def _div_md(content: str) -> Dict[str, Any]:
    """一行 markdown 文本块(用于命中结果行)。"""
    return {
        "tag": "div",
        "text": {"tag": "lark_md", "content": content},
    }


def _note(content: str) -> Dict[str, Any]:
    """底部灰色注释行(用于"还有 N 条"等补充说明)。"""
    return {
        "tag": "note",
        "elements": [{"tag": "plain_text", "content": content}],
    }


def _action_button(text: str, url: str) -> Dict[str, Any]:
    """底部 action 按钮(用于"查看全部"跳转 Web)。"""
    return {
        "tag": "action",
        "actions": [
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": text},
                "type": "primary",
                "url": url,
            }
        ],
    }


# ---------- 资产搜索卡片 ----------

def render_asset_card(query: str, data: dict) -> Dict[str, Any]:
    """把 /api/v1/assets/search 的响应渲染为飞书资产搜索结果卡片。

    Args:
        query: 用户原始关键词
        data:  /api/v1/assets/search 的 JSON 响应({total, matched, query, tokens, assets})

    Returns:
        飞书 interactive card dict,字段形如:
        {
            "msg_type": "interactive",
            "card": {
                "header": {"title": ..., "template": "blue"},
                "elements": [
                    {"tag": "div", "text": ...},  # 1 命中 1 行
                    ...
                    {"tag": "note", ...},         # 底部注释
                    {"tag": "action", ...},       # 底部按钮
                ],
            },
        }

    行为:
    - data 为空 / 后端未响应 → render_backend_down_card
    - matched == 0          → render_no_match_card
    - matched > 0           → 头部 + 前 3 条 div + note(剩余条数) + action(查看全部)
    """
    if not data:
        return render_backend_down_card(query)

    total = data.get("total", 0)
    matched = data.get("matched", 0)
    assets = data.get("assets", [])

    if matched == 0:
        return render_no_match_card(query, hint_pool=total)

    title = f"🎨 资产库 · {query} · {matched}/{total} 命中"
    elements: List[Dict[str, Any]] = []

    for a in assets[:HITS_DISPLAY_LIMIT]:
        mfields = ",".join(a.get("matched_fields", [])) or "?"
        # 用 markdown 加粗 id / 灰显命中字段,卡片视觉层级: id > meta > 命中字段
        line = (
            f"**{a['id']}** "
            f"<font color='grey'>v{a['version']} · {a['kind']} · {a['status']}</font>\n"
            f"  · {a.get('purpose', '')[:60]}\n"
            f"  · score={a['score']} 命中:{mfields}"
        )
        elements.append(_div_md(line))

    if matched > HITS_DISPLAY_LIMIT:
        elements.append(_note(f"还有 {matched - HITS_DISPLAY_LIMIT} 条命中未展示,点下方按钮看全部"))

    # 底部跳转 Web(把 q 编码进 URL,Web /assets 消费 ?q=)
    import urllib.parse
    web_url = f"{WEB_BASE}/assets?q={urllib.parse.quote(query)}"
    elements.append(_action_button("🔗 在 Web 看全部", web_url))

    return {
        "msg_type": "interactive",
        "card": {
            "header": _header(title, template="blue"),
            "elements": elements,
        },
    }


# ---------- DP 搜索卡片 ----------

def render_dp_card(query: str, dps: List[dict]) -> Dict[str, Any]:
    """把 /api/v1/dp/search 的响应渲染为飞书 DP 搜索结果卡片。

    Args:
        query: 用户原始关键词
        dps:   [dp, ...]({id, title, category, source, ...})

    Returns:
        飞书 interactive card dict
    """
    if not dps:
        return render_backend_down_card(query, kind="dp")

    # 区分"后端未响应([] 是合法空命中)"——如果 dps 是空 list 且无 key 'id' 字段,降级为后端未响应
    # 简单实现:dps 为空 → 0 命中卡片(后端正常时也是空 list,需另判;本轮简化:dps 长度==0 一律当 0 命中)
    if len(dps) == 0:
        return render_no_match_card(query, kind="dp")

    title = f"📚 设计哲学 · {query} · {len(dps)} 命中"
    elements: List[Dict[str, Any]] = []
    for dp in dps[:HITS_DISPLAY_LIMIT]:
        line = (
            f"**{dp['id']} {dp['title']}**\n"
            f"  · 分类:{dp.get('category', '?')} · 来源:{dp.get('source', '?')}"
        )
        elements.append(_div_md(line))

    if len(dps) > HITS_DISPLAY_LIMIT:
        elements.append(_note(f"还有 {len(dps) - HITS_DISPLAY_LIMIT} 条命中未展示"))

    import urllib.parse
    web_url = f"{WEB_BASE}/dp?q={urllib.parse.quote(query)}"
    elements.append(_action_button("🔗 在 Web 看全部", web_url))

    return {
        "msg_type": "interactive",
        "card": {
            "header": _header(title, template="purple"),
            "elements": elements,
        },
    }


# ---------- 通用卡片(0 命中 / 后端未响应 / help) ----------

def render_no_match_card(query: str, kind: str = "asset", hint_pool: Optional[int] = None) -> Dict[str, Any]:
    """0 命中友好提示卡片(给用户备选关键词)。"""
    title = f"🔍 {'资产库' if kind == 'asset' else '设计哲学'} · {query} · 0 命中"
    pool_note = f" (总池 {hint_pool} 件)" if hint_pool and kind == "asset" else ""
    hints = {
        "asset": "试试:登录 主色 auth 按钮 卡片",
        "dp": "试试:简约 用户体验 思想 DP-01",
    }
    elements: List[Dict[str, Any]] = [
        _div_md(f"未找到匹配结果{pool_note}"),
        _div_md(f"💡 {hints.get(kind, hints['asset'])}"),
    ]
    return {
        "msg_type": "interactive",
        "card": {
            "header": _header(title, template="grey"),
            "elements": elements,
        },
    }


def render_backend_down_card(query: str, kind: str = "asset") -> Dict[str, Any]:
    """后端未响应卡片(友好提示 + 排查建议,不暴露内部 stack)。"""
    title = f"⚠️ {'资产库' if kind == 'asset' else '设计哲学'} · {query} · 后端未响应"
    elements: List[Dict[str, Any]] = [
        _div_md("本地后端未响应或超时(3s 兜底)"),
        _div_md("💡 请确认 `uvicorn api.main:app --port 8000` 已启动"),
        _div_md("💡 或检查 `DESIGNADVISOR_API` 环境变量"),
    ]
    return {
        "msg_type": "interactive",
        "card": {
            "header": _header(title, template="red"),
            "elements": elements,
        },
    }


def render_help_card() -> Dict[str, Any]:
    """命令清单卡片(给 help 命令专用)。"""
    elements: List[Dict[str, Any]] = [
        _div_md("**🤖 DesignAdvisor · 飞书 bot 命令清单**"),
        _div_md("· `help` — 本卡片"),
        _div_md("· `asset <关键词>` — 搜设计资产(组件/页面/令牌/参考)"),
        _div_md("· `dp <关键词>` — 搜设计哲学规范(24 条)"),
        _div_md("· `<关键词>` — 默认走 asset"),
        _div_md("· 示例:`asset 按钮` / `dp 简约` / `登录`"),
        _note("本轮默认 dry_run,只 print 不真发;真发前显式 FEISHU_BOT_DRY_RUN=0"),
    ]
    return {
        "msg_type": "interactive",
        "card": {
            "header": _header("🤖 DesignAdvisor · 命令清单", template="blue"),
            "elements": elements,
        },
    }


# ---------- CLI 调试 ----------

if __name__ == "__main__":
    import json
    import sys

    # CLI 用法:
    #   python -m bot.card help
    #   python -m bot.card asset button
    #   python -m bot.card dp 简约
    #   python -m bot.card no_match button
    #   python -m bot.card down asset
    if len(sys.argv) < 2:
        print("用法:python -m bot.card <help|asset|dp|no_match|down> [query]")
        sys.exit(1)

    mode = sys.argv[1]
    if mode == "help":
        print(json.dumps(render_help_card(), ensure_ascii=False, indent=2))
    elif mode == "asset":
        # 模拟 3 条命中(用于卡片结构可视化)
        fake_data = {
            "total": 133,
            "matched": 5,
            "query": sys.argv[2] if len(sys.argv) > 2 else "button",
            "tokens": ["button"],
            "assets": [
                {
                    "id": "comp-button-primary-v0.1.0",
                    "kind": "component",
                    "version": "0.1.0",
                    "status": "approved",
                    "purpose": "主按钮,用于主操作 CTA,品牌色填充,圆角 6px",
                    "score": 18.0,
                    "matched_fields": ["id", "tags"],
                },
                {
                    "id": "comp-button-secondary-v0.1.0",
                    "kind": "component",
                    "version": "0.1.0",
                    "status": "approved",
                    "purpose": "次按钮,用于辅助操作,描边样式,品牌色描边",
                    "score": 14.0,
                    "matched_fields": ["tags"],
                },
                {
                    "id": "comp-button-ghost-v0.1.0",
                    "kind": "component",
                    "version": "0.1.0",
                    "status": "draft",
                    "purpose": "幽灵按钮,用于不强调的次要操作,无背景无描边",
                    "score": 10.0,
                    "matched_fields": ["tags"],
                },
            ],
        }
        print(json.dumps(render_asset_card(sys.argv[2] if len(sys.argv) > 2 else "button", fake_data),
                         ensure_ascii=False, indent=2))
    elif mode == "dp":
        fake_dps = [
            {"id": "DP-01", "title": "少即是多", "category": "哲学", "source": "Dieter Rams"},
            {"id": "DP-02", "title": "用户中心", "category": "方法", "source": "Don Norman"},
        ]
        print(json.dumps(render_dp_card(sys.argv[2] if len(sys.argv) > 2 else "简约", fake_dps),
                         ensure_ascii=False, indent=2))
    elif mode == "no_match":
        print(json.dumps(render_no_match_card(sys.argv[2] if len(sys.argv) > 2 else "button"),
                         ensure_ascii=False, indent=2))
    elif mode == "down":
        print(json.dumps(render_backend_down_card(sys.argv[2] if len(sys.argv) > 2 else "button"),
                         ensure_ascii=False, indent=2))
    else:
        print(f"未知 mode:{mode}")
        sys.exit(1)
