import Link from "next/link";
import { notFound } from "next/navigation";
import ReviewActions from "./ReviewActions";

type ReviewDetail = {
  id: string;
  title: string;
  description: string;
  asset_id: string | null;
  status: string;
  decision: string;
  priority: string;
  created_by: string;
  reviewers: string[];
  created_at: string;
  updated_at: string;
  decisions_log: Array<{
    decision: string;
    voter: string;
    comment: string;
    at: string;
  }>;
  transitions_log: Array<{
    from: string;
    to: string;
    reason: string;
    actor: string;
    at: string;
  }>;
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

// 6 状态中文映射
const STATUS_LABELS: Record<string, string> = {
  draft: "草稿",
  in_review: "评审中",
  approved: "已批准",
  rejected: "已拒绝",
  deprecated: "已弃用",
  archived: "已归档",
};

// 4 决策中文映射
const DECISION_LABELS: Record<string, string> = {
  pending: "待投票",
  approved: "通过",
  rejected_with_reason: "拒绝(含原因)",
  request_changes: "请求修改",
};

// 4 优先级中文映射
const PRIORITY_LABELS: Record<string, string> = {
  low: "低",
  medium: "中",
  high: "高",
  blocker: "阻塞",
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

// 决策配色(评审进度卡复用)
const DECISION_STYLES: Record<string, string> = {
  pending: "border-white/15 bg-white/5 text-ink-50/50",
  approved: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
  rejected_with_reason: "border-red-500/40 bg-red-500/10 text-red-300",
  request_changes: "border-orange-500/40 bg-orange-500/10 text-orange-300",
};

// 评审进度 4 决策固定顺序(供进度卡用)
const DECISION_ORDER = [
  "approved",
  "rejected_with_reason",
  "request_changes",
  "pending",
] as const;

// 优先级配色
const PRIORITY_STYLES: Record<string, string> = {
  low: "bg-white/5 text-ink-50/50",
  medium: "bg-blue-500/15 text-blue-300",
  high: "bg-orange-500/15 text-orange-300",
  blocker: "bg-red-500/20 text-red-300",
};

// 6 状态机合法转移表(对齐 api/reviews.py _REVIEW_TRANSITIONS)
const TRANSITIONS: Record<string, string[]> = {
  draft: ["in_review", "archived"],
  in_review: ["approved", "rejected", "draft", "archived"],
  approved: ["deprecated", "archived"],
  rejected: ["in_review", "archived"],
  deprecated: ["archived"],
  archived: [],
};

async function fetchReviewDetail(
  reviewId: string
): Promise<ReviewDetail | null> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/reviews/${reviewId}`, {
      cache: "no-store",
    });
    if (res.status === 404) return null;
    if (!res.ok) {
      console.error(`fetchReviewDetail ${reviewId} failed: ${res.status}`);
      return null;
    }
    return (await res.json()) as ReviewDetail;
  } catch (err) {
    console.error(`fetchReviewDetail ${reviewId} error:`, err);
    return null;
  }
}

export default async function ReviewDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const reviewId = params.id;
  const review = await fetchReviewDetail(reviewId);

  if (!review) {
    notFound();
  }

  const createdAt = new Date(review.created_at).toLocaleString("zh-CN", {
    hour12: false,
  });
  const updatedAt = new Date(review.updated_at).toLocaleString("zh-CN", {
    hour12: false,
  });

  const legalTransitions = TRANSITIONS[review.status] ?? [];

  // 评审进度:按 4 决策汇总票数(对齐 api/reviews.py DECISION enum)
  // 同一评审人多次投票时按"最新一次"计(每人在 decisions_log 取 last)
  const latestVoteByVoter = new Map<string, string>();
  for (const d of review.decisions_log) {
    latestVoteByVoter.set(d.voter, d.decision);
  }
  const voteCounts: Record<string, number> = {
    pending: 0,
    approved: 0,
    rejected_with_reason: 0,
    request_changes: 0,
  };
  for (const dec of latestVoteByVoter.values()) {
    if (dec in voteCounts) voteCounts[dec] += 1;
  }
  const totalReviewers = review.reviewers.length;
  const votedReviewers = latestVoteByVoter.size;

  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      {/* 顶部导航 */}
      <div className="mb-6 flex items-center justify-between">
        <Link
          href="/reviews"
          className="text-xs text-ink-50/50 transition hover:text-accent"
        >
          ← 返回评审列表
        </Link>
        <Link
          href="/"
          className="text-xs text-ink-50/30 transition hover:text-ink-50/60"
        >
          主页
        </Link>
      </div>

      {/* 标题区 */}
      <header className="mb-8">
        <div className="mb-2 flex items-baseline gap-3">
          <span className="font-mono text-sm text-accent">{review.id}</span>
          <span
            className={`rounded-md border px-2 py-0.5 text-[10px] uppercase tracking-wide ${
              STATUS_STYLES[review.status] ?? "border-white/10 text-ink-50/50"
            }`}
          >
            {STATUS_LABELS[review.status] ?? review.status}
          </span>
          <span
            className={`rounded-md px-2 py-0.5 text-[10px] ${
              PRIORITY_STYLES[review.priority] ?? "bg-white/5 text-ink-50/50"
            }`}
          >
            优先级 · {PRIORITY_LABELS[review.priority] ?? review.priority}
          </span>
        </div>
        <h1 className="text-3xl font-semibold leading-tight">{review.title}</h1>
        {review.description && (
          <p className="mt-3 text-sm leading-relaxed text-ink-50/70">
            {review.description}
          </p>
        )}
      </header>

      {/* 元数据卡 */}
      <section className="mb-8 grid grid-cols-1 gap-4 rounded-2xl border border-white/10 bg-white/[0.02] p-6 sm:grid-cols-2">
        <div>
          <p className="text-[10px] uppercase tracking-widest text-ink-50/40">
            创建人
          </p>
          <p className="mt-1 font-mono text-xs text-ink-50/70">
            {review.created_by}
          </p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-widest text-ink-50/40">
            当前决策
          </p>
          <p className="mt-1 text-xs text-ink-50/70">
            {DECISION_LABELS[review.decision] ?? review.decision}
          </p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-widest text-ink-50/40">
            关联资产
          </p>
          <p className="mt-1 text-xs text-ink-50/70">
            {review.asset_id ? (
              <code className="rounded bg-white/5 px-1.5 py-0.5 font-mono text-[11px] text-accent">
                {review.asset_id}
              </code>
            ) : (
              <span className="text-ink-50/40">独立评审(无关联资产)</span>
            )}
          </p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-widest text-ink-50/40">
            评审人({review.reviewers.length} 位)
          </p>
          <p className="mt-1 text-xs text-ink-50/70">
            {review.reviewers.length > 0
              ? review.reviewers.map((r) => (
                  <code
                    key={r}
                    className="mr-1 inline-block rounded bg-white/5 px-1.5 py-0.5 font-mono text-[11px]"
                  >
                    {r}
                  </code>
                ))
              : "暂未指定评审人"}
          </p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-widest text-ink-50/40">
            创建时间
          </p>
          <p className="mt-1 font-mono text-xs text-ink-50/70">{createdAt}</p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-widest text-ink-50/40">
            最后更新
          </p>
          <p className="mt-1 font-mono text-xs text-ink-50/70">{updatedAt}</p>
        </div>
      </section>

      {/* 评审进度 · 4 决策票数汇总(切第六刀票数聚合阈值通过的前置视图) */}
      <section className="mb-8 rounded-2xl border border-white/10 bg-white/[0.02] p-6">
        <div className="mb-4 flex items-baseline justify-between">
          <h2 className="text-[10px] uppercase tracking-widest text-ink-50/40">
            评审进度
          </h2>
          <span className="text-[10px] font-mono text-ink-50/30">
            已投 {votedReviewers} / 评审人 {totalReviewers}
          </span>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {DECISION_ORDER.map((dec) => {
            const count = voteCounts[dec] ?? 0;
            const isCurrent = review.decision === dec;
            return (
              <div
                key={dec}
                className={`rounded-xl border p-3 text-center transition ${
                  isCurrent
                    ? DECISION_STYLES[dec]
                    : "border-white/10 bg-white/[0.02] text-ink-50/40"
                } ${isCurrent ? "ring-1 ring-accent/40" : ""}`}
              >
                <p className="text-[10px] uppercase tracking-wide">
                  {DECISION_LABELS[dec] ?? dec}
                </p>
                <p
                  className={`mt-1 font-mono text-2xl ${
                    isCurrent ? "" : "text-ink-50/40"
                  }`}
                >
                  {count}
                </p>
                {isCurrent && (
                  <p className="mt-0.5 text-[9px] uppercase tracking-widest opacity-70">
                    current
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* 状态机 + 决策投票 - 客户端组件 */}
      <ReviewActions
        reviewId={review.id}
        currentStatus={review.status}
        currentDecision={review.decision}
        legalTransitions={legalTransitions}
        currentReviewers={review.reviewers}
      />

      {/* 转移日志时间线 */}
      <section className="mt-8">
        <div className="mb-3 flex items-baseline justify-between">
          <h2 className="text-xs uppercase tracking-widest text-ink-50/40">
            状态机转移日志({review.transitions_log.length})
          </h2>
          <span className="text-[10px] text-ink-50/30">append-only</span>
        </div>
        {review.transitions_log.length === 0 ? (
          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-6 text-center text-xs text-ink-50/40">
            尚无状态转移记录
          </div>
        ) : (
          <ol className="space-y-2">
            {review.transitions_log
              .slice()
              .reverse()
              .map((t, idx) => (
                <li
                  key={`${t.at}-${idx}`}
                  className="rounded-lg border border-white/10 bg-white/[0.02] p-3"
                >
                  <div className="flex items-baseline justify-between gap-3">
                    <div className="flex items-baseline gap-2 text-xs">
                      <span
                        className={`rounded-md border px-1.5 py-0.5 text-[10px] ${
                          STATUS_STYLES[t.from] ??
                          "border-white/10 text-ink-50/50"
                        }`}
                      >
                        {STATUS_LABELS[t.from] ?? t.from}
                      </span>
                      <span className="text-ink-50/40">→</span>
                      <span
                        className={`rounded-md border px-1.5 py-0.5 text-[10px] ${
                          STATUS_STYLES[t.to] ?? "border-white/10 text-ink-50/50"
                        }`}
                      >
                        {STATUS_LABELS[t.to] ?? t.to}
                      </span>
                      <span className="text-[10px] text-ink-50/40">
                        · {t.actor}
                      </span>
                    </div>
                    <span className="font-mono text-[10px] text-ink-50/40">
                      {new Date(t.at).toLocaleString("zh-CN", { hour12: false })}
                    </span>
                  </div>
                  {t.reason && (
                    <p className="mt-2 text-xs text-ink-50/60">"{t.reason}"</p>
                  )}
                </li>
              ))}
          </ol>
        )}
      </section>

      {/* 决策日志时间线 */}
      <section className="mt-8">
        <div className="mb-3 flex items-baseline justify-between">
          <h2 className="text-xs uppercase tracking-widest text-ink-50/40">
            决策投票日志({review.decisions_log.length})
          </h2>
          <span className="text-[10px] text-ink-50/30">append-only</span>
        </div>
        {review.decisions_log.length === 0 ? (
          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-6 text-center text-xs text-ink-50/40">
            尚无投票记录
          </div>
        ) : (
          <ol className="space-y-2">
            {review.decisions_log
              .slice()
              .reverse()
              .map((d, idx) => (
                <li
                  key={`${d.at}-${idx}`}
                  className="rounded-lg border border-white/10 bg-white/[0.02] p-3"
                >
                  <div className="flex items-baseline justify-between gap-3">
                    <div className="flex items-baseline gap-2 text-xs">
                      <span className="rounded-md bg-accent/15 px-2 py-0.5 text-[10px] text-accent">
                        {DECISION_LABELS[d.decision] ?? d.decision}
                      </span>
                      <span className="text-[10px] text-ink-50/40">
                        · {d.voter}
                      </span>
                    </div>
                    <span className="font-mono text-[10px] text-ink-50/40">
                      {new Date(d.at).toLocaleString("zh-CN", { hour12: false })}
                    </span>
                  </div>
                  {d.comment && (
                    <p className="mt-2 text-xs text-ink-50/60">"{d.comment}"</p>
                  )}
                </li>
              ))}
          </ol>
        )}
      </section>

      {/* 页脚 */}
      <footer className="mt-12 border-t border-white/10 pt-6 text-xs text-ink-50/40">
        <p>
          API:
          <code className="ml-1 rounded bg-white/5 px-1.5 py-0.5">
            GET /api/v1/reviews/{`{review_id}`}
          </code>
          +
          <code className="ml-1 rounded bg-white/5 px-1.5 py-0.5">
            PATCH /api/v1/reviews/{`{review_id}`}/transition
          </code>
          +
          <code className="ml-1 rounded bg-white/5 px-1.5 py-0.5">
            PATCH /api/v1/reviews/{`{review_id}`}/decision
          </code>
          · 后端 v0.5.0(2026-09-12)· Web 消费 v0.6 → <strong>v0.7</strong>
          (2026-09-15,Phase 1 #2 切第三刀 - Web 端评审详情页 v0.1)
        </p>
        <p className="mt-1">
          不做什么(留待后续 T1-T5):飞书通知 v0.1(评审创建/状态变更 @
          飞书群)· SQLite 持久化(替代内存 fake-load)· 票数聚合 + 阈值通过
        </p>
      </footer>
    </main>
  );
}