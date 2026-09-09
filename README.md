# DesignAdvisor

> 27-设计-Design Level 行业 Web 项目 · 内部代号 DesignAdvisor · v0.9(2026-09-05)

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
- v0.9(2026-09-05)· T1 · **Phase 0 #4 飞书 bot 雏形闭环**:新增 `bot/` 三模块(`webhook.py` FastAPI 路由 + `lark_client.py` lark-cli 包装 + `search_handler.py` 业务分发)+ `api/main.py` 注册 `bot_router` + 后端版本 0.3 → **0.4**;支持 `asset <关键词>` / `dp <关键词>` / `help` 三个命令(裸关键词默认走 asset),`GET /api/v1/bot/health` 200,`POST /api/v1/bot/webhook` 端到端验证(asset button → 5/133 命中 / dp 简约 → 1 命中 / help → 命令清单);`FEISHU_BOT_DRY_RUN=1` 默认 dry_run(只 print 不真发,Phase 0 试运行安全);七前置全栈就绪(0828-0904 七个 commit)差最后 20% 全部补齐,Phase 0 业务工程 10/10 闭环
- v0.8(2026-09-04)· T1 · Phase 1 #1 资产库 MVP 第四刀:新增 `GET /api/v1/assets/search?q=&kind=&status=&limit=` 语义搜索端点(133 件 + 字段权重 ranking:id 5x / tags 3x / 描述 2x / 子分类 1x + tokenize 中英文)+ 前端 `app/assets/page.tsx` 顶部加搜索框 + 命中卡片显示 `★ score` 与 `命中字段` 提示,Phase 1 #1 推进 3/5 → **4/5**,后端 v0.3 → v0.4 · Web 消费 v0.4 → v0.5;Phase 2 升级预埋:CLIP 视觉相似度 + whoosh 倒排索引
- v0.7(2026-09-03)· T1 · Phase 1 #1 资产库 MVP 第三刀:`scripts/gen_assets.py` 从 `docs/04-可入库资产清单 v0.1` §2-§6 命名空间批量生成 125 件 stub + `api/assets_stub.json` 2642 行,`api/assets.py` 加载合并 8 manual + 125 stub = **133 件**,`/api/v1/assets` total 133 · `/summary` 命名空间 32-19-73-9,后端 v0.2 → v0.3
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
  - `GET /api/v1/assets/search` · 语义搜索(关键词 + 字段权重 ranking · Phase 1 #1 切第四刀 2026-09-04)
  - `GET /api/v1/assets/{id}` · 单个资产完整元数据
  - `GET /api/v1/bot/health` · 飞书 bot 健康检查(Phase 0 #4 2026-09-05)
  - `POST /api/v1/bot/webhook` · 飞书事件回调(dry_run 默认开,Phase 0 试运行)
- CORS 默认白名单 `http://localhost:3000`,通过 `CORS_ORIGINS` 环境变量覆盖

### 飞书 bot(Phase 0 #4 雏形闭环,2026-09-05)

`bot/` 三模块,把 Web 端搜索能力塞进飞书群:

- `bot/search_handler.py` · 业务分发:解析 `asset <kw>` / `dp <kw>` / `help` 三个命令,裸关键词默认走 asset;调本机 `/api/v1/assets/search` 或 `/api/v1/dp/search` 拉命中,渲染 1-3 条简版卡片文本
- `bot/lark_client.py` · lark-cli 包装,默认 `FEISHU_BOT_DRY_RUN=1` 只 print 不真发;真发前 `FEISHU_BOT_DRY_RUN=0` 关闭
- `bot/webhook.py` · FastAPI 路由 `POST /api/v1/bot/webhook`,收飞书事件后用 `run_in_threadpool` 调 search_handler(避免 uvicorn 单线程事件循环自调本地后端的死锁)

命令清单:
```
help                · 本清单
asset <关键词>      · 搜设计资产(组件/页面/令牌/参考 · 133 件)
dp <关键词>         · 搜设计哲学规范(24 条)
<关键词>            · 默认走 asset
```

试运行(默认 dry_run):
```bash
# 1) 启动后端
cd _DesignLib/DesignWeb
python3 -m uvicorn api.main:app --host 127.0.0.1 --port 8000

# 2) 干跑 bot 分发(无需后端,直接验证命令解析)
python3 -c "from bot.search_handler import dispatch; print(dispatch('help'))"
python3 -c "from bot.search_handler import dispatch; print(dispatch('asset button'))"

# 3) 端到端 webhook 测试
curl -X POST "http://127.0.0.1:8000/api/v1/bot/webhook?chat_id=oc_test_xxx" \
  -H "Content-Type: application/json" \
  -d '{"header":{"event_type":"im.message.receive_v1"},"event":{"message":{"chat_id":"oc_test_xxx","content":{"text":"asset button"}},"sender":{"sender_id":{"open_id":"ou_test"}}}}'

# 4) 真发(谨慎):lark-cli --profile design im +messages-send ...
FEISHU_BOT_DRY_RUN=0 python3 -c "
from bot.lark_client import send_text
send_text('oc_real_chat_id', 'hello from design bot')
"
```

环境变量:
- `FEISHU_BOT_DRY_RUN` · `1`(默认,dry_run)/ `0`(真发)
- `LARK_CLI_BIN` · lark-cli 路径(默认 `lark-cli`,假设在 PATH)
- `LARK_PROFILE` · lark-cli profile 名(默认 `design`,与 36 行业约定一致)
- `DESIGNADVISOR_API` · 本机后端基址(默认 `http://127.0.0.1:8000`,用 127.0.0.1 避免 macOS localhost IPv6 解析问题)

后续 T1-T5 计划:
- [x] 飞书卡片 / 富文本(`bot/card.py` 2026-09-06 闭环)
- [x] URL 验签(`bot/signature.py` 2026-09-08 闭环)
- [x] 限流(`bot/ratelimit.py` 2026-09-09 闭环)
- [x] 切真发 smoke 工具(`bot/live_send.py` 2026-09-10 闭环)
- [ ] 5 设计师 dogfood 验收(试运行首刀,纯外部沟通)

#### 切真发部署清单(2026-09-10 闭环)

`bot/live_send.py` 在 `bot/lark_client.py` 之上加"试运行前自检 + 真发编排"。
限流 / URL 验签 / 卡片化 3 步安全垫 0906-0909 全部闭环后,本步把"切真发"流程
收敛为 5 步部署清单:

```bash
# 步骤 1:lark-cli profile 配对(假设 lark-cli 已在 PATH)
lark-cli login --profile design    # 走 OAuth 流程,落 ~/.lark-cli/config.yaml
lark-cli --profile design im +messages-send --help   # 验证可用

# 步骤 2:填 .env(env 已留 4 个变量,见 .env.example)
FEISHU_BOT_DRY_RUN=0                 # 显式开启真发(默认 1=dry_run)
FEISHU_BOT_VERIFY_TOKEN=<your_token> # 飞书后台"事件订阅 Verification Token"
LARK_PROFILE=design                  # 已默认
LARK_CLI_BIN=lark-cli                # 已默认

# 步骤 3:探活(probe_lark_cli 调 --help,无副作用,不发消息)
python3 -c "from bot.live_send import probe_lark_cli; print(probe_lark_cli('lark-cli', 'design'))"

# 步骤 4:单条真发(send_via_lark 自动先 probe 后 send,probe 失败抛 ProbeError)
FEISHU_BOT_DRY_RUN=0 FEISHU_BOT_DEFAULT_CHAT_ID=oc_xxx \
  python3 -m bot.live_send "smoke test from design bot"

# 步骤 5:5 设计师 dogfood 验收(2026-09-10 起的下一刀)
# - 收集命中质量 / 响应延迟 / 卡片可读性 / 限流是否合理
# - bot/webhook.py 加 dry_run/真发切换埋点 + 命中日志(纯本地)
```

试运行前自检(`bot/test_live_send.py` 8 单元):
- env 默认值 / env chat_id 覆盖
- dry_run=True 不调 subprocess / dry_run=False 调 subprocess 正确
- chat_id 缺失 raise ValueError / 显式 chat_id 覆盖 default
- probe 调 `lark-cli --profile <p> im +messages-send --help`
- probe 失败(rc != 0 / lark-cli 不存在 / 超时)raise ProbeError

已知边界(留待 Phase 1):
- 单 chat_id 单消息(本轮 1 条 1 chat,无多 chat 广播)
- 同步阻塞(无队列/重试,probe 失败直接 raise,人工介入)
- 卡片切真发(`bot/card.py` 仍是 dry_run,卡片走 lark SDK 在 Phase 1 切)

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
├── bot/                 # 飞书 bot(Phase 0 #4 闭环 + 增强 1-4/4)
│   ├── webhook.py
│   ├── search_handler.py
│   ├── lark_client.py
│   ├── card.py
│   ├── signature.py
│   ├── ratelimit.py
│   ├── live_send.py
│   └── test_live_send.py
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
- **Phase 0**(资产盘点):**10/10 业务工程闭环**(0905 巡检口径,9 实际目标 + #4 飞书 bot 雏形 = 10 项全完成 = #1 哲学清单 / #2 4 类资产骨架 / #5 schema / #7 工程骨架 / #8 24 条 DP / Web dp SSR / #10 4 类资产清单 v0.1 / Phase 1 #1 后端 / Phase 1 #1 前端 / **#4 飞书 bot 雏形闭环** 2026-09-05);#3 Figma OAuth / #6 设计师访谈 仍待动(纯外部沟通)
- **Phase 1**(MVP):4/6 · **#1 资产库 4/5** 子项打勾(后端 fake-load ✓ + 前端列表页 ✓ + 32+19+73 全量回填 ✓ + 语义搜索 ✓),剩余 1 子项 Figma OAuth 真实入库
- 详见 [[项目开发计划]]
