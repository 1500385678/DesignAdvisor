import Link from "next/link";

type ReviewSummary = {
  id: string;
  title: string;
  asset_id: string | null;
  status: string;
  decision: string;
  priority: string;
  created_by: string;
  reviewer_count: number;
  created_at: string;
  updated_at: string;
};

type ReviewsResponse = {
  total: number;
  returned: number;
  reviews: ReviewSummary[];
};

type ReviewsSummaryResponse = {
  total: number;
  by_status: Record<string, number>;
  by_decision: Record<string, number>;
  by_priority: Record<string, number>;
  namespaces: Record<string, { current: number; target: number | null; note: string }>;
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

// 6 状态过滤(对齐 api/reviews.py _REVIEW_STATUSES)
const STATUSES = [
  { value: "", label: "全部 6 状态" },
  { value: "draft", label: "草稿" },
  { value: "in_review", label: "评审中" },
  { value: "approved", label: "已批准" },
  { value: "rejected", label: "已拒绝" },
  { value: "deprecated", label: "已弃用" },
  { value: "archived", label: "已归档" },
];

// 4 优先级过滤
const PRIORITIES = [
  { value: "", label: "全部 4 优先级" },
  { value: "low", label: "低" },
  { value: "medium", label: "中" },
  { value: "high", label: "高" },
  { value: "blocker", label: "阻塞" },
];

// status / decision / priority → 中文标签
const STATUS_LABELS: Record<string, string> = {
  draft: "草稿",
  in_review: "评审中",
  approved: "已批准",
  rejected: "已拒绝",
  deprecated: "已弃用",
  archived: "已归档",
};

const DECISION_LABELS: Record<string, string> = {
  pending: "待投票",
  approved: "通过",
  rejected_with_reason: "拒绝(含原因)",
  request_changes: "请求修改",
};

const PRIORITY_LABELS: Record<string, string> = {
  low: "低",
  medium: "中",
  high: "高",
  blocker: "阻塞",
};

// 优先级配色(高优先级更醒目)
const PRIORITY_STYLES: Record<string, string> = {
  low: "bg-white/5 text-ink-50/50",
  medium: "bg-blue-500/15 text-blue-300",
  high: "bg-orange-500/15 text-orange-300",
  blocker: "bg-red-500/20 text-red-300",
};

// 状态配色
const STATUS_STYLES: Record<string, string> = {
  draft: "border-white/15 text-ink-50/50",
  in_review: "border-yellow-500/40 text-yellow-300",
  approved: "border-emerald-500/40 text-emerald-300",
  rejected: "border-red-500/40 text-red-300",
  deprecated: "border-white/10 text-ink-50/30 line-through",
  archived: "border-white/5 text-ink-50/30",
};

async function fetchReviews(opts: {
  status?: string;
  priority?: string;
}): Promise<ReviewsResponse | null> {
  const params = new URLSearchParams();
  if (opts.status) params.set("status", opts.status);
  if (opts.priority) params.set("priority", opts.priority);
  const qs = params.toString();
  const url = `${API_BASE.replace(/\/$/, "")}/api/v1/reviews${
    qs ? `?${qs}` : ""
  }`;
  try {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) {
      console.error(`[reviews/page] fetch ${url} -> ${res.status}`);
      return null;
    }
    return (await res.json()) as ReviewsResponse;
  } catch (err) {
    console.error(`[reviews/page] fetch ${url} failed:`, err);
    return null;
  }
}

async function fetchSummary(): Promise<ReviewsSummaryResponse | null> {
  const url = `${API_BASE.replace(/\/$/, "")}/api/v1/reviews/summary`;
  try {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) {
      console.error(`[reviews/page] summary ${url} -> ${res.status}`);
      return null;
    }
    return (await res.json()) as ReviewsSummaryResponse;
  } catch (err) {
    console.error(`[reviews/page] summary ${url} failed:`, err);
    return null;
  }
}

