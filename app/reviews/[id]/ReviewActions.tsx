"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

type Props = {
  reviewId: string;
  currentStatus: string;
  currentDecision: string;
  legalTransitions: string[];
  currentReviewers: string[];
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

// 状态中文
const STATUS_LABELS: Record<string, string> = {
  draft: "草稿",
  in_review: "评审中",
  approved: "已批准",
  rejected: "已拒绝",
  deprecated: "已弃用",
  archived: "已归档",
};

// 决策中文
const DECISION_LABELS: Record<string, string> = {
  pending: "待投票",
  approved: "通过",
  rejected_with_reason: "拒绝(含原因)",
  request_changes: "请求修改",
};

// 决策配色
const DECISION_STYLES: Record<string, string> = {
  approved: "border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/10",
  rejected_with_reason: "border-red-500/40 text-red-300 hover:bg-red-500/10",
  request_changes: "border-orange-500/40 text-orange-300 hover:bg-orange-500/10",
  pending: "border-white/15 text-ink-50/50 hover:bg-white/5",
};

// 状态配色(用于 transition 按钮)
const TRANSITION_STYLES: Record<string, string> = {
  in_review: "border-yellow-500/40 text-yellow-300 hover:bg-yellow-500/10",
  approved: "border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/10",
  rejected: "border-red-500/40 text-red-300 hover:bg-red-500/10",
  draft: "border-white/15 text-ink-50/50 hover:bg-white/5",
  deprecated: "border-white/10 text-ink-50/40 hover:bg-white/5",
  archived: "border-white/5 text-ink-50/30 hover:bg-white/5",
};

export default function ReviewActions({
  reviewId,
  currentStatus,
  currentDecision,
  legalTransitions,
  currentReviewers,
}: Props) {
  const router = useRouter();
  const [transitionTo, setTransitionTo] = useState<string>("");
  const [transitionReason, setTransitionReason] = useState<string>("");
  const [voter, setVoter] = useState<string>(
    currentReviewers[0] ?? "feishu:placeholder"
  );
  const [decisionTo, setDecisionTo] = useState<string>("");
  const [decisionComment, setDecisionComment] = useState<string>("");
  const [busy, setBusy] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<
    | { kind: "ok" | "err"; msg: string }
    | null
  >(null);

  const canVote =
    currentStatus === "in_review" ||
    currentStatus === "approved" ||
    currentStatus === "rejected";

  async function doTransition() {
    if (!transitionTo) {
      setFeedback({ kind: "err", msg: "请选择目标状态" });
      return;
    }
    setBusy(true);
    setFeedback(null);
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/reviews/${reviewId}/transition`,
        {
          method: "PATCH",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            to: transitionTo,
            reason: transitionReason,
          }),
        }
      );
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setFeedback({
          kind: "err",
          msg: `状态转移失败:HTTP ${res.status} · ${
            body.detail ?? "未知错误"
          }`,
        });
        return;
      }
      setFeedback({
        kind: "ok",
        msg: `状态已转移 → ${STATUS_LABELS[transitionTo] ?? transitionTo}`,
      });
      setTransitionTo("");
      setTransitionReason("");
      // 刷新服务端组件
      router.refresh();
    } catch (err) {
      setFeedback({
        kind: "err",
        msg: `状态转移异常:${err instanceof Error ? err.message : String(err)}`,
      });
    } finally {
      setBusy(false);
    }
  }

  async function doDecision() {
    if (!decisionTo) {
      setFeedback({ kind: "err", msg: "请选择决策" });
      return;
    }
    if (!voter.trim()) {
      setFeedback({ kind: "err", msg: "请填写投票人(voter)" });
      return;
    }
    setBusy(true);
    setFeedback(null);
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/reviews/${reviewId}/decision`,
        {
          method: "PATCH",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            decision: decisionTo,
            voter: voter.trim(),
            comment: decisionComment,
          }),
        }
      );
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setFeedback({
          kind: "err",
          msg: `投票失败:HTTP ${res.status} · ${body.detail ?? "未知错误"}`,
        });
        return;
      }
      setFeedback({
        kind: "ok",
        msg: `已投票 → ${DECISION_LABELS[decisionTo] ?? decisionTo}`,
      });
      setDecisionTo("");
      setDecisionComment("");
      router.refresh();
    } catch (err) {
      setFeedback({
        kind: "err",
        msg: `投票异常:${err instanceof Error ? err.message : String(err)}`,
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      {/* 状态机转移 */}
      <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
        <div className="mb-3 flex items-baseline justify-between">
          <h3 className="text-xs uppercase tracking-widest text-ink-50/40">
            状态机转移
          </h3>
          <span className="text-[10px] text-ink-50/30">
            当前 · {STATUS_LABELS[currentStatus] ?? currentStatus}
          </span>
        </div>

        {legalTransitions.length === 0 ? (
          <p className="text-xs text-ink-50/40">
            终态,无可用转移路径。
          </p>
        ) : (
          <>
            <div className="mb-3 flex flex-wrap gap-2">
              {legalTransitions.map((t) => (
                <button
                  key={t}
                  type="button"
                  disabled={busy}
                  onClick={() => setTransitionTo(t)}
                  className={`rounded-md border px-3 py-1.5 text-xs transition ${
                    transitionTo === t
                      ? `${TRANSITION_STYLES[t] ?? "border-white/15"} ring-2 ring-accent/40`
                      : TRANSITION_STYLES[t] ??
                        "border-white/15 text-ink-50/50 hover:bg-white/5"
                  } disabled:opacity-40`}
                >
                  → {STATUS_LABELS[t] ?? t}
                </button>
              ))}
            </div>
            <input
              type="text"
              maxLength={280}
              value={transitionReason}
              onChange={(e) => setTransitionReason(e.target.value)}
              placeholder="转移原因(0-280 字,可选)"
              className="mb-2 w-full rounded-md border border-white/10 bg-white/[0.02] px-3 py-2 text-xs text-ink-50/80 placeholder:text-ink-50/30 focus:border-accent/40 focus:outline-none"
            />
            <button
              type="button"
              disabled={busy || !transitionTo}
              onClick={doTransition}
              className="w-full rounded-md bg-accent/80 px-3 py-2 text-xs font-medium text-white transition hover:bg-accent disabled:opacity-40"
            >
              {busy ? "处理中..." : "提交状态转移"}
            </button>
            <p className="mt-2 text-[10px] text-ink-50/30">
              合法路径来自 _REVIEW_TRANSITIONS(
              {Object.entries({
                draft: "in_review, archived",
                in_review: "approved, rejected, draft, archived",
                approved: "deprecated, archived",
                rejected: "in_review, archived",
                deprecated: "archived",
              })
                .filter(([k]) => k === currentStatus)
                .map(([, v]) => v)
                .join(", ")}
              ),非法转移返 422。
            </p>
          </>
        )}
      </div>

      {/* 决策投票 */}
      <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
        <div className="mb-3 flex items-baseline justify-between">
          <h3 className="text-xs uppercase tracking-widest text-ink-50/40">
            评审人投票
          </h3>
          <span className="text-[10px] text-ink-50/30">
            当前 · {DECISION_LABELS[currentDecision] ?? currentDecision}
          </span>
        </div>

        {!canVote ? (
          <p className="text-xs text-ink-50/40">
            当前状态 {STATUS_LABELS[currentStatus] ?? currentStatus}{" "}
            不允许投票,需先 transition 到 in_review。
          </p>
        ) : (
          <>
            <div className="mb-3 flex flex-wrap gap-2">
              {(
                [
                  "approved",
                  "rejected_with_reason",
                  "request_changes",
                  "pending",
                ] as const
              ).map((d) => (
                <button
                  key={d}
                  type="button"
                  disabled={busy}
                  onClick={() => setDecisionTo(d)}
                  className={`rounded-md border px-3 py-1.5 text-xs transition ${
                    decisionTo === d
                      ? `${DECISION_STYLES[d] ?? "border-white/15"} ring-2 ring-accent/40`
                      : DECISION_STYLES[d] ?? "border-white/15 text-ink-50/50"
                  } disabled:opacity-40`}
                >
                  {DECISION_LABELS[d] ?? d}
                </button>
              ))}
            </div>
            <input
              type="text"
              maxLength={80}
              value={voter}
              onChange={(e) => setVoter(e.target.value)}
              placeholder="投票人 voter(飞书 user_id)"
              className="mb-2 w-full rounded-md border border-white/10 bg-white/[0.02] px-3 py-2 font-mono text-xs text-ink-50/80 placeholder:text-ink-50/30 focus:border-accent/40 focus:outline-none"
            />
            <input
              type="text"
              maxLength={280}
              value={decisionComment}
              onChange={(e) => setDecisionComment(e.target.value)}
              placeholder="投票意见(0-280 字,可选)"
              className="mb-2 w-full rounded-md border border-white/10 bg-white/[0.02] px-3 py-2 text-xs text-ink-50/80 placeholder:text-ink-50/30 focus:border-accent/40 focus:outline-none"
            />
            <button
              type="button"
              disabled={busy || !decisionTo || !voter.trim()}
              onClick={doDecision}
              className="w-full rounded-md bg-accent/80 px-3 py-2 text-xs font-medium text-white transition hover:bg-accent disabled:opacity-40"
            >
              {busy ? "处理中..." : "提交投票"}
            </button>
            <p className="mt-2 text-[10px] text-ink-50/30">
              决策日志 append-only(voter + comment + at),Phase 1
              #2 切第六刀会引入"票数聚合 + 阈值通过"取代单票同步。
            </p>
          </>
        )}
      </div>

      {/* 反馈条 */}
      {feedback && (
        <div
          className={`rounded-lg border px-3 py-2 text-xs lg:col-span-2 ${
            feedback.kind === "ok"
              ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-300"
              : "border-red-500/30 bg-red-500/5 text-red-300"
          }`}
        >
          {feedback.msg}
        </div>
      )}
    </section>
  );
}