"""
DesignAdvisor · 资产库后端 v0.1 (Phase 1 #1 资产库 MVP 第一刀)

按 `docs/04-可入库资产清单_v0.1.md` §3-§6 的 4 类资产骨架 fake-load 8 件代表
(每类 2 件),对齐 `docs/02-设计资产元数据-schema.md` v0.1 字段约定。

端点:
- GET /api/v1/assets                 列出资产(支持 ?kind / ?category / ?status 过滤)
- GET /api/v1/assets/summary         4 类计数 + 命名空间摘要(前端 Dashboard 用)

Fake-load 范围(8 件):
- component 2 件:  comp-button-primary / comp-form-input
- page 2 件:       page-auth-login / page-overview-dashboard
- token 2 件:      token-color-brand-primary / token-spacing-4
- reference 2 件:  ref-dingtalk-chat / ref-linear-issue

不做什么(留待后续 T1-T5 任务):
- 32+19+73+开放 件全量回填(本端点只是 fake-load 形状,OAuth 接入后遍历入库)
- 真实 Figma 拉取(等 Phase 0 #3 OAuth)
- POST/PUT/DELETE(只读 v0.1,Phase 1 #1 后段加写入)
- 视觉相似度 hash(Phase 2 CLIP)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/assets", tags=["assets"])

# 8 件 fake-load 资产(每类 2 件)
# 数据源:docs/04-可入库资产清单_v0.1.md §3-§6
# 字段口径:docs/02-设计资产元数据-schema.md §2/§5
# id 命名:按 §8 决策"按 kind 加前缀" · comp-/page-/token-/ref- 三段式
_ASSET_CATALOG: List[dict] = [
    # ----- component · §3 组件类 -----
    {
        "id": "comp-button-primary-v0.1.0",
        "kind": "component",
        "version": "0.1.0",
        "status": "approved",
        "category": "button",
        "purpose": "主操作按钮,用于页面级正向动作(提交/确认/下一步)",
        "tags": ["button", "primary", "action"],
        "code_ref": ["packages/ui/src/Button.tsx#primary"],
        "figma_ref": "PENDING_OAUTH",
        "reviewers": ["feishu:owner-design", "feishu:owner-frontend"],
    },
    {
        "id": "comp-form-input-v0.1.0",
        "kind": "component",
        "version": "0.1.0",
        "status": "approved",
        "category": "form",
        "purpose": "单行文本输入框,支持受控/非受控,前后置插槽,错误态",
        "tags": ["form", "input", "text"],
        "code_ref": ["packages/ui/src/Input.tsx"],
        "figma_ref": "PENDING_OAUTH",
        "reviewers": ["feishu:owner-design", "feishu:owner-frontend"],
    },
    # ----- page · §4 页面类 -----
    {
        "id": "page-auth-login-v0.1.0",
        "kind": "page",
        "version": "0.1.0",
        "status": "draft",
        "category": "auth",
        "purpose": "登录页 · 邮箱+密码主流程,支持 SSO 二级入口",
        "tags": ["auth", "login", "sso"],
        "code_ref": ["apps/web/app/(auth)/login/page.tsx"],
        "figma_ref": "PENDING_OAUTH",
        "reviewers": ["feishu:owner-design", "feishu:owner-product"],
    },
    {
        "id": "page-overview-dashboard-v0.1.0",
        "kind": "page",
        "version": "0.1.0",
        "status": "in_review",
        "category": "overview",
        "purpose": "工作台首页 · 展示用户关键指标卡 + 今日待办 + 快捷入口",
        "tags": ["dashboard", "overview", "home"],
        "code_ref": ["apps/web/app/(workspace)/dashboard/page.tsx"],
        "figma_ref": "PENDING_OAUTH",
        "reviewers": ["feishu:owner-design", "feishu:owner-product", "feishu:owner-frontend"],
    },
    # ----- token · §5 令牌类 -----
    {
        "id": "token-color-brand-primary-v0.1.0",
        "kind": "token",
        "version": "0.1.0",
        "status": "approved",
        "category": "color",
        "purpose": "品牌主色,用于关键 CTA / 品牌强调 / 高亮态,全局生效",
        "tags": ["color", "brand", "primary"],
        "code_ref": ["packages/tokens/src/color.json#brand.primary"],
        "figma_ref": "PENDING_OAUTH",
        "reviewers": ["feishu:owner-brand", "feishu:owner-frontend"],
    },
    {
        "id": "token-spacing-4-v0.1.0",
        "kind": "token",
        "version": "0.1.0",
        "status": "approved",
        "category": "spacing",
        "purpose": "标准间距 16px,用于组件内边距 / 卡片间距 / 中等段落间距",
        "tags": ["spacing", "base"],
        "code_ref": ["packages/tokens/src/spacing.json#4"],
        "figma_ref": "PENDING_OAUTH",
        "reviewers": ["feishu:owner-design", "feishu:owner-frontend"],
    },
    # ----- reference · §6 参考类 -----
    {
        "id": "ref-dingtalk-chat-v0.1.0",
        "kind": "reference",
        "version": "0.1.0",
        "status": "approved",
        "category": "competitor",
        "purpose": "钉钉聊天列表视觉决策参考 · 消息密度 / 时间分组 / 已读状态",
        "tags": ["competitor", "chat", "list"],
        "code_ref": [],
        "figma_ref": None,  # 参考类不要求 figma_ref(02-schema §6)
        "reviewers": ["feishu:owner-design"],
    },
    {
        "id": "ref-linear-issue-v0.1.0",
        "kind": "reference",
        "version": "0.1.0",
        "status": "approved",
        "category": "inspiration",
        "purpose": "Linear Issue 视图参考 · 键盘流 / 状态机 / 极简信息层级",
        "tags": ["inspiration", "issue", "keyboard"],
        "code_ref": [],
        "figma_ref": None,
        "reviewers": ["feishu:owner-design"],
    },
]

# fake-load 时间戳(全部 8 件同时间落库)
_FAKE_LOAD_TS = datetime(2026, 9, 1, 3, 20, 0, tzinfo=timezone.utc)
_PLACEHOLDER_USER = "feishu:placeholder"  # Phase 0 #3 OAuth 接入后回填真实 user_ref


class AssetSummary(BaseModel):
    """单个资产的简化摘要(列表/卡片展示用)"""

    id: str
    kind: str
    version: str
    status: str
    category: str
    purpose: str
    tags: List[str]
    code_ref_count: int = Field(..., description="关联代码引用数量,0=无")
    figma_synced: bool = Field(..., description="Figma 是否已同步(OAuth 后才有真实值)")


class AssetDetail(BaseModel):
    """单个资产完整元数据(详情页/评审用)"""

    id: str
    kind: str
    version: str
    status: str
    category: str
    purpose: str
    tags: List[str]
    code_ref: List[str]
    figma_ref: Optional[str] = None
    reviewers: List[str]
    author: str
    owner: str
    created_at: str
    updated_at: str


class AssetsResponse(BaseModel):
    """资产列表响应"""

    total: int
    returned: int
    assets: List[AssetSummary]


class AssetsSummaryResponse(BaseModel):
    """4 类资产计数摘要"""

    total: int
    by_kind: dict
    by_category: dict
    namespaces: dict = Field(
        ..., description="4 类命名空间预期量(对齐 docs/04 §3-§6 表格小计)"
    )


def _to_summary(asset: dict) -> AssetSummary:
    return AssetSummary(
        id=asset["id"],
        kind=asset["kind"],
        version=asset["version"],
        status=asset["status"],
        category=asset["category"],
        purpose=asset["purpose"],
        tags=asset["tags"],
        code_ref_count=len(asset.get("code_ref", [])),
        figma_synced=asset.get("figma_ref") not in (None, "PENDING_OAUTH"),
    )


def _to_detail(asset: dict) -> AssetDetail:
    return AssetDetail(
        id=asset["id"],
        kind=asset["kind"],
        version=asset["version"],
        status=asset["status"],
        category=asset["category"],
        purpose=asset["purpose"],
        tags=asset["tags"],
        code_ref=asset.get("code_ref", []),
        figma_ref=asset.get("figma_ref"),
        reviewers=asset.get("reviewers", []),
        author=_PLACEHOLDER_USER,
        owner=_PLACEHOLDER_USER,
        created_at=_FAKE_LOAD_TS.isoformat(),
        updated_at=_FAKE_LOAD_TS.isoformat(),
    )


@router.get(
    "",
    response_model=AssetsResponse,
    summary="列出资产(支持 ?kind / ?category / ?status 过滤)",
)
def list_assets(
    kind: Optional[str] = Query(
        default=None,
        description="资产类型,可选值: component / page / token / reference",
    ),
    category: Optional[str] = Query(
        default=None,
        description="子分类,例如 component 类下 button/form/feedback/nav/data/typography",
    ),
    status: Optional[str] = Query(
        default=None,
        description="状态过滤,可选值: draft / in_review / approved / deprecated / archived",
    ),
) -> AssetsResponse:
    """列出全部 4 类资产,支持三种维度过滤。

    v0.1 仅 fake-load 8 件(每类 2 件),OAuth 接入后按 docs/04 §3-§6 命名空间
    全量回填到 32+19+73+开放 件。
    """
    filtered = _ASSET_CATALOG
    if kind is not None:
        filtered = [a for a in filtered if a["kind"] == kind]
    if category is not None:
        filtered = [a for a in filtered if a["category"] == category]
    if status is not None:
        filtered = [a for a in filtered if a["status"] == status]

    summaries = [_to_summary(a) for a in filtered]
    return AssetsResponse(
        total=len(_ASSET_CATALOG),
        returned=len(summaries),
        assets=summaries,
    )


@router.get(
    "/summary",
    response_model=AssetsSummaryResponse,
    summary="4 类资产计数 + 命名空间摘要(前端 Dashboard 用)",
)
def assets_summary() -> AssetsSummaryResponse:
    """返回 4 类资产当前 fake-load 数量 + docs/04 §3-§6 预期命名空间小计。

    用法:前端 Dashboard 渲染 "组件 2/32 · 页面 2/19 · 令牌 2/73 · 参考 2/开放"
    """
    by_kind: dict = {}
    by_category: dict = {}
    for a in _ASSET_CATALOG:
        by_kind[a["kind"]] = by_kind.get(a["kind"], 0) + 1
        key = f"{a['kind']}/{a['category']}"
        by_category[key] = by_category.get(key, 0) + 1

    return AssetsSummaryResponse(
        total=len(_ASSET_CATALOG),
        by_kind=by_kind,
        by_category=by_category,
        namespaces={
            "component": {"current": by_kind.get("component", 0), "target": 32, "note": "30-60 件区间"},
            "page": {"current": by_kind.get("page", 0), "target": 19, "note": "15-30 件区间"},
            "token": {"current": by_kind.get("token", 0), "target": 73, "note": "40-80 条区间"},
            "reference": {"current": by_kind.get("reference", 0), "target": None, "note": "开放,无上限"},
        },
    )


@router.get(
    "/{asset_id}",
    response_model=AssetDetail,
    summary="按 ID 查单个资产完整元数据",
)
def get_asset(asset_id: str) -> AssetDetail:
    """按 ID 查单个资产完整元数据,用于详情页/评审页面。"""
    for a in _ASSET_CATALOG:
        if a["id"] == asset_id:
            return _to_detail(a)
    from fastapi import HTTPException

    raise HTTPException(status_code=404, detail=f"asset not found: {asset_id}")
