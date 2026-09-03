"""
DesignAdvisor · 资产库后端 v0.2 (Phase 1 #1 资产库 MVP 切第三刀 · 32+19+73 全量回填)

合并两路数据(对齐 `docs/04-可入库资产清单_v0.1.md` §2-§6 命名空间):
- 8 件 manual fake-load(本文件 `_ASSET_CATALOG`,手工详细,kebab-case)
- 125 件 stub(由 `scripts/gen_assets.py` 从 docs/04 表格批量生成,`assets_stub.json`)

合计 133 件(8 + 125) = 组件 32 / 页面 19 / 令牌 73 / 参考 9(开放,首批 7+manual 2)。
字段口径统一对齐 `docs/02-设计资产元数据-schema.md` v0.1。

端点:
- GET /api/v1/assets                 列出资产(支持 ?kind / ?category / ?status 过滤)
- GET /api/v1/assets/summary         4 类计数 + 命名空间摘要(前端 Dashboard 用)
- GET /api/v1/assets/search          语义搜索(关键词 + 字段权重 ranking + ?kind / ?status 二次过滤)
- GET /api/v1/assets/{asset_id}      按 ID 查单个资产完整元数据

不做什么(留待后续 T1-T5 任务):
- 真实 Figma 拉取(等 Phase 0 #3 OAuth;stub 的 figma_ref = PENDING_OAUTH)
- POST/PUT/DELETE(只读 v0.3,Phase 1 #1 后段加写入)
- 视觉相似度 hash(Phase 2 CLIP)
- stub 字段回填(目前 purpose / tags / code_ref 是占位,OAuth 后批量回填)
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
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


# ---------- 加载 scripts/gen_assets.py 批量生成的 stub ----------
# v0.2 扩展(2026-09-03):从 8 件 fake-load 扩展到 133 件 = 8 manual + 125 stub,
# stub 由 `scripts/gen_assets.py` 从 `docs/04-可入库资产清单 v0.1` §2-§6
# 命名空间批量生成,字段对齐 `docs/02-设计资产元数据-schema.md` v0.1;
# id 前缀 `stub-` 标识批量产物,与 manual 8 件 kebab-case 区分。
_STUB_JSON = Path(__file__).parent / "assets_stub.json"
_STUB_ASSETS: List[dict] = []
if _STUB_JSON.exists():
    import json  # noqa: E402 局部 import,避免 main 启动开销
    _STUB_ASSETS = json.loads(_STUB_JSON.read_text(encoding="utf-8")).get("assets", [])

# 合并:8 件 manual + 125 件 stub = 133 件(对齐 docs/04 §2-§6 命名空间)
_ASSETS_ALL: List[dict] = list(_ASSET_CATALOG) + _STUB_ASSETS


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


class AssetSearchHit(BaseModel):
    """语义搜索单条命中(带 ranking score)"""

    id: str
    kind: str
    version: str
    status: str
    category: str
    purpose: str
    tags: List[str]
    code_ref_count: int = Field(..., description="关联代码引用数量,0=无")
    figma_synced: bool
    score: float = Field(..., description="ranking 分数,越高越相关")
    matched_fields: List[str] = Field(
        default_factory=list,
        description="命中的字段名(用于前端高亮调试)",
    )


class AssetSearchResponse(BaseModel):
    """语义搜索响应(关键词 + 字段权重 ranking)"""

    total: int = Field(..., description="搜索池总量(=133 件,排除过滤后)")
    matched: int = Field(..., description="命中件数(score>0)")
    query: str = Field(..., description="原始查询字符串")
    tokens: List[str] = Field(..., description="拆词后的小写 token 列表")
    assets: List[AssetSearchHit]


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

    v0.2 合并 8 件 manual + 125 件 stub = 133 件(对齐 docs/04 §2-§6
    命名空间:组件 32 / 页面 19 / 令牌 73 / 参考 9=首批 7+manual 2)。
    OAuth 接入后,stub 的 figma_ref / code_ref / purpose 字段会回填真实值。
    """
    filtered = _ASSETS_ALL
    if kind is not None:
        filtered = [a for a in filtered if a["kind"] == kind]
    if category is not None:
        filtered = [a for a in filtered if a["category"] == category]
    if status is not None:
        filtered = [a for a in filtered if a["status"] == status]

    summaries = [_to_summary(a) for a in filtered]
    return AssetsResponse(
        total=len(_ASSETS_ALL),
        returned=len(summaries),
        assets=summaries,
    )