export default async function ReviewsPage({
  searchParams,
}: {
  searchParams: { status?: string; priority?: string };
}) {
  const status = searchParams.status ?? "";
  const priority = searchParams.priority ?? "";

  // 两路并发:列表(按过滤)+ 摘要
  const [reviewsResp, summary] = await Promise.all([
    fetchReviews({ status, priority }),
    fetchSummary(),
  ]);

  const reviews = reviewsResp?.reviews ?? [];
  const totalAll = reviewsResp?.total ?? 0;
  const returned = reviewsResp?.returned ?? 0;

  // 6 状态计数卡(对齐 summary.namespaces)
  const statusCards = summary
    ? (["draft", "in_review", "approved", "rejected", "deprecated", "archived"] as const).map(
        (s) => ({
          key: s,
          label: STATUS_LABELS[s] ?? s,
          current: summary.namespaces?.[s]?.current ?? 0,
        })
      )
    : [];

  return (
    <main className="mx-auto max-w-5xl px-6 py-16">
      <header className="mb-10">
        <p className="text-sm uppercase tracking-widest text-accent">
          DesignAdvisor · 设计评审
        </p>
        <h1 className="mt-3 text-3xl font-semibold leading-tight">
          Phase 1 #2 · 设计评审协作 v0.1
        </h1>
        <p className="mt-3 max-w-2xl text-sm text-ink-50/70">
          消费后端
          <code className="mx-1 rounded bg-white/5 px-1.5 py-0.5 text-xs">
            api/reviews.py
          </code>
          6 端点 · 6 状态机 + 4 决策 + 4 优先级 · 字段口径对齐
          <code className="mx-1 rounded bg-white/5 px-1.5 py-0.5 text-xs">
            docs/02-设计资产元数据-schema v0.1 §6
          </code>
          · 决策日志 + 转移日志 append-only(审计面留痕)。
        </p>
        <p className="mt-3 text-xs text-ink-50/40">
          <Link href="/" className="text-accent hover:underline">
            ← 返回首页
          </Link>
          <span className="mx-2 text-ink-50/20">|</span>
          <Link href="/assets" className="text-accent hover:underline">
            资产库 →
          </Link>
        </p>
      </header>

      {/* 6 状态计数卡 */}
      {statusCards.length > 0 && (
        <section className="mb-8 grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
          {statusCards.map((c) => (
            <div
              key={c.key}
              className="rounded-xl border border-white/10 bg-white/[0.02] p-4"
            >
              <p className="text-xs uppercase tracking-widest text-ink-50/40">
                {c.label}
              </p>
              <p className="mt-2 text-2xl font-semibold text-ink-50">
                {c.current}
              </p>
            </div>
          ))}
        </section>
      )}

      {/* 过滤表单(GET · URL 状态可分享) */}
      <form
        action="/reviews"
        method="get"
        className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center"
      >
        <select
          name="status"
          defaultValue={status}
          className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2.5 text-sm text-ink-50 focus:border-accent/60 focus:outline-none"
        >
          {STATUSES.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
        <select
          name="priority"
          defaultValue={priority}
          className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2.5 text-sm text-ink-50 focus:border-accent/60 focus:outline-none"
        >
          {PRIORITIES.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </select>
        <button
          type="submit"
          className="rounded-lg border border-accent/40 bg-accent/10 px-5 py-2.5 text-sm font-medium text-accent transition hover:bg-accent/20"
        >
          过滤
        </button>
        {(status || priority) && (
          <Link
            href="/reviews"
            className="rounded-lg border border-white/10 px-4 py-2.5 text-center text-sm text-ink-50/60 transition hover:border-white/30"
          >
            清除
          </Link>
        )}
      </form>

      {/* 结果区 */}
      <section>
        <div className="mb-4 flex items-baseline justify-between">
          <p className="text-xs uppercase tracking-widest text-ink-50/40">
            {status
              ? `状态:${STATUS_LABELS[status] ?? status}`
              : priority
                ? `优先级:${PRIORITY_LABELS[priority] ?? priority}`
                : "全部评审"}
          </p>
          <p className="text-xs text-ink-50/40">
            命中 {returned} / {totalAll} 件
          </p>
        </div>

        {reviews.length === 0 ? (
          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-10 text-center text-sm text-ink-50/50">
            没有命中结果。试试其他过滤条件,或
            <Link href="/reviews" className="ml-1 text-accent hover:underline">
              清除筛选
            </Link>
            。
          </div>
        ) : (
          <ul className="grid grid-cols-1 gap-3">
            {reviews.map((r) => (
              <li
                key={r.id}
                className="rounded-xl border border-white/10 bg-white/[0.02] p-4 transition hover:border-accent/60"
              >
                <div className="flex items-baseline justify-between gap-3">
                  <div className="flex items-baseline gap-2">
                    <span className="font-mono text-xs text-accent">{r.id}</span>
                    <span
                      className={`rounded-md border px-2 py-0.5 text-[10px] uppercase tracking-wide ${
                        STATUS_STYLES[r.status] ?? "border-white/10 text-ink-50/50"
                      }`}
                    >
                      {STATUS_LABELS[r.status] ?? r.status}
                    </span>
                    <span
                      className={`rounded-md px-2 py-0.5 text-[10px] ${
                        PRIORITY_STYLES[r.priority] ?? "bg-white/5 text-ink-50/50"
                      }`}
                    >
                      优先级 · {PRIORITY_LABELS[r.priority] ?? r.priority}
                    </span>
                  </div>
                  <span className="text-[10px] text-ink-50/40">
                    {new Date(r.created_at).toLocaleString("zh-CN", {
                      hour12: false,
                    })}
                  </span>
                </div>
                <p className="mt-2 text-sm text-ink-50/80">{r.title}</p>
                <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] text-ink-50/40">
                  <span>决策 · {DECISION_LABELS[r.decision] ?? r.decision}</span>
                  <span>评审人 · {r.reviewer_count} 位</span>
                  {r.asset_id && (
                    <span>
                      关联资产 ·{" "}
                      <code className="rounded bg-white/5 px-1 py-0.5 font-mono text-[10px] text-ink-50/60">
                        {r.asset_id}
                      </code>
                    </span>
                  )}
                  <span>创建 · {r.created_by}</span>
                </div>
                <p className="mt-2 text-[10px] text-ink-50/30">
                  详情 / 状态切换:Phase 1 #2 切第二刀 · Web 端评审详情页 v0.2(下一刀)
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>

      <footer className="mt-12 border-t border-white/10 pt-6 text-xs text-ink-50/40">
        <p>
          API:
          <code className="ml-1 rounded bg-white/5 px-1.5 py-0.5">
            /api/v1/reviews
          </code>
          +
          <code className="ml-1 rounded bg-white/5 px-1.5 py-0.5">
            /api/v1/reviews/summary
          </code>
          · 后端 v0.5.0(2026-09-12)· Web 消费 v0.5 → **v0.6**(2026-09-14)
        </p>
        <p className="mt-1">
          不做什么(留待后续 T1-T5):评审详情页 v0.2(
          <code>GET /{`{review_id}`}</code> + 状态切换 UI + 决策投票 UI)· 飞书通知 v0.1
          (评审创建/状态变更 @ 飞书群)· SQLite 持久化 · 票数聚合 + 阈值通过
        </p>
      </footer>
    </main>
  );
}
