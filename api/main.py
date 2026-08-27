"""
DesignAdvisor · FastAPI 后端 v0.2

最小骨架 + 24 条设计哲学真实数据:
- GET /healthz                    健康检查
- GET /api/v1/info                项目元信息(版本/阶段/模块清单)
- GET /api/v1/dp                  24 条设计哲学清单(从 docs/03- 真实落库)
- GET /api/v1/dp?category=...     按分类过滤(A/B/C/D/E 五类)
- GET /api/v1/dp/search?q=...     关键词搜索(id/title/source 命中,飞书 bot 用)

启动:uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

APP_NAME = "DesignAdvisor API"
APP_VERSION = "0.2.0"
APP_PHASE = "Phase 0 · 资产盘点"

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="27-设计-Design Level 行业 Web 后端",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthInfo(BaseModel):
    status: str
    app: str
    version: str
    phase: str
    now: str


class AppInfo(BaseModel):
    name: str
    version: str
    phase: str
    modules: List[str]


class DesignPrinciple(BaseModel):
    id: str
    title: str
    category: str
    source: str


# 24 条 DP 真实数据
# 数据源:docs/03-_DesignLib盘点_设计哲学清单_v0.1.md §4(2026-08-25 T1 产物)
# 落库:T5 2026-08-28 · 为 Phase 0 #4 飞书 bot "查设计规范" 提供后端数据
_DP_CATALOG: List[DesignPrinciple] = [
    # A. 功能 / 形式类
    DesignPrinciple(id="DP-01", title="形式追随功能", category="A·功能形式", source="01/04/06/09"),
    DesignPrinciple(id="DP-02", title="少,却更好", category="A·功能形式", source="01/04/06"),
    DesignPrinciple(id="DP-03", title="功能 ≠ 外观", category="A·功能形式", source="01"),
    DesignPrinciple(id="DP-04", title="功能 vs 形式平衡", category="A·功能形式", source="04"),
    DesignPrinciple(id="DP-05", title="简约 vs 复杂平衡", category="A·功能形式", source="04"),
    DesignPrinciple(id="DP-06", title="大规模量产设计", category="A·功能形式", source="02"),
    # B. 用户体验类
    DesignPrinciple(id="DP-07", title="设计是如何运作的", category="B·用户体验", source="01/04/06"),
    DesignPrinciple(id="DP-08", title="用户体验优先", category="B·用户体验", source="02/04/06"),
    DesignPrinciple(id="DP-09", title="以用户为中心", category="B·用户体验", source="01/02"),
    DesignPrinciple(id="DP-10", title="用户研究 → 交互设计 → 视觉设计", category="B·用户体验", source="02"),
    DesignPrinciple(id="DP-11", title="数字化用户体验", category="B·用户体验", source="01"),
    DesignPrinciple(id="DP-12", title="体验之美", category="B·用户体验", source="09"),
    # C. 逻辑 / 推理类
    DesignPrinciple(id="DP-13", title="归纳法:从现象到规律", category="C·逻辑推理", source="03/07/08"),
    DesignPrinciple(id="DP-14", title="演绎法:从理论到现象", category="C·逻辑推理", source="03/07/08"),
    DesignPrinciple(id="DP-15", title="思想实验", category="C·逻辑推理", source="03/07"),
    DesignPrinciple(id="DP-16", title="建模是把抽象落地的步骤", category="C·逻辑推理", source="03/08"),
    # D. 思想 / 文化类
    DesignPrinciple(id="DP-17", title="思想指导方法,方法落地应用", category="D·思想文化", source="07/08"),
    DesignPrinciple(id="DP-18", title="大师是知识地图而非崇拜对象", category="D·思想文化", source="06"),
    DesignPrinciple(id="DP-19", title="故事与传说是文化载体", category="D·思想文化", source="04"),
    DesignPrinciple(id="DP-20", title="游戏化学习", category="D·思想文化", source="05"),
    # E. 实践 / 评审类
    DesignPrinciple(id="DP-21", title="8 大分支同源", category="E·实践评审", source="02"),
    DesignPrinciple(id="DP-22", title="理论到实践需'应用'层", category="E·实践评审", source="08"),
    DesignPrinciple(id="DP-23", title="评审 checklist 化", category="E·实践评审", source="03/07"),
    DesignPrinciple(id="DP-24", title="速查表是知识沉淀的最小单元", category="E·实践评审", source="全部10章"),
]


@app.get("/healthz", response_model=HealthInfo, tags=["meta"])
def healthz() -> HealthInfo:
    return HealthInfo(
        status="ok",
        app=APP_NAME,
        version=APP_VERSION,
        phase=APP_PHASE,
        now=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/api/v1/info", response_model=AppInfo, tags=["meta"])
def info() -> AppInfo:
    return AppInfo(
        name=APP_NAME,
        version=APP_VERSION,
        phase=APP_PHASE,
        modules=[
            "设计资产库",
            "设计令牌同步",
            "设计评审协作",
            "AI 草稿生成器",
            "设计灵感库",
        ],
    )


@app.get(
    "/api/v1/dp",
    response_model=List[DesignPrinciple],
    tags=["knowledge"],
    summary="24 条设计哲学清单(可按分类过滤)",
)
def list_dp(
    category: Optional[str] = Query(
        default=None,
        description="分类过滤,可选值: A·功能形式 / B·用户体验 / C·逻辑推理 / D·思想文化 / E·实践评审",
    ),
) -> List[DesignPrinciple]:
    if category is None:
        return _DP_CATALOG
    return [dp for dp in _DP_CATALOG if dp.category == category]


@app.get(
    "/api/v1/dp/search",
    response_model=List[DesignPrinciple],
    tags=["knowledge"],
    summary="关键词搜索(命中 id/title/source,大小写不敏感)",
)
def search_dp(
    q: str = Query(..., min_length=1, description="搜索关键词,例如 简约 / 用户体验 / DP-01"),
) -> List[DesignPrinciple]:
    keyword = q.strip().lower()
    if not keyword:
        return []
    return [
        dp
        for dp in _DP_CATALOG
        if keyword in dp.id.lower()
        or keyword in dp.title.lower()
        or keyword in dp.source.lower()
    ]
