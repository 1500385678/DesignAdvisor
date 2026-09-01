# DesignAdvisor

> 27-设计-Design Level 行业 Web 项目 · 内部代号 DesignAdvisor · v0.6(2026-09-02)

## 项目说明
基于张勇的 36 行业架构,DesignAdvisor 是 设计-Design Level 行业的 Web 端顾问产品。
定位:把设计资产管理从文件夹 / Sketch 库 / Figma 链接散落状态,整合为可被 AI
调用、可被设计师搜索、可被产品研发引用的统一设计中枢。

## 同步
- GitHub: https://github.com/1500385678/DesignAdvisor
- Gitee: https://gitee.com/architectzy/DesignAdvisor

## 自动化
- T4 每日 02:00 检查项目并更新开发计划
- T5 每日 03:00 完成小步开发并 commit + push

## 变更记录
- v0.6(2026-09-02)· T5 · Phase 1 #1 资产库 MVP 第二刀:新增 `app/assets/page.tsx` SSR 列表页消费后端 8 件 fake-load,顶部 4 类计数卡(对齐 `docs/04` 命名空间预期:组件 2/32 · 页面 2/19 · 令牌 2/73 · 参考 2/开放)+ `?kind=` + `?status=` + `?category=` 三维过滤,首页加资产库入口卡 · Web 端 0.3 → 0.4,后端 → 前端"半成品接力"完成
- v0.5(2026-09-01)· T5 · Phase 1 #1 资产库 MVP 第一刀:新增 `api/assets.py` 模块(8 件 fake-load 资产,4 类各 2 件),暴露 `GET /api/v1/assets` 列表 + `/summary` 计数 + `/{id}` 详情三端点,字段对齐 `02-schema` v0.1;后端版本 0.2 → 0.3,阶段由 Phase 0 资产盘点进入 Phase 1 资产库 MVP
- v0.4(2026-08-31)· T5 · 新增 `docs/04-可入库资产清单_v0.1.md`,4 类(组件 32 / 页面 19 / 令牌 ~73 / 参考开放)骨架清单对齐 `02-schema` v0.1;Phase 0 #2 闭环,Phase 1 OAuth 后按此清单遍历
- v0.3(2026-08-29)· T5 · 新增 `app/dp/page.tsx` SSR 浏览页(消费 `GET /api/v1/dp/search?q=` + `?category=`),首页加知识库入口 · Web 端先于飞书 bot 跑通规范查询 UI
- v0.2(2026-08-28)· T5 · 24 条 DP 真实数据从 `docs/03-` 抽到 `api/main.py` `_DP_CATALOG`,新增 `/api/v1/dp/search?q=` 关键词搜索端点
- v0.1(2026-08-27)· T5 · 启动 Next.js 14 + FastAPI 最小骨架,Phase 1 前置就位

## 文档地图
- [[项目开发计划]] · T1 主计划(执行态)
- [[docs/01-设计顾问-技术方案-v1.0]] · v1.0 技术方案存档
- [[docs/02-设计资产元数据-schema]] · 资产元数据 schema v0.1
- [[docs/03-_DesignLib盘点_设计哲学清单_v0.1]] · 24 条 DP / 9 条大师名言 / 3 条悖论
- [[docs/04-可入库资产清单_v0.1]] · 4 类资产骨架(组件 32 / 页面 19 / 令牌 ~73 / 参考开放)

## 工程基础设施(v0.1,2026-08-27 立)

技术栈选型已落地最小骨架,Phase 1 业务可在该骨架上直接写。

### 前端 · Next.js 14 + TypeScript + Tailwind
- 入口:`app/layout.tsx` + `app/page.tsx`
- 主题:深色背景(`ink-900`)+ 紫色 accent(`#5B5BD6`),Tailwind 配置见 `tailwind.config.ts`
- API 反代:`/api/be/*` → FastAPI(`next.config.mjs` 中通过 `NEXT_PUBLIC_API_BASE` 配置)

```bash
cd _DesignLib/DesignWeb
npm install          # 装依赖(首次约 1-2 分钟)
npm run dev          # 开发模式 · http://localhost:3000
npm run build        # 生产构建
npm start            # 启动生产服务
```

### 后端 · FastAPI + Pydantic
- 入口:`api/main.py`
- 端点:
  - `GET /healthz` · 健康检查
  - `GET /api/v1/info` · 项目元信息
  - `GET /api/v1/dp` · 24 条设计哲学清单(可按 `?category=` 过滤)
  - `GET /api/v1/dp/search?q=` · DP 关键词搜索(飞书 bot 用)
  - `GET /api/v1/assets` · 资产列表(支持 `?kind=` / `?category=` / `?status=` 过滤,Phase 1 #1)
  - `GET /api/v1/assets/summary` · 4 类资产计数 + 命名空间摘要(Dashboard 用)
  - `GET /api/v1/assets/{id}` · 单个资产完整元数据
- CORS 默认白名单 `http://localhost:3000`,通过 `CORS_ORIGINS` 环境变量覆盖

```bash
cd _DesignLib/DesignWeb
python3 -m venv .venv
source .venv/bin/activate
pip install -r api/requirements.txt
uvicorn api.main:app --reload --port 8000
# 浏览器打开 http://localhost:8000/docs 看 Swagger
```

### 环境变量
- 复制 `.env.example` 为 `.env`,填入 `FIGMA_TOKEN` / `LLM_API_KEY` 等真实值
- `.env` 已在 `.gitignore` 内,不入库

### 目录结构
```
DesignWeb/
├── app/                 # Next.js App Router
│   ├── layout.tsx
│   ├── page.tsx
│   └── globals.css
├── api/                 # FastAPI 后端
│   ├── main.py
│   └── requirements.txt
├── docs/                # 详档
│   ├── 01-设计顾问-技术方案-v1.0.md
│   ├── 02-设计资产元数据-schema.md
│   └── 03-_DesignLib盘点_设计哲学清单_v0.1.md
├── .env.example
├── .gitignore
├── next.config.mjs
├── package.json
├── postcss.config.js
├── tailwind.config.ts
├── tsconfig.json
└── 项目开发计划.md      # T1 主计划
```

## 当前阶段
- **Phase 0**(资产盘点):6/9 完成(+ v0.5 资产后端 fake-load 端点,Phase 0 阶段闭环向 Phase 1 推进)
- **Phase 1**(MVP):0.5/6 · **#1 资产库切第一刀**已落 `api/assets.py` 后端 8 件 fake-load 端点,前端 `app/assets/page.tsx` 列表页待切
- 详见 [[项目开发计划]]