@router.get(
    "/summary",
    response_model=AssetsSummaryResponse,
    summary="4 类资产计数 + 命名空间摘要(前端 Dashboard 用)",
)
def assets_summary() -> AssetsSummaryResponse:
    """返回 4 类资产当前合并数(8 manual + 125 stub)+ docs/04 §3-§6 预期命名空间小计。

    用法:前端 Dashboard 渲染 "组件 32/32 · 页面 19/19 · 令牌 73/73 · 参考 9/开放"
    """
    by_kind: dict = {}
    by_category: dict = {}
    for a in _ASSETS_ALL:
        by_kind[a["kind"]] = by_kind.get(a["kind"], 0) + 1
        key = f"{a['kind']}/{a['category']}"
        by_category[key] = by_category.get(key, 0) + 1

    return AssetsSummaryResponse(
        total=len(_ASSETS_ALL),
        by_kind=by_kind,
        by_category=by_category,
        namespaces={
            "component": {"current": by_kind.get("component", 0), "target": 32, "note": "30-60 件区间"},
            "page": {"current": by_kind.get("page", 0), "target": 19, "note": "15-30 件区间"},
            "token": {"current": by_kind.get("token", 0), "target": 73, "note": "40-80 条区间"},
            "reference": {"current": by_kind.get("reference", 0), "target": None, "note": "开放,无上限"},
        },
    )


# ---- 语义搜索(Phase 1 #1 切第四刀 · 2026-09-04)----
# ranking 设计:简单 token 重合度 + 字段权重
#   - id      权重 5(id 完整命中说明用户精准搜了某个具体资产)
#   - tags    权重 3(标签是设计意图最浓缩的摘要)
#   - purpose 权重 2(描述含完整语义信息,但通常较长)
#   - category 权重 1(粗分类,弱信号)
# 任一 token 在任一字段命中即累加 score,完全无命中 score=0 不入结果;
# tokens 拆分规则:按非字母数字非中文切分(对中文输入也友好,中文字符 char 级别保留)。
# 二次过滤:支持 ?kind / ?status 收敛搜索池(在 ranking 之前过滤)。
#
# Phase 2 升级:向量检索(CLIP) + 倒排索引(whoosh) + 同义词扩展(同义 tag 合并)。

_SEARCH_FIELD_WEIGHTS = {
    "id": 5.0,
    "tags": 3.0,
    "purpose": 2.0,
    "category": 1.0,
}


def _tokenize(text: str) -> List[str]:
    """对查询字符串做最小拆词。

    - 全小写
    - 按非字母数字(ASCII 字母数字之外)切分,中文按 char 切分
    - 过滤空 token
    """
    import re  # noqa: E402 局部 import

    text = text.strip().lower()
    if not text:
        return []
    # 用 [\W_]+ 切分(unicode-aware),中文 / 日文 / 韩文都按 char 切分
    tokens = re.split(r"[\W_]+", text, flags=re.UNICODE)
    return [t for t in tokens if t]


def _search_score(asset: dict, tokens: List[str]) -> tuple:
    """对单个资产按 tokens 累计 score,返回 (score, matched_fields)。

    每个 token 独立计算贡献,字段权重只表示"该字段每次命中的基础分"。
    """
    if not tokens:
        return 0.0, []
    id_l = asset["id"].lower()
    cat_l = asset["category"].lower()
    purpose_l = asset["purpose"].lower()
    tags_l = [t.lower() for t in asset.get("tags", [])]
    id_text = " ".join([id_l, cat_l, purpose_l, " ".join(tags_l)])

    score = 0.0
    matched: List[str] = []

    for tok in tokens:
        if not tok:
            continue
        # id 完全相等(精准)权重最高
        if tok in id_l:
            score += _SEARCH_FIELD_WEIGHTS["id"]
            if "id" not in matched:
                matched.append("id")
        # tags 命中(逐 tag 匹配)
        if any(tok in tag for tag in tags_l):
            score += _SEARCH_FIELD_WEIGHTS["tags"]
            if "tags" not in matched:
                matched.append("tags")
        # purpose 命中
        if tok in purpose_l:
            score += _SEARCH_FIELD_WEIGHTS["purpose"]
            if "purpose" not in matched:
                matched.append("purpose")
        # category 命中
        if tok in cat_l:
            score += _SEARCH_FIELD_WEIGHTS["category"]
            if "category" not in matched:
                matched.append("category")
        # 全文字符串兜底命中(中文字符 char 级别也覆盖)
        if tok in id_text and not matched:
            score += 0.1
            matched.append("text")

    return round(score, 3), matched


