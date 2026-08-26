"""
DesignAdvisor · FastAPI 后端 v0.1

仅最小骨架:
- GET /healthz       健康检查
- GET /api/v1/info   项目元信息(版本/阶段/模块清单)
- GET /api/v1/dp     24 条设计哲学清单(占位,Phase 0 落库时替换为真实数据)

启动:uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

APP_NAME = "DesignAdvisor API"
APP_VERSION = "0.1.0"
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


# 24 条 DP 占位 — Phase 0 落库时从 docs/03-_DesignLib盘点_设计哲学清单_v0.1.md 抽取真实数据
_DEMO_DP: List[DesignPrinciple] = [
    DesignPrinciple(
        id="DP-001",
        title="(占位)设计服务于功能,而非装饰",
        category="原则",
        source="_DesignLib/03-设计哲学",
    ),
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
    summary="24 条设计哲学清单",
)
def list_dp() -> List[DesignPrinciple]:
    return _DEMO_DP
