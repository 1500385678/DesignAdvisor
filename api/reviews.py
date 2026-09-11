"""
DesignAdvisor · 设计评审后端 v0.1 (Phase 1 #2 设计评审模块 切第一刀)

评审数据模型 v0.1(对齐 docs/02-设计资产元数据-schema.md §6 `review_id`):
- 每个评审独立一条记录,关联到某个资产(`asset_id` 可选,允许独立评审)
- 6 状态机:draft → in_review → {approved, rejected} / 撤回 → draft → deprecated → archived
- 决策 4 种:pending / approved / rejected_with_reason / request_changes
- 优先级 4 档:low / medium / high / blocker
- 内存 fake-load 存储(对齐 assets.py v0.3 风格,Phase 1 后段切到 SQLite)

端点(全部 Phase 1 #2 v0.1):
- POST /api/v1/reviews                     创建评审(必填 title / asset_id? / priority / reviewers)
- GET  /api/v1/reviews                     列出评审(?status / ?priority / ?asset_id 过滤)
- GET  /api/v1/reviews/summary             6 状态计数(前端 Dashboard)
- GET  /api/v1/reviews/{review_id}         单个评审详情
- PATCH /api/v1/reviews/{review_id}/transition  状态机转移(合法校验)
- PATCH /api/v1/reviews/{review_id}/decision    决策变更(评审人投票)

不做什么(留待后续 T1-T5):
- 真实 SQLite 持久化(Phase 1 #2 后段)
- Web 端评审页 v0.1(Phase 1 #2 第二刀)
- @飞书通知 / 飞书卡片评审(Phase 1 #2 第三刀)
- 历史 changelog(评审自己的版本变化,Phase 2)
- 评审 SLA / 截止时间(Phase 1 #3)
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"])


# ---------- 评审领域模型 ----------

# 6 种状态(对齐 docs/02-schema §4 `status` 但评审独立 6 态)
_REVIEW_STATUSES = {"draft", "in_review", "approved", "rejected", "deprecated", "archived"}

# 4 种决策(评审人投票结果)
_REVIEW_DECISIONS = {"pending", "approved", "rejected_with_reason", "request_changes"}

# 4 档优先级
_REVIEW_PRIORITIES = {"low", "medium", "high", "blocker"}

# 状态机:合法转移表(从 → {可去状态})
# draft       → {in_review, archived}
# in_review   → {approved, rejected, draft(撤回), archived}
# approved    → {deprecated(后续不再用), archived}
# rejected    → {in_review(重审), archived}
# deprecated  → {archived}
# archived    → {} 终态
_REVIEW_TRANSITIONS: Dict[str, set] = {
    "draft": {"in_review", "archived"},
    "in_review": {"approved", "rejected", "draft", "archived"},
    "approved": {"deprecated", "archived"},
    "rejected": {"in_review", "archived"},
    "deprecated": {"archived"},
    "archived": set(),
}

_ID_PATTERN = re.compile(r"^[A-Za-z0-9_:.\-]{1,80}$")
_FAKE_LOAD_TS = datetime(2026, 9, 12, 3, 20, 0, tzinfo=timezone.utc)
_PLACEHOLDER_USER = "feishu:placeholder"


# ---------- Pydantic 请求/响应模型 ----------


class ReviewCreate(BaseModel):
    """创建评审请求体"""

    title: str = Field(..., min_length=1, max_length=80, description="评审标题,1-80 字")
    asset_id: Optional[str] = Field(
        default=None, max_length=120, description="关联资产 ID(可选,允许独立评审)"
    )
    description: str = Field(default="", max_length=500, description="评审描述,0-500 字")
    priority: str = Field(
        default="medium",
        description="优先级:low / medium / high / blocker",
    )
    reviewers: List[str] = Field(
        default_factory=list,
        description="飞书 user_id 列表,例如 ['feishu:owner-design', 'feishu:owner-frontend']",
    )
    created_by: str = Field(
        default=_PLACEHOLDER_USER,
        max_length=80,
        description="创建者飞书 user_id,Phase 0 #3 OAuth 后回填真实值",
    )


class ReviewTransition(BaseModel):
    """状态机转移请求体"""

    to: str = Field(..., description="目标状态,合法值见 _REVIEW_STATUSES")
    reason: str = Field(default="", max_length=280, description="转移原因,0-280 字")


class ReviewDecision(BaseModel):
    """决策变更请求体(评审人投票)"""

    decision: str = Field(..., description="决策:pending / approved / rejected_with_reason / request_changes")
    voter: str = Field(..., max_length=80, description="投票人飞书 user_id")
    comment: str = Field(default="", max_length=280, description="投票意见,0-280 字")


class ReviewSummary(BaseModel):
    """评审列表摘要"""

    id: str
    title: str
    asset_id: Optional[str] = None
    status: str
    decision: str
    priority: str
    created_by: str
    reviewer_count: int
    created_at: str
    updated_at: str


class ReviewDetail(BaseModel):
    """评审完整元数据(详情页/审计用)"""

    id: str
    title: str
    description: str
    asset_id: Optional[str] = None
    status: str
    decision: str
    priority: str
    created_by: str
    reviewers: List[str]
    created_at: str
    updated_at: str
    decisions_log: List[dict] = Field(
        default_factory=list,
        description="决策日志(评审人投票历史,append-only)",
    )
    transitions_log: List[dict] = Field(
        default_factory=list,
        description="状态机转移日志(append-only)",
    )


class ReviewsResponse(BaseModel):
    """评审列表响应"""

    total: int
    returned: int
    reviews: List[ReviewSummary]


class ReviewsSummaryResponse(BaseModel):
    """6 状态计数摘要 + 4 决策计数 + 4 优先级计数"""

    total: int
    by_status: dict
    by_decision: dict
    by_priority: dict
    namespaces: dict = Field(
        default_factory=dict,
        description="6 状态命名空间(对齐 _REVIEW_STATUSES 集合)",
    )


# ---------- 存储(内存 fake-load,进程级单例) ----------

# v0.1 fake-load:3 件 seed(覆盖 3 种状态,演示状态机)
_REVIEWS: Dict[str, dict] = {
    "rev-seed-001": {
        "id": "rev-seed-001",
        "title": "评审:comp-button-primary 圆角 4 → 8px",
        "description": "适配新品牌规范 v1.1 圆角标准,影响 12 处引用,需设计+前端双签",
        "asset_id": "comp-button-primary-v0.1.0",
        "status": "in_review",
        "decision": "pending",
        "priority": "high",
        "created_by": "feishu:placeholder",
        "reviewers": ["feishu:owner-design", "feishu:owner-frontend"],
        "created_at": _FAKE_LOAD_TS.isoformat(),
        "updated_at": _FAKE_LOAD_TS.isoformat(),
        "decisions_log": [],
        "transitions_log": [
            {
                "from": "draft",
                "to": "in_review",
                "reason": "seed 演示:直接进评审",
                "actor": _PLACEHOLDER_USER,
                "at": _FAKE_LOAD_TS.isoformat(),
            }
        ],
    },
    "rev-seed-002": {
        "id": "rev-seed-002",
        "title": "评审:page-auth-login 视觉稿定稿",
        "description": "登录页 v0.1 视觉稿,主流程 + SSO 入口,等品牌 + 前端评审",
        "asset_id": "page-auth-login-v0.1.0",
        "status": "draft",
        "decision": "pending",
        "priority": "medium",
        "created_by": _PLACEHOLDER_USER,
        "reviewers": ["feishu:owner-brand", "feishu:owner-frontend"],
        "created_at": _FAKE_LOAD_TS.isoformat(),
        "updated_at": _FAKE_LOAD_TS.isoformat(),
        "decisions_log": [],
        "transitions_log": [],
    },
    "rev-seed-003": {
        "id": "rev-seed-003",
        "title": "评审:token-color-brand-primary 暗黑模式适配",
        "description": "品牌主色在暗黑模式下需微调明度,待设计师评审",
        "asset_id": "token-color-brand-primary-v0.1.0",
        "status": "approved",
        "decision": "approved",
        "priority": "low",
        "created_by": _PLACEHOLDER_USER,
        "reviewers": ["feishu:owner-brand"],
        "created_at": _FAKE_LOAD_TS.isoformat(),
        "updated_at": _FAKE_LOAD_TS.isoformat(),
        "decisions_log": [
            {
                "decision": "approved",
                "voter": "feishu:owner-brand",
                "comment": "明度 +8% 适配暗黑,通过",
                "at": _FAKE_LOAD_TS.isoformat(),
            }
        ],
        "transitions_log": [
            {
                "from": "draft",
                "to": "in_review",
                "reason": "提交评审",
                "actor": _PLACEHOLDER_USER,
                "at": _FAKE_LOAD_TS.isoformat(),
            },
            {
                "from": "in_review",
                "to": "approved",
                "reason": "评审通过",
                "actor": "feishu:owner-brand",
                "at": _FAKE_LOAD_TS.isoformat(),
            },
        ],
    },
}


# ---------- 工具函数 ----------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    """生成评审 ID:rev-<8hex>。取 uuid4 前 8 位,人眼可读 + 唯一性足够(v0.1 阶段)"""
    return f"rev-{uuid.uuid4().hex[:8]}"


def _validate_id(value: str, field: str) -> None:
    if not _ID_PATTERN.match(value):
        raise HTTPException(
            status_code=422,
            detail=f"{field} 格式非法(只允许字母数字 + `_:.-`,1-80 字符),got={value!r}",
        )


def _to_summary(review: dict) -> ReviewSummary:
    return ReviewSummary(
        id=review["id"],
        title=review["title"],
        asset_id=review.get("asset_id"),
        status=review["status"],
        decision=review["decision"],
        priority=review["priority"],
        created_by=review["created_by"],
        reviewer_count=len(review.get("reviewers", [])),
        created_at=review["created_at"],
        updated_at=review["updated_at"],
    )


def _to_detail(review: dict) -> ReviewDetail:
    return ReviewDetail(
        id=review["id"],
        title=review["title"],
        description=review.get("description", ""),
        asset_id=review.get("asset_id"),
        status=review["status"],
        decision=review["decision"],
        priority=review["priority"],
        created_by=review["created_by"],
        reviewers=list(review.get("reviewers", [])),
        created_at=review["created_at"],
        updated_at=review["updated_at"],
        decisions_log=list(review.get("decisions_log", [])),
        transitions_log=list(review.get("transitions_log", [])),
    )


# ---------- 端点 ----------


@router.post(
    "",
    response_model=ReviewDetail,
    status_code=201,
    summary="创建评审(必填 title + priority,默认 status=draft / decision=pending)",
)
def create_review(payload: ReviewCreate) -> ReviewDetail:
    """v0.1 创建评审。

    - title 1-80 字(必填)
    - asset_id 可选(允许独立评审,非资产相关讨论也支持)
    - priority 4 选 1(默认 medium)
    - reviewers 飞书 user_id 列表(0-N 个)
    - 创建后 status=draft / decision=pending,需走 PATCH /transition 进 in_review
    """
    if payload.priority not in _REVIEW_PRIORITIES:
        raise HTTPException(
            status_code=422,
            detail=f"priority 非法,合法值={sorted(_REVIEW_PRIORITIES)},got={payload.priority!r}",
        )
    if payload.asset_id is not None:
        _validate_id(payload.asset_id, "asset_id")
    for rev in payload.reviewers:
        _validate_id(rev, "reviewers[]")
    _validate_id(payload.created_by, "created_by")

    new_id = _new_id()
    now = _now_iso()
    record = {
        "id": new_id,
        "title": payload.title.strip(),
        "description": payload.description.strip(),
        "asset_id": payload.asset_id,
        "status": "draft",
        "decision": "pending",
        "priority": payload.priority,
        "created_by": payload.created_by,
        "reviewers": list(payload.reviewers),
        "created_at": now,
        "updated_at": now,
        "decisions_log": [],
        "transitions_log": [],
    }
    _REVIEWS[new_id] = record
    return _to_detail(record)


@router.get(
    "",
    response_model=ReviewsResponse,
    summary="列出评审(支持 ?status / ?priority / ?asset_id 过滤)",
)
def list_reviews(
    status: Optional[str] = Query(
        default=None,
        description="状态过滤: draft / in_review / approved / rejected / deprecated / archived",
    ),
    priority: Optional[str] = Query(
        default=None,
        description="优先级过滤: low / medium / high / blocker",
    ),
    asset_id: Optional[str] = Query(
        default=None,
        description="按关联资产 ID 过滤(精确匹配)",
    ),
) -> ReviewsResponse:
    """列出全部评审(默认按 created_at 倒序,最新在前)。"""
    if status is not None and status not in _REVIEW_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"status 非法,合法值={sorted(_REVIEW_STATUSES)},got={status!r}",
        )
    if priority is not None and priority not in _REVIEW_PRIORITIES:
        raise HTTPException(
            status_code=422,
            detail=f"priority 非法,合法值={sorted(_REVIEW_PRIORITIES)},got={priority!r}",
        )
    if asset_id is not None:
        _validate_id(asset_id, "asset_id")

    items = list(_REVIEWS.values())
    if status is not None:
        items = [r for r in items if r["status"] == status]
    if priority is not None:
        items = [r for r in items if r["priority"] == priority]
    if asset_id is not None:
        items = [r for r in items if r.get("asset_id") == asset_id]

    # 按 created_at 倒序(稳定排序:同 ts 时按 id 升序)
    items.sort(key=lambda r: (r["created_at"], r["id"]), reverse=True)

    return ReviewsResponse(
        total=len(_REVIEWS),
        returned=len(items),
        reviews=[_to_summary(r) for r in items],
    )


@router.get(
    "/summary",
    response_model=ReviewsSummaryResponse,
    summary="6 状态计数 + 4 决策计数 + 4 优先级计数(前端 Dashboard)",
)
def reviews_summary() -> ReviewsSummaryResponse:
    by_status: dict = {}
    by_decision: dict = {}
    by_priority: dict = {}
    for r in _REVIEWS.values():
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
        by_decision[r["decision"]] = by_decision.get(r["decision"], 0) + 1
        by_priority[r["priority"]] = by_priority.get(r["priority"], 0) + 1
    return ReviewsSummaryResponse(
        total=len(_REVIEWS),
        by_status=by_status,
        by_decision=by_decision,
        by_priority=by_priority,
        namespaces={
            s: {"current": by_status.get(s, 0), "target": None, "note": "开放,无上限"}
            for s in sorted(_REVIEW_STATUSES)
        },
    )


@router.get(
    "/{review_id}",
    response_model=ReviewDetail,
    summary="单个评审完整元数据(含 decisions_log + transitions_log)",
)
def get_review(review_id: str) -> ReviewDetail:
    _validate_id(review_id, "review_id")
    rec = _REVIEWS.get(review_id)
    if rec is None:
        raise HTTPException(status_code=404, detail=f"review {review_id!r} 不存在")
    return _to_detail(rec)


@router.patch(
    "/{review_id}/transition",
    response_model=ReviewDetail,
    summary="状态机转移(合法校验,转移日志 append-only)",
)
def transition_review(review_id: str, payload: ReviewTransition) -> ReviewDetail:
    """v0.1 状态机严格按 _REVIEW_TRANSITIONS 校验。

    合法路径:
      draft → in_review → {approved, rejected} / 撤回 draft → deprecated → archived
    非法路径返回 422,不修改记录。
    """
    _validate_id(review_id, "review_id")
    rec = _REVIEWS.get(review_id)
    if rec is None:
        raise HTTPException(status_code=404, detail=f"review {review_id!r} 不存在")
    if payload.to not in _REVIEW_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"to 非法,合法值={sorted(_REVIEW_STATUSES)},got={payload.to!r}",
        )
    current = rec["status"]
    if payload.to not in _REVIEW_TRANSITIONS.get(current, set()):
        raise HTTPException(
            status_code=422,
            detail=f"非法状态转移 {current!r} → {payload.to!r},合法转移={sorted(_REVIEW_TRANSITIONS.get(current, set()))}",
        )

    now = _now_iso()
    rec["status"] = payload.to
    rec["updated_at"] = now
    rec.setdefault("transitions_log", []).append(
        {
            "from": current,
            "to": payload.to,
            "reason": payload.reason.strip(),
            "actor": _PLACEHOLDER_USER,  # v0.1 暂未从请求头取 actor,后续接飞书 user_id
            "at": now,
        }
    )
    return _to_detail(rec)


@router.patch(
    "/{review_id}/decision",
    response_model=ReviewDetail,
    summary="评审人投票(append-only 决策日志,同步更新 decision 字段为最近一票)",
)
def decide_review(review_id: str, payload: ReviewDecision) -> ReviewDetail:
    """v0.1 决策变更。

    - 决策日志 append-only,记录 voter / comment / at
    - decision 字段同步更新为最新一票(简化版;Phase 1 #2 第二刀会引入"票数聚合 + 阈值通过")
    - 合法决策:pending / approved / rejected_with_reason / request_changes
    """
    _validate_id(review_id, "review_id")
    rec = _REVIEWS.get(review_id)
    if rec is None:
        raise HTTPException(status_code=404, detail=f"review {review_id!r} 不存在")
    if payload.decision not in _REVIEW_DECISIONS:
        raise HTTPException(
            status_code=422,
            detail=f"decision 非法,合法值={sorted(_REVIEW_DECISIONS)},got={payload.decision!r}",
        )
    _validate_id(payload.voter, "voter")
    if rec["status"] not in ("in_review", "approved", "rejected"):
        raise HTTPException(
            status_code=422,
            detail=f"当前状态 {rec['status']!r} 不允许投票,需先 transition 到 in_review",
        )

    now = _now_iso()
    rec["decision"] = payload.decision
    rec["updated_at"] = now
    rec.setdefault("decisions_log", []).append(
        {
            "decision": payload.decision,
            "voter": payload.voter,
            "comment": payload.comment.strip(),
            "at": now,
        }
    )
    return _to_detail(rec)
