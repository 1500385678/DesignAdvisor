# DesignAdvisor

> 27-设计-Design Level 行业 Web 项目 · 内部代号 DesignAdvisor · v0.16(2026-09-19)

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
- v0.16(2026-09-19)· T5 · **Phase 1 #2 设计评审模块 v0.1 切第四刀 完整版 - 飞书评审通知 v0.1 端点埋点 + send_card 直发**(评审协作闭环 4/5 不变 · 飞书通知 v0.1 全栈就绪):`api/reviews.py` 新增 lazy `_notifier` 单例 + `_get_notifier()` 工厂 + `_safe_notify(event_type, record, **kwargs)` 非阻塞包装(try/except 全捕获 → log warning,不阻塞主业务)+ 3 mutation 端点 return 前埋点:`create_review` → `notify(EVENT_CREATED, record)` / `transition_review` 写 `rec["last_actor"]` 后 → `notify(EVENT_TRANSITIONED, rec, from_status=current, to_status=payload.to)` / `decide_review` → `notify(EVENT_DECIDED, rec, decision=payload.decision, voter=payload.voter)`;`bot/notify_reviews.py` `notify()` 内部从"render → `_card_to_text_fallback` → `send_text`"链换成"render → `send_card`"直发(0918 `send_card` 真发卡片函数落地),移除 `_card_to_text_fallback` 纯文本降级函数;`bot/__init__.py` v0.5.0 → **v0.6.0**;`bot/test_notify_reviews.py` 重写:移除 `TestCardToTextFallback` 3 件 + 更新 `TestReviewNotifier` 5 件 mock 目标 `send_text` → `send_card`(断言 `send_card` 被调 1 次 + `card_dict["msg_type"] == "interactive"` + header.template=blue/orange/green 三色校验)+ 新增 `test_notify_sends_card_not_text` 关键回归(enabled=True 时 send_card 被调,send_text 不被调);**新增** `api/test_reviews_notify.py` **6/6 单元**(`SpyNotifier` 替换 `_notifier` 单例,记录所有 notify 调用):POST 201 → 1 notify(EVENT_CREATED) / PATCH transition 200 → 1 notify(EVENT_TRANSITIONED, from_status=draft, to_status=in_review) / PATCH transition 422 → 0 notify / PATCH decision 200 → 1 notify(EVENT_DECIDED, decision=approved, voter=feishu:owner-design) / PATCH decision 422 → 0 notify / `ExplodingNotifier` raise → POST 仍 201(非阻塞契约);`bot/` 从 ~1920 行 → ~2030 行(+约 110 行:新 `api/test_reviews_notify.py` ~200 行 + `test_notify_reviews.py` 重写 ~290 行 + `notify_reviews.py` 删 ~50 行 `_card_to_text_fallback`);`api/` 从 ~3101 行 → ~3300 行(+约 200 行:`reviews.py` 加 `logging` import + `_notifier` / `_get_notifier` / `_safe_notify` 4 件 ~35 行 + 3 端点埋点 12 行 + `test_reviews_notify.py` 200 行);**Phase 1 #2 切第四刀完整版闭环 · 飞书通知 v0.1 全栈就绪**(卡片化 0906 + URL 验签 0908 + 限流 0909 + 切真发 smoke 0910 + 命中日志 0911 + 评审通知 stub 0917 + send_card 函数 0918 + **端点埋点 0920**),剩余仅沟通事项:5 设计师 dogfood 验收 + Figma OAuth 真实入库;**0918 → 0919 间隔 ~24h** = **连续 5 日 24h 间隔内连发五刀** `999680c` + `d75fed9` + 0917 stub + 0918 send_card + **0919 端点埋点**;项目 v0.15 → **v0.16**
- v0.15(2026-09-17)· T5 · **Phase 1 #2 设计评审模块 v0.1 切第四刀 stub - 飞书评审通知 v0.1 启动**(评审协作闭环 4/5 推进):新增 `bot/notify_reviews.py` 评审飞书通知 stub(`ReviewNotifierConfig` dataclass + `from_env()` 工厂 + 3 事件 `created` / `transitioned` / `decided` + `ReviewNotifier.notify()` 统一入口 + 3 卡片渲染 `render_review_created_card` / `render_review_transitioned_card` / `render_review_decided_card` + `_card_to_text_fallback` 纯文本降级 + `__main__` CLI 调试入口;复用 `bot/card._header / _div_md / _note / _action_button` 4 件工厂保证视觉风格一致;复用 `bot/lark_client.send_text` 做底层发送;2 env 变量 `FEISHU_REVIEW_NOTIFY_ENABLED` 默认 0 / `FEISHU_REVIEW_NOTIFY_CHAT_ID` 默认空(env-gated 双保险缺一不可)) + `bot/test_notify_reviews.py` **16/16 单元** 验证通过(`TestNotifierConfig` 4 件:env 默认 / env 开但缺 chat_id / 全配 / 大小写宽容 + `TestRenderCards` 3 件:3 卡片 schema 含 msg_type + header.title + 5 elements + from/to/decision 字段 + `TestReviewNotifier` 5 件:disabled skipped / 未知 event_type error / dry_run 真发 / transitioned 真发 / decided 真发 + `TestCardToTextFallback` 3 件:3 事件纯文本降级含 URL + `test_supported_events_constant` 1 件) + `bot/__init__.py` v0.4.1 → **v0.5.0** 增列 notify_reviews 子模块 + `.env.example` 增 2 行 env 变量 + README 新增"评审飞书通知 v0.1 stub(2026-09-17 启动)"小节 + 主计划 §6 #2 checkbox 新增"飞书通知 v0.1 stub"打勾 + 项目版本 v0.14 → **v0.15**;`bot/` 从 ~1660 行 → ~1810 行(+约 150 行,新 notify_reviews.py 290 行 + test_notify_reviews.py 220 行 - 注释精简);**Phase 1 #2 评审协作推进 4/5 → 仍 4/5**(后端 v0.5 ✓ + Web 列表 v0.1 ✓ + Web 详情 v0.1 ✓ + Web 详情 v0.2 微改进 ✓ + 飞书通知 stub ✓,剩 2 子项:真实 SQLite 持久化 + 票数聚合阈值通过);**下一刀候选**:① Phase 1 #2 切第四刀完整版(api/reviews.py 6 端点 return 点埋 notify 调用 + lark_client.send_card 真发卡片)+ ② 切第五刀 SQLite 持久化(1 周可上线)+ ③ 切第六刀票数聚合阈值通过(评审进度卡已就绪为视图层前置);**0917 距 47h 周末警戒线 ~24h01m**(0916 `d75fed9` → 0917 stub = 23h59m 间隔);**0916 → 0917 间隔 23h59m** = **连续 4 日 24h 间隔内连发四刀** `e5bfa35` + `999680c` + `d75fed9` + 0917 stub
- v0.14(2026-09-16)· T5 · **Phase 1 #2 设计评审模块 v0.1 切第三刀半 - Web 端评审详情页 v0.2 微改进(评审进度卡)**(评审协作闭环 3/5 不变 · 接续切第六刀票数聚合阈值通过的前置视图):`app/reviews/[id]/page.tsx` 元数据 section 之后插入"评审进度"小卡(纯 SSR,无 client)+ 新增 `DECISION_STYLES` 常量(4 决策配色:pending 白灰 / approved 翠绿 / rejected_with_reason 红 / request_changes 橙)+ `DECISION_ORDER` 固定顺序(approved → rejected_with_reason → request_changes → pending)+ 按 `decisions_log` 实时聚合 4 决策票数(同评审人多次投票按 latest 一次)+ 顶部右侧"已投 N / 评审人 M"参与度提示 + 当前决策用 `ring-1 ring-accent/40` 高亮 + `current` 标签,Web 端版本 v0.7 → **v0.8**;Next.js 14 构建通过 `/reviews/[id]` 路由仍 3.36 kB 不变(SSR 内联 + 零额外 JS 体积);为切第六刀"票数聚合 + 阈值通过"做视图层前置(决策汇总逻辑前端验证可行,切第六刀仅需后端按此口径增加自动 approved/rejected 阈值触发 + 飞书通知);**下一刀候选**:飞书通知 v0.1(评审创建/状态变更 @ 飞书群 · Phase 1 #2 切第四刀)+ SQLite 持久化(替代内存 fake-load · 切第五刀)+ 票数聚合 + 阈值通过(切第六刀 · 评审进度卡已就绪)+ 5 设计师 dogfood 验收(纯外部沟通)+ Phase 1 #1 Figma OAuth 真实入库(纯外部沟通)
- v0.13(2026-09-15)· T1 · **Phase 1 #2 设计评审模块 v0.1 切第三刀 - Web 端评审详情页 v0.1**(评审协作闭环 3/5 推进):新增 `app/reviews/[id]/page.tsx` 评审详情页 SSR(消费 `GET /api/v1/reviews/{review_id}`)+ 客户端组件 `app/reviews/[id]/ReviewActions.tsx`(状态机 + 投票按钮组,消费 `PATCH /transition` + `PATCH /decision`)+ 6 状态机合法路径按 `_REVIEW_TRANSITIONS` 动态生成按钮(终态 archived 无路径)+ 4 决策按钮组(approved / rejected_with_reason / request_changes / pending)+ 投票前置校验(仅 in_review / approved / rejected 可投票)+ 决策日志 + 转移日志 append-only 时间线(倒序显示,状态/中文章/voter/actor/reason/comment 全字段)+ 评审基本信息卡(创建人 / 当前决策 / 关联资产 ID / 评审人列表 / 创建 + 更新时间)+ 列表页每条加 `<Link href="/reviews/{id}">` 跳转 + footer 文案更新(去掉"评审详情页 v0.2 下一刀"提示)+ Web 端版本 v0.6 → **v0.7**;Web 端 `app/` 1046 → ~1750 行(+约 704 行:reviews/[id]/page.tsx ~371 行 + ReviewActions.tsx ~333 行);`Phase 1 #2 评审协作推进 2/5 → 3/5`(后端 v0.5 + Web 列表 v0.1 + Web 详情 v0.1);Next.js 14 构建通过 `/reviews/[id]` 路由已注册(`ƒ Dynamic server-rendered`,3.36 kB,First Load JS 97.3 kB);**下一刀候选**:飞书通知 v0.1(评审创建/状态变更 @ 飞书群 · Phase 1 #2 切第四刀)+ SQLite 持久化(替代内存 fake-load · 切第五刀)+ 票数聚合 + 阈值通过(切第六刀)+ 5 设计师 dogfood 验收(纯外部沟通)+ Phase 1 #1 Figma OAuth 真实入库(纯外部沟通)
- v0.12(2026-09-14)· T1 · **Phase 1 #2 设计评审模块 v0.1 切第二刀 - Web 端评审列表页 v0.1**(评审协作闭环 2/5 推进):新增 `app/reviews/page.tsx` SSR 列表页消费后端 6 端点(`/api/v1/reviews` + `/summary`)+ 6 状态计数卡(对齐 `summary.namespaces` 字段)+ `?status=` / `?priority=` 二维过滤(URL 状态可分享)+ 状态/决策/优先级中文标签映射 + 状态/优先级彩色标签(draft 灰 / in_review 黄 / approved 绿 / rejected 红 / deprecated 划线 / archived 暗;low 灰 / medium 蓝 / high 橙 / blocker 红)+ 关联资产 ID 展示(`<code>` 字体) + 评审人计数 + 时间戳本地化(中文 zh-CN + 24h 制)+ 主页 `app/page.tsx` 加"评审协作"入口卡(黄色高亮 + Phase 1 #2 启动标识)+ 资产库页加评审协作交叉链接 + 主页版本 v0.3 → **v0.6**;Web 端 `app/` 716 → ~1046 行(+约 330 行:reviews/page.tsx ~330 行);`Phase 1 #2 评审协作推进 1/5 → 2/5`(后端 v0.5 + Web 列表 v0.1);**下一刀候选**:评审详情页 v0.1(`GET /{review_id}` + decisions_log + transitions_log 时间线 + 状态切换 UI 走 PATCH /transition)+ 决策投票 UI 走 PATCH /decision + 飞书通知 v0.1(评审创建/状态变更 @ 飞书群)+ SQLite 持久化
- v0.11(2026-09-12)· T1 · **Phase 1 #2 设计评审模块 v0.1 启动 - 切第一刀**(Phase 1 启动第二个 P0 · 评审协作):新增 `api/reviews.py` 评审后端(6 端点 + 6 Pydantic 模型 + 6 状态机 + 4 决策 + 4 优先级 + 内存 fake-load 3 件 seed)+ `api/test_reviews.py` 10/10 单元 + `api/main.py` 增 `reviews_router` + APP_VERSION v0.4.0 → **v0.5.0** + 模块清单增列"设计评审协作";6 状态机严格校验 `draft → in_review → {approved, rejected} / 撤回 → draft → deprecated → archived`(非法转移返 422 不改记录);决策日志 + 转移日志全部 append-only(审计面留痕);字段口径对齐 `docs/02-schema` v0.1 §6 `review_id`;10 单元全过(seed 可见 + 创建成功 + priority 非法 422 + 列表过滤 + summary 计数 + 状态机合法/非法 + 投票成功/状态不允许 + 不存在 404);7 项端到端验证全过(/healthz 200 + /info v0.5.0 + 默认 3 件 seed + summary 计数 + 创建 201 + transition 200 + decision 200);**Phase 1 推进 4/6 → 5/6**(评审协作 v0.1 后端闭环);**下一刀候选**:Phase 1 #2 切第二刀 Web 端评审页 v0.1(Next.js 列表 + 详情 + 状态切换 UI,消费 6 端点)+ 切第三刀飞书通知(评审创建/状态变更 @ 飞书群)+ 5 设计师 dogfood 验收(纯外部沟通)+ Phase 1 #1 Figma OAuth 真实入库(纯外部沟通)
- v0.10(2026-09-11)· T1 · **飞书 bot 增强 - 命中日志埋点**(为 5 设计师 dogfood 做审计面):新增 `bot/hit_log.py` 命中日志模块(`HitLogConfig` dataclass + `HitLog` append-only JSONL 写入器 + `now_event()` 标准化事件构造 + `from_env()` 工厂 + `__main__` CLI 调试入口,2 env 变量:`FEISHU_BOT_HIT_LOG_ENABLED` 默认 0 / `FEISHU_BOT_HIT_LOG_PATH` 默认 `./data/bot_hit_log.jsonl`)+ `bot/test_hit_log.py` 12 单元 + `bot/webhook.py` 集成 6 个 return 点全覆盖打埋点(正常路径 / 验签失败 / JSON 失败 / payload 非 dict / 无 text / 限流拒发) + `bot/__init__.py` v0.4.0 → **v0.4.1** 增列 hit_log 子模块 + `HealthResponse` 增 `hit_log_enabled` 字段 + note 增 `hitlog=on/off` 段 + `.env.example` 增 2 行 env 变量 + README 新增"命中日志(2026-09-11 闭环)"小节(纯本地不上报,失败不阻塞主流程,字段:ts / chat_id / sender / text / ok / note[含 hit=N + latency_ms] / echo / reply_len / dry_run / event_type)+ 切真发部署清单 § 步骤 5 改为"开启命中日志";12/12 单元 + 3 端到端验证通过(单元 12 + E2E:/health hit_log_enabled 显式 + /webhook 正常路径落盘 + /webhook 限流连发 4 次前 3 通第 4 拒,JSONL 6 行字段全)
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
  - `POST /api/v1/reviews` · 设计评审创建(Phase 1 #2 切第一刀 2026-09-12)
  - `GET /api/v1/reviews` · 评审列表(支持 `?status=` / `?priority=` / `?asset_id=` 过滤)
  - `GET /api/v1/reviews/summary` · 6 状态 + 4 决策 + 4 优先级计数
  - `GET /api/v1/reviews/{review_id}` · 单个评审详情(含 decisions_log + transitions_log)
  - `PATCH /api/v1/reviews/{review_id}/transition` · 状态机转移(合法校验,非法返 422)
  - `PATCH /api/v1/reviews/{review_id}/decision` · 评审人投票(append-only 决策日志)
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
- [x] 命中日志埋点(`bot/hit_log.py` 2026-09-11 闭环,纯本地 JSONL,为 5 设计师 dogfood 做审计面)
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

# 步骤 5:开启命中日志,为 5 设计师 dogfood 做审计面(2026-09-11 闭环)
FEISHU_BOT_HIT_LOG_ENABLED=1   # 默认 0=关闭,5 设计师 dogfood 前开
FEISHU_BOT_HIT_LOG_PATH=./data/bot_hit_log.jsonl  # 默认路径
# - 每条 webhook 落 1 行 JSONL(纯本地不上报,失败不阻塞主流程)
# - 字段:ts / chat_id / sender / text / ok / note / echo / reply_len / dry_run / event_type
# - note 含 hit=N(best-effort 从 reply 提取)+ latency_ms(整条 webhook 处理耗时)
# - 6 种场景全覆盖:正常路径 / 验签失败 / JSON 失败 / payload 非 dict / 无 text / 限流拒发
```

#### 命中日志(2026-09-11 闭环)

`bot/hit_log.py` 是"5 设计师 dogfood 验收"的基础设施 —— 纯本地 JSONL 落盘,
**不上报、不外发**,只把 webhook 主路径的所有事件按 1 行 / 条 append 到文件,
事后用 `jq` / `pandas` 简单分析"设计师问了什么 / 命中几条 / 限流拒几条"等。

CLI 调试入口:

```bash
# 默认关闭,先开
FEISHU_BOT_HIT_LOG_ENABLED=1 python3 -m bot.hit_log \
  '{"text":"button","ok":true,"note":"hit=5"}'
# → recorded ok=True → ./data/bot_hit_log.jsonl

# 验签失败也落(便于事后看"误拒了多少")
FEISHU_BOT_HIT_LOG_ENABLED=1 python3 -m bot.hit_log \
  '{"text":"","ok":false,"note":"sig=deny reason=ts_out_of_range"}'
```

`bot/test_hit_log.py` 12 单元(env 默认 / env 启用 / env 路径 / 7 种假值关闭 /
关闭 record 返 False / 启用 record 写 1 行 / 多次 record append / now_event 必填 /
None 归一 / 写失败不抛 / get_default_hitlog / 自动创建父目录)。

`GET /api/v1/bot/health` 增 `hit_log_enabled` 字段,note 段增 `hitlog=on(path)`
或 `hitlog=off(未启用,5 设计师 dogfood 时建议开启)`。

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

### 评审飞书通知 v0.1 stub(2026-09-17 启动)

`bot/notify_reviews.py` 是 **Phase 1 #2 切第四刀** 的预热 stub —— 评审协作的"飞书通知"
模块契约已落,3 件事件入口(env-gated,默认安全),真正的 `api/reviews.py` 6 端点埋点
+ `lark_client.send_card` 真发卡片留待切第四刀完整版接。

**3 个事件入口**(对齐评审协作 3 个 PATCH/POST 触发点):

| 事件 | 触发点 | 卡片模板色 | 关键字段 |
|---|---|---|---|
| `created` | `POST /api/v1/reviews` 成功 | blue | id / title / priority / creator / reviewers |
| `transitioned` | `PATCH /api/v1/reviews/{id}/transition` 成功 | orange | id / from_status / to_status / last_actor |
| `decided` | `PATCH /api/v1/reviews/{id}/decision` 成功 | green | id / decision / voter |

**入口三件套**(对齐 0910 live_send 风格):
- `ReviewNotifierConfig.from_env()` · 从 env 构造(env-gated,缺 `FEISHU_REVIEW_NOTIFY_CHAT_ID` 时 `enabled=False` 静默跳过)
- `ReviewNotifier.from_env()` · 便利工厂
- `notifier.notify(event_type, review, **kwargs)` · 统一入口,内部按 event_type 路由到 render → send_text → return `{ok, skipped, event_type, chat_id, send_result}`

**复用既有基建**(避免重复造轮子):
- `bot/card._header / _div_md / _note / _action_button` · 4 件工厂,保证卡片视觉风格与 0906 卡片化闭环一致
- `bot/lark_client.send_text` · 底层发送,dry_run 复用全局 `FEISHU_BOT_DRY_RUN` 开关
- `_PRIORITY_LABEL / _STATUS_LABEL / _DECISION_LABEL` · 3 张中文 + emoji 映射,字段口径对齐 `api/reviews.py` _REVIEW_PRIORITIES / _REVIEW_STATUSES / _REVIEW_DECISIONS

**环境变量**(试运行前必读):
- `FEISHU_REVIEW_NOTIFY_ENABLED` · 是否启用评审通知(默认 `0`,切真发前显式设 `1`)
- `FEISHU_REVIEW_NOTIFY_CHAT_ID` · 接收通知的飞书群 `oc_xxx`(必填,未配 enabled 自动 False)
- `FEISHU_BOT_DRY_RUN` · 复用 bot 全局 dry_run 开关(默认 `1`,真发前显式设 `0`)

**试运行(默认 dry_run)**:
```bash
cd _DesignLib/DesignWeb
# 1) 跑单元测试(16/16 通过,无需 env)
python3 -m pytest bot/test_notify_reviews.py -v

# 2) CLI 调试入口(无需 env,默认 enabled=False,返回 skipped=True)
python3 -m bot.notify_reviews created
FEISHU_REVIEW_NOTIFY_ENABLED=1 FEISHU_REVIEW_NOTIFY_CHAT_ID=oc_test_xxx \
  python3 -m bot.notify_reviews decided decision approved voter alice
```

**不做什么(留待切第四刀完整版)**:
- `api/reviews.py` 6 端点 return 点埋 notify 调用(本轮 stub 不接)
- `bot/lark_client.send_card` 真发卡片(本轮走纯文本 fallback `_card_to_text_fallback`)
- 异步队列 / 重试(本轮同步,评审事件低频,够用)
- 卡片交互回调(URL 跳转不算,本轮只静态渲染)
- 评审 SLA / 截止时间告警(Phase 1 #3)
- 多群分发(不同优先级 → 不同群,本轮单群)

**16/16 单元覆盖**:
- `TestNotifierConfig`(4):env 默认关 / env 开但缺 chat_id / 全配 enabled=True / 大小写宽容 `True/true/TRUE`
- `TestRenderCards`(3):3 卡片 msg_type + header.title + 5 elements(div×3 + note + action)
- `TestReviewNotifier`(5):disabled → skipped / 未知 event → error / dry_run 真发 created / transitioned / decided
- `TestCardToTextFallback`(3):3 事件纯文本降级含评审 URL
- `test_supported_events_constant`(1):3 事件常量集合

### 设计评审模块 v0.1(2026-09-12 启动 · 切第一刀)

Phase 1 启动第二个 P0(评审协作),后端先就位,Web 端 + 飞书通知后续两刀。
`api/reviews.py` 实现评审的核心数据模型 + 6 端点 + 6 状态机严格校验。

**数据模型 v0.1**(字段口径对齐 `docs/02-schema` v0.1 §6 `review_id`):

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | str | ✓ | `rev-<8hex>`,进程内 UUID-like,Phase 1 #2 后段切 SQLite 自增 |
| `title` | str(≤80字) | ✓ | 评审标题 |
| `description` | str(≤500字) | ✗ | 评审描述 |
| `asset_id` | str | ✗ | 关联资产 ID(可选,允许独立评审) |
| `status` | enum | ✓ | 6 状态:draft / in_review / approved / rejected / deprecated / archived |
| `decision` | enum | ✓ | 4 决策:pending / approved / rejected_with_reason / request_changes |
| `priority` | enum | ✓ | 4 档:low / medium / high / blocker |
| `created_by` | user_ref | ✓ | 飞书 user_id(占位 `feishu:placeholder`,OAuth 后回填) |
| `reviewers` | user_ref[] | ✗ | 飞书 user_id 列表(0-N 个) |
| `decisions_log` | append-only | ✓ | 投票历史,每条 {decision / voter / comment / at} |
| `transitions_log` | append-only | ✓ | 状态机转移历史,每条 {from / to / reason / actor / at} |
| `created_at` / `updated_at` | ISO8601 | ✓ | UTC 时间戳 |

**6 状态机**(非法转移返 422,不修改记录):

```
draft ──submit──→ in_review ──approve──→ approved ──deprecate──→ deprecated ──→ archived
  ↑                  │                                                       ↑
  └─withdraw─────────┤                                                       │
                     └──reject──→ rejected ──reopen──→ in_review             │
                                  │                                          │
                                  └──────────────────→ archived ──────────────┘
```

**6 端点**:
- `POST /api/v1/reviews` · 创建评审(必填 title + priority,默认 status=draft / decision=pending,返 201)
- `GET /api/v1/reviews` · 列表(支持 `?status=` / `?priority=` / `?asset_id=` 过滤,按 created_at 倒序)
- `GET /api/v1/reviews/summary` · 6 状态 + 4 决策 + 4 优先级计数(前端 Dashboard)
- `GET /api/v1/reviews/{review_id}` · 单个评审详情(含完整 decisions_log + transitions_log)
- `PATCH /api/v1/reviews/{review_id}/transition` · 状态机转移(合法校验,非法返 422)
- `PATCH /api/v1/reviews/{review_id}/decision` · 评审人投票(append-only 日志,同步更新 decision 字段)

**3 件 fake-load seed**(内存存储,Phase 1 #2 切第四刀换 SQLite):
- `rev-seed-001` · 评审 comp-button-primary 圆角 4 → 8px,priority=high / status=in_review
- `rev-seed-002` · 评审 page-auth-login 视觉稿定稿,priority=medium / status=draft
- `rev-seed-003` · 评审 token-color-brand-primary 暗黑模式适配,priority=low / status=approved

**10/10 单元 + 7 端到端验证**:
- 单元:seed 可见 / 创建成功 / priority 非法 422 / 列表过滤 / summary 计数 / 状态机合法 / 状态机非法 / 投票成功 / 投票状态不允许 / 不存在 404
- 端到端:/healthz 200 / /info v0.5.0 / 默认 3 件 seed / summary 计数 / 创建 201 / transition 200 / decision 200

**下一刀候选**:
- 切第二刀 · Web 端评审页 v0.1(Next.js 列表 + 详情 + 状态切换 UI,消费 6 端点)
- 切第三刀 · 飞书通知 v0.1(评审创建/状态变更 @ 飞书群,利用已闭环的 5 件套)
- 切第四刀 · 真实 SQLite 持久化(替代内存 fake-load,数据可入库)
- 切第五刀 · 票数聚合 + 阈值通过(替代单票同步,多人评审场景)

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
│   ├── globals.css
│   ├── assets/          # 资产库 Web 端(Phase 1 #1)
│   └── dp/              # 设计哲学 Web 端
├── api/                 # FastAPI 后端
│   ├── main.py
│   ├── assets.py        # 资产库后端(Phase 1 #1)
│   ├── assets_stub.json # 125 件 stub 数据
│   ├── reviews.py       # 设计评审后端(Phase 1 #2 切第一刀 2026-09-12)
│   ├── test_reviews.py  # 评审后端 10 单元
│   └── requirements.txt
├── bot/                 # 飞书 bot(Phase 0 #4 闭环 + 增强 1-5/5)
│   ├── webhook.py
│   ├── search_handler.py
│   ├── lark_client.py
│   ├── card.py
│   ├── signature.py
│   ├── ratelimit.py
│   ├── live_send.py
│   ├── test_live_send.py
│   ├── hit_log.py
│   └── test_hit_log.py
├── docs/                # 详档
│   ├── 01-设计顾问-技术方案-v1.0.md
│   ├── 02-设计资产元数据-schema.md
│   ├── 03-_DesignLib盘点_设计哲学清单_v0.1.md
│   └── 04-可入库资产清单_v0.1.md
├── scripts/             # 数据生成脚本
│   └── gen_assets.py
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
- **Phase 0**(资产盘点):**10/10 业务工程闭环**(0905 巡检口径,9 实际目标 + #4 飞书 bot 雏形 = 10 项全完成 = #1 哲学清单 / #2 4 类资产骨架 / #5 schema / #7 工程骨架 / #8 24 条 DP / Web dp SSR / #10 4 类资产清单 v0.1 / Phase 1 #1 后端 / Phase 1 #1 前端 / **#4 飞书 bot 雏形闭环** 2026-09-05);**飞书 bot 增强 5/5 卡片化 + URL 验签 + 限流 + 切真发 smoke 工具 + 命中日志埋点全部闭环**(0906-0911 五 commit,bot/ 547 → ~1660 行);#3 Figma OAuth / #6 设计师访谈 仍待动(纯外部沟通)
- **Phase 1**(MVP):5/6 · **#1 资产库 4/5** 子项打勾(后端 fake-load ✓ + 前端列表页 ✓ + 32+19+73 全量回填 ✓ + 语义搜索 ✓) + **#2 评审协作 v0.1 后端闭环** ✓(2026-09-12,6 端点 + 6 状态机 + 10/10 单元,后端 v0.5);剩 #1 Figma OAuth 真实入库 + #2 评审 Web 端 / 飞书通知 / SQLite 持久化
- 详见 [[项目开发计划]]