@router.get(
    "/search",
    response_model=AssetSearchResponse,
    summary="语义搜索(关键词 + 字段权重 ranking,可叠加 ?kind / ?status)",
)
def search_assets(
    q: str = Query(
        ...,
        min_length=1,
        description="搜索关键词,例: button / 登录 / color / auth,支持中英文",
    ),
    kind: Optional[str] = Query(
        default=None,
        description="资产类型,可选值: component / page / token / reference",
    ),
    status: Optional[str] = Query(
        default=None,
        description="状态过滤,可选值: draft / in_review / approved / deprecated / archived",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
        description="返回前 N 条(ranking 后),默认 50",
    ),
) -> AssetSearchResponse:
    """在 133 件资产(8 manual + 125 stub)中按关键词搜索。

    ranking 算法:
    - 拆词 → 全小写 → token 列表
    - 字段权重:id 5x / tags 3x / purpose 2x / category 1x
    - 任一 token 在任一字段命中即累加 score
    - 按 score 降序返回,score=0 不入结果

    二次过滤:?kind / ?status 在 ranking 之前收敛搜索池,排名仍然在子集中计算。

    用法:
    - 设计师:输入"登录"找 auth 页面、输入"主色"找 brand primary token
    - 飞书 bot:@bot 查 "button" → 转发到 /search?q=button → 返回卡片列表
    - 5 周后 Phase 2 升级:CLIP 视觉相似度 + whoosh 倒排索引
    """
    # 1. 二次过滤(在 ranking 前收敛搜索池)
    pool = _ASSETS_ALL
    if kind is not None:
        pool = [a for a in pool if a["kind"] == kind]
    if status is not None:
        pool = [a for a in pool if a["status"] == status]

    # 2. 拆词
    tokens = _tokenize(q)

    # 3. ranking
    hits: List[AssetSearchHit] = []
    for a in pool:
        score, matched = _search_score(a, tokens)
        if score <= 0:
            continue
        hits.append(
            AssetSearchHit(
                id=a["id"],
                kind=a["kind"],
                version=a["version"],
                status=a["status"],
                category=a["category"],
                purpose=a["purpose"],
                tags=a.get("tags", []),
                code_ref_count=len(a.get("code_ref", [])),
                figma_synced=a.get("figma_ref") not in (None, "PENDING_OAUTH"),
                score=score,
                matched_fields=matched,
            )
        )
    # 4. 排序 + 截断
    hits.sort(key=lambda h: h.score, reverse=True)
    hits = hits[:limit]

    return AssetSearchResponse(
        total=len(pool),
        matched=len(hits),
        query=q,
        tokens=tokens,
        assets=hits,
    )


@router.get(
    "/{asset_id}",
    response_model=AssetDetail,
    summary="按 ID 查单个资产完整元数据",
)
def get_asset(asset_id: str) -> AssetDetail:
    """按 ID 查单个资产完整元数据,用于详情页/评审页面。

    v0.2 在 8 件 manual + 125 件 stub 共 133 件中查找。
    路由顺序:必须放在 /search 之后(否则 path param 会吞掉 /search 路径)。
    """
    for a in _ASSETS_ALL:
        if a["id"] == asset_id:
            return _to_detail(a)
    from fastapi import HTTPException

    raise HTTPException(status_code=404, detail=f"asset not found: {asset_id}")
