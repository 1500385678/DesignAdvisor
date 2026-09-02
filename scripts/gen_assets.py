#!/usr/bin/env python3
"""
DesignAdvisor · 命名空间批量生成脚本 v0.1

用途
----
从 `docs/04-可入库资产清单_v0.1.md` 的 4 类资产骨架(组件 32 / 页面 19 /
令牌 ~73 / 参考开放)批量生成 fake-load stub,字段对齐
`docs/02-设计资产元数据-schema.md` v0.1 §2/§5 约定,作为 Phase 1 #1
资产库 MVP 32+19+73 全量回填的工程前置。

不做什么(本脚本边界)
--------------------
- 不动现有 8 件 fake-load(它们是手工详细写的"代表作",id 用
  `comp-button-primary-v0.1.0` kebab-case);本脚本只生成 130 件 stub
- 不动 docs/04 markdown(只读)
- 不真实拉 Figma(等 Phase 0 #3 OAuth)
- 不写后端代码(本脚本只产出 `api/assets_stub.json`,由 `api/assets.py`
  加载时合并进 `_ASSET_CATALOG`)

命名约定(对齐 docs/04 §8)
------------------------
- id 前缀: `stub-` 标识本脚本批量产物,与手工 fake-load 8 件 kebab-case 区分
- 命名空间: `<kind>/<category>/<sub>` 段式,如 `comp/button/primary`
- version: 全量 0.1.0(初始入库,首次评审通过后跳 1.0.0)
- status: 组件/令牌默认 `approved`,页面默认 `draft`,参考默认 `approved`
- purpose: 自动从子项名生成,stub 阶段占位(≤140 字)
- tags: 全小写,逗号分隔数组,默认 `[category, kind, sub]`
- figma_ref: 组件/页面/令牌 = `PENDING_OAUTH`,参考 = `null`
- code_ref: 组件 = `packages/ui/src/<PascalName>.tsx`,令牌 = `packages/tokens/src/<kebab>.json`
- reviewers: 默认 `[feishu:owner-design, feishu:owner-frontend]`

用法
----
    python3 scripts/gen_assets.py
    # 输出: api/assets_stub.json + stdout 校验表
    #       组件 32 / 页面 19 / 令牌 73 / 参考 6 = 130 件
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Any

# ---------- 路径常量 ----------

REPO_ROOT = Path(__file__).resolve().parent.parent
DOC_04 = REPO_ROOT / "docs" / "04-可入库资产清单_v0.1.md"
OUT_JSON = REPO_ROOT / "api" / "assets_stub.json"

# ---------- 命名空间表(从 docs/04 §3-§6 抽) ----------

# 组件类(§3):32 件 = 5 + 6 + 6 + 5 + 5 + 5
COMPONENTS: List[Dict[str, Any]] = [
    {"category": "button", "items": ["primary", "secondary", "text", "danger", "loading"], "count": 5},
    {"category": "form", "items": ["input", "textarea", "radio", "checkbox", "switch", "select"], "count": 6},
    {"category": "feedback", "items": ["modal", "drawer", "toast", "alert", "loading", "empty"], "count": 6},
    {"category": "nav", "items": ["topbar", "sidebar", "breadcrumb", "pagination", "tabs"], "count": 5},
    {"category": "data", "items": ["table", "card", "list", "stat-card", "chart-frame"], "count": 5},
    {"category": "typography", "items": ["heading", "paragraph", "quote", "list", "code-block"], "count": 5},
]
COMPONENT_TOTAL = sum(c["count"] for c in COMPONENTS)  # 32

# 页面类(§4):19 件 = 4 + 3 + 3 + 5 + 4
PAGES: List[Dict[str, Any]] = [
    {"category": "auth", "items": ["login", "register", "forgot-password", "two-factor"], "count": 4},
    {"category": "overview", "items": ["home", "dashboard", "workspace"], "count": 3},
    {"category": "content", "items": ["list", "detail", "search-result"], "count": 3},
    {"category": "flow", "items": ["onboarding", "empty-state", "error-page", "404", "500"], "count": 5},
    {"category": "settings", "items": ["profile", "team", "billing", "notification"], "count": 4},
]
PAGE_TOTAL = sum(c["count"] for c in PAGES)  # 19

# 令牌类(§5):~73 条
TOKENS: List[Dict[str, Any]] = [
    # color ~25(brand 2 + text 5 + bg 4 + border 4 + state 6 + 杂 4)
    {"category": "color", "items": [
        "brand-primary", "brand-secondary",
        "text-primary", "text-secondary", "text-tertiary", "text-disabled", "text-inverse",
        "bg-canvas", "bg-surface", "bg-elevated", "bg-overlay",
        "border-default", "border-strong", "border-focus", "border-divider",
        "state-success", "state-warning", "state-error", "state-info", "state-hover", "state-active",
        "neutral-50", "neutral-100", "neutral-500", "neutral-900",
    ], "count": 25},
    # font-size 8
    {"category": "font-size", "items": ["xs", "sm", "base", "lg", "xl", "2xl", "3xl", "4xl"], "count": 8},
    # font-weight 4
    {"category": "font-weight", "items": ["regular", "medium", "semibold", "bold"], "count": 4},
    # line-height 3
    {"category": "line-height", "items": ["tight", "normal", "relaxed"], "count": 3},
    # spacing 9
    {"category": "spacing", "items": ["0", "1", "2", "3", "4", "6", "8", "12", "16"], "count": 9},
    # radius 8
    {"category": "radius", "items": ["none", "sm", "base", "md", "lg", "xl", "2xl", "full"], "count": 8},
    # shadow 8
    {"category": "shadow", "items": ["xs", "sm", "base", "md", "lg", "xl", "2xl", "inner"], "count": 8},
    # opacity 8
    {"category": "opacity", "items": ["0", "5", "10", "20", "40", "60", "80", "100"], "count": 8},
]
TOKEN_TOTAL = sum(c["count"] for c in TOKENS)  # 73

# 参考类(§6):开放,本脚本首批取 7 件代表(竞品 3 / 灵感 2 / 大师 2)
REFERENCES: List[Dict[str, Any]] = [
    {"category": "competitor", "items": ["feishu-chat", "notion-workspace", "figma-editor"], "count": 3},
    {"category": "inspiration", "items": ["dribbble-shot-01", "awwwards-site-01"], "count": 2},
    {"category": "master", "items": ["dieter-rams-braun", "kenya-hara-muji"], "count": 2},
]
REFERENCE_TOTAL = sum(c["count"] for c in REFERENCES)  # 7

# 已被 `api/assets.py` 8 件 fake-load 占用的子项,stub 跳过(避免重叠)
# 映射:`<category>/<sub>`
MANUAL_SUBS: set = {
    "button/primary",     # comp-button-primary-v0.1.0
    "form/input",         # comp-form-input-v0.1.0
    "auth/login",         # page-auth-login-v0.1.0
    "overview/dashboard", # page-overview-dashboard-v0.1.0
    "color/brand-primary",# token-color-brand-primary-v0.1.0
    "spacing/4",          # token-spacing-4-v0.1.0
    "competitor/dingtalk-chat",  # ref-dingtalk-chat-v0.1.0
    "inspiration/linear-issue",  # ref-linear-issue-v0.1.0
}

# ---------- 字段填充函数 ----------


def _to_pascal(name: str) -> str:
    """kebab-case → PascalCase,如 primary-button → PrimaryButton"""
    return "".join(s.capitalize() for s in name.split("-"))


def _gen_component(category: str, sub: str) -> Dict[str, Any]:
    pascal = _to_pascal(sub)
    return {
        "id": f"stub-comp-{category}-{sub}-v0.1.0",
        "kind": "component",
        "version": "0.1.0",
        "status": "approved",
        "category": category,
        "purpose": f"[stub] {category} 类组件 / {sub} · 字段待 OAuth 后回填;占位 purpose",
        "tags": [category, "component", sub],
        "code_ref": [f"packages/ui/src/{pascal}.tsx"],
        "figma_ref": "PENDING_OAUTH",
        "reviewers": ["feishu:owner-design", "feishu:owner-frontend"],
    }


def _gen_page(category: str, sub: str) -> Dict[str, Any]:
    return {
        "id": f"stub-page-{category}-{sub}-v0.1.0",
        "kind": "page",
        "version": "0.1.0",
        "status": "draft",
        "category": category,
        "purpose": f"[stub] {category} 页面 / {sub} · 整页设计稿待 OAuth 后拉取;占位 purpose",
        "tags": [category, "page", sub],
        "code_ref": [f"apps/web/app/({category})/{sub}/page.tsx"],
        "figma_ref": "PENDING_OAUTH",
        "reviewers": ["feishu:owner-design", "feishu:owner-product"],
    }


def _gen_token(category: str, sub: str) -> Dict[str, Any]:
    code_ref_path = f"packages/tokens/src/{category}.json#{sub}"
    return {
        "id": f"stub-token-{category}-{sub}-v0.1.0",
        "kind": "token",
        "version": "0.1.0",
        "status": "approved",
        "category": category,
        "purpose": f"[stub] {category} 令牌 / {sub} · 数值待 Style Dictionary 同步;占位 purpose",
        "tags": [category, "token", sub],
        "code_ref": [code_ref_path],
        "figma_ref": "PENDING_OAUTH",
        "reviewers": ["feishu:owner-brand", "feishu:owner-frontend"],
    }


def _gen_reference(category: str, sub: str) -> Dict[str, Any]:
    return {
        "id": f"stub-ref-{category}-{sub}-v0.1.0",
        "kind": "reference",
        "version": "0.1.0",
        "status": "approved",
        "category": category,
        "purpose": f"[stub] {category} 参考 / {sub} · 外部 URL 待设计师提交;占位 purpose",
        "tags": [category, "reference", sub],
        "code_ref": [],
        "figma_ref": None,  # 参考类不要求 figma_ref(02-schema §6)
        "reviewers": ["feishu:owner-design"],
        "external_ref": None,  # 02-schema v0.2 待补字段
    }


# ---------- 主流程 ----------


def main() -> int:
    if not DOC_04.exists():
        print(f"ERROR: 找不到 {DOC_04}", file=sys.stderr)
        return 1

    assets: List[Dict[str, Any]] = []
    by_kind: Dict[str, int] = {"component": 0, "page": 0, "token": 0, "reference": 0}
    skipped: List[str] = []  # 记录被跳过的子项(对应 manual fake-load)

    # 组件
    for cat in COMPONENTS:
        for sub in cat["items"]:
            if f"{cat['category']}/{sub}" in MANUAL_SUBS:
                skipped.append(f"component/{cat['category']}/{sub}")
                continue
            assets.append(_gen_component(cat["category"], sub))
            by_kind["component"] += 1

    # 页面
    for cat in PAGES:
        for sub in cat["items"]:
            if f"{cat['category']}/{sub}" in MANUAL_SUBS:
                skipped.append(f"page/{cat['category']}/{sub}")
                continue
            assets.append(_gen_page(cat["category"], sub))
            by_kind["page"] += 1

    # 令牌
    for cat in TOKENS:
        for sub in cat["items"]:
            if f"{cat['category']}/{sub}" in MANUAL_SUBS:
                skipped.append(f"token/{cat['category']}/{sub}")
                continue
            assets.append(_gen_token(cat["category"], sub))
            by_kind["token"] += 1

    # 参考
    for cat in REFERENCES:
        for sub in cat["items"]:
            if f"{cat['category']}/{sub}" in MANUAL_SUBS:
                skipped.append(f"reference/{cat['category']}/{sub}")
                continue
            assets.append(_gen_reference(cat["category"], sub))
            by_kind["reference"] += 1

    total = len(assets)

    # 校验:stub 数量 = docs/04 命名空间目标 - manual fake-load 占用
    expected_stub = {
        "component": COMPONENT_TOTAL - sum(1 for s in skipped if s.startswith("component/")),
        "page": PAGE_TOTAL - sum(1 for s in skipped if s.startswith("page/")),
        "token": TOKEN_TOTAL - sum(1 for s in skipped if s.startswith("token/")),
        "reference": REFERENCE_TOTAL - sum(1 for s in skipped if s.startswith("reference/")),
    }
    if by_kind != expected_stub:
        print(
            f"ERROR: 数量不符 实际 {by_kind} 预期 {expected_stub}",
            file=sys.stderr,
        )
        return 1

    # 写 JSON
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "0.1.0",
        "doc_source": "docs/04-可入库资产清单_v0.1.md",
        "field_alignment": "docs/02-设计资产元数据-schema.md v0.1",
        "stub_marker": "stub-",
        "manual_assets_count": 8,  # 8 件 fake-load 在 api/assets.py
        "skipped_manual_subs": skipped,
        "total": total,
        "by_kind": by_kind,
        "namespace_target": {
            "component": COMPONENT_TOTAL,
            "page": PAGE_TOTAL,
            "token": TOKEN_TOTAL,
            "reference": REFERENCE_TOTAL,
        },
        "merged_total_with_manual": total + 8,  # stub + manual fake-load
        "assets": assets,
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # 校验输出
    print(f"✓ 写出 {OUT_JSON.relative_to(REPO_ROOT)} · {total} 件 stub (跳过 {len(skipped)} 件 manual 占用)")
    print(f"  组件 {by_kind['component']}/{COMPONENT_TOTAL}  (skip {sum(1 for s in skipped if s.startswith('component/'))})")
    print(f"  页面 {by_kind['page']}/{PAGE_TOTAL}  (skip {sum(1 for s in skipped if s.startswith('page/'))})")
    print(f"  令牌 {by_kind['token']}/{TOKEN_TOTAL}  (skip {sum(1 for s in skipped if s.startswith('token/'))})")
    print(f"  参考 {by_kind['reference']}/{REFERENCE_TOTAL}  (skip {sum(1 for s in skipped if s.startswith('reference/'))})")
    print(f"  stub 合计 {total} · 合并 manual 8 件 → {total + 8} 件 = docs/04 §2-§6 命名空间目标")
    print()
    print("前 3 件样本:")
    for a in assets[:3]:
        print(f"  {a['id']} ({a['kind']}/{a['category']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
