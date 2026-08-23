# 设计资产元数据 Schema · v0.1

> Phase 0 任务 5 产物 · 2026-08-24 · 起草稿,待 Phase 1 入库时定稿

## 1. 设计目标

- 资产**可被搜索**:语义检索 + 标签 + 视觉相似度都需要稳定字段
- 资产**可被版本化**:每次入库产生新版本,旧版可追溯
- 资产**可被关联**:与 Figma 源文件、代码仓库、评审记录双向追溯
- 资产**可被审计**:谁在何时、为何入库/修改/废弃,留痕完整

## 2. 字段定义(顶层 5 大类)

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | UUID v7 | ✓ | 资产唯一 ID,时序可排序,作主键 |
| `kind` | enum | ✓ | 资产类型,见 §3 |
| `version` | semver string | ✓ | 当前主版本号,与 `versions[]` 数组联动 |
| `status` | enum | ✓ | 资产状态,见 §4 |
| `created_at` / `updated_at` | ISO8601 | ✓ | UTC 时间戳 |

## 3. `kind` 资产类型枚举

- `brand` · 品牌资产(Logo / VI / 字体授权)
- `token` · 设计令牌(颜色 / 字号 / 间距 / 阴影 / 圆角)
- `component` · 组件(按钮 / 表单 / 卡片 / 导航)
- `page` · 页面模板(整页设计稿)
- `template` · 工作流模板(评审 / 走查 / 复用模板)
- `reference` · 外部参考(竞品 / 灵感 / 行业案例)
- `guideline` · 规范文档(品牌手册 / 组件使用说明)

## 4. `status` 状态枚举

- `draft` · 草稿(未提交评审)
- `in_review` · 评审中
- `approved` · 已通过(当前生效)
- `deprecated` · 已废弃(保留只读,不再推荐)
- `archived` · 已归档(超过保留期,只对审计可见)

## 5. 治理字段(谁/为什么/怎么用)

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `author` | user_ref | ✓ | 创建者,引用飞书 user_id |
| `owner` | user_ref | ✓ | 当前负责人(可与 author 不同) |
| `reviewers` | user_ref[] | ✗ | 默认评审人,资产入库时自动 @ |
| `purpose` | string(≤140字) | ✓ | 一句话说明这个资产解决什么问题 |
| `tags` | string[] | ✗ | 自定义标签,大小写不敏感,统一小写 |

## 6. 关联字段(代码 / 源文件 / 评审)

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `figma` | figma_ref | ✗ | Figma 节点指针,见 §6.1 |
| `code` | code_ref[] | ✗ | 前端代码引用,见 §6.2 |
| `review_id` | UUID | ✗ | 最近一次评审记录 ID |
| `supersedes` | UUID | ✗ | 被本资产取代的旧资产 ID |
| `superseded_by` | UUID | ✗ | 取代本资产的新版本 ID |

### 6.1 `figma_ref` 结构

```json
{
  "file_key": "abc123XYZ",
  "node_id": "1:23",
  "version": 1234567890,
  "synced_at": "2026-08-24T03:00:00Z"
}
```

### 6.2 `code_ref` 结构

```json
{
  "repo": "frontend/monorepo",
  "path": "packages/ui/src/Button.tsx",
  "commit_sha": "a1b2c3d4",
  "token_binding": "color.brand.primary"
}
```

## 7. 版本字段(`versions[]`)

每次资产更新产生一条版本记录,**不覆盖**历史:

```json
{
  "version": "1.2.0",
  "created_at": "2026-09-15T10:30:00Z",
  "author": "user_ref",
  "changelog": "圆角从 4px 改为 8px,适配新品牌规范",
  "figma_version": 1234567890,
  "code_sha": "a1b2c3d4",
  "review_id": "uuid"
}
```

## 8. 待定事项(Phase 1 入库前需明确)

- [ ] `id` 命名空间:全局 UUID 还是按 `kind` 加前缀(便于人眼分类)?
- [ ] `tags` 是否引入本体(ontology)而非自由文本?(避免"按钮/Button/btn"三标签并存)
- [ ] `figma_ref.synced_at` 超过 N 天是否触发"图-码不一致"告警?
- [ ] 评审记录是内嵌在本资产还是独立表关联?

## 9. 不做什么

- 不在本期引入"视觉相似度 hash"(Phase 2 用 CLIP 另算)
- 不做权限/可见性字段(资产库内部全开,外部权限走仓库 ACL)
- 不做"喜欢数 / 浏览数"等社交字段(评审记录已承载质量信号)
