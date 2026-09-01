import Link from "next/link";

type Asset = {
  id: string;
  kind: string;
  version: string;
  status: string;
  category: string;
  purpose: string;
  tags: string[];
  code_ref_count: number;
  figma_synced: boolean;
};

type AssetsSummary = {
  total: number;
  by_kind: Record<string, number>;
  by_category: Record<string, number>;
  namespaces: Record<
    string,
    { current: number; target: number | null; note: string }
  >;
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

// 4 类资产 kind 过滤(与 api/assets.py router 端点 ?kind= 对齐)
const KINDS = [
  { value: "", label: "全部 4 类" },
  { value: "component", label: "组件" },
  { value: "page", label: "页面" },
  { value: "token", label: "令牌" },
  { value: "reference", label: "参考" },
];

// 4 类状态(对齐 docs/02-schema §3 状态机)
const STATUSES = [
  { value: "", label: "全部状态" },
  { value: "draft", label: "草稿" },
  { value: "in_review", label: "评审中" },
  { value: "approved", label: "已批准" },
  { value: "deprecated", label: "已弃用" },
  { value: "archived", label: "已归档" },
];

// kind → 中文标签
const KIND_LABELS: Record<string, string> = {
  component: "组件",
  page: "页面",
  token: "令牌",
  reference: "参考",
};

// status → 中文标签
const STATUS_LABELS: Record<string, string> = {
  draft: "草稿",
  in_review: "评审中",
  approved: "已批准",
  deprecated: "已弃用",
  archived: "已归档",
};

async function fetchAssets(opts: {
  kind?: string;
  category?: string;
  status?: string;
}): Promise<{ items: Asset[]; summary: AssetsSummary | null }> {
  const params = new URLSearchParams();
  if (opts.kind) params.set("kind", opts.kind);
  if (opts.category) params.set("category", opts.category);
  if (opts.status) params.set("status", opts.status);
  const qs = params.toString();

  const assetsUrl = `${API_BASE.replace(/\/$/, "")}/api/v1/assets${
    qs ? `?${qs}` : ""
  }`;

  try {
    const res = await fetch(assetsUrl, { cache: "no-store" });
    if (!res.ok) {
      console.error(`[assets/page] fetch ${assetsUrl} -> ${res.status}`);
      return { items: [], summary: null };
    }
    const data = (await res.json()) as { assets: Asset[] };
    return { items: data.assets ?? [], summary: null };
  } catch (err) {
    console.error(`[assets/page] fetch ${assetsUrl} failed:`, err);
    return { items: [], summary: null };
  }
}

async function fetchSummary(): Promise<AssetsSummary | null> {
  const url = `${API_BASE.replace(/\/$/, "")}/api/v1/assets/summary`;
  try {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) {
      console.error(`[assets/page] summary ${url} -> ${res.status}`);
      return null;
    }
    return (await res.json()) as AssetsSummary;
  } catch (err) {
    console.error(`[assets/page] summary ${url} failed:`, err);
    return null;
  }
}

export default async function AssetsPage({
  searchParams,
}: {
  searchParams: { kind?: string; category?: string; status?: string };
}) {
  const kind = searchParams.kind ?? "";
  const category = searchParams.category ?? "";
  const status = searchParams.status ?? "";

  // 列表 + 摘要(摘要用于顶部 4 类计数卡,不随过滤项变化)
  const [{ items }, summary] = await Promise.all([
    fetchAssets({ kind, category, status }),
    fetchSummary(),
  ]);

  // 顶部 4 类计数卡数据(从 summary.namespaces 读 current/target)
  const kindCards = summary
    ? (["component", "page", "token", "reference"] as const).map((k) => ({
        key: k,
        label: KIND_LABELS[k] ?? k,
        current: summary.namespaces?.[k]?.current ?? 0,
        target: summary.namespaces?.[k]?.target ?? null,
        note: summary.namespaces?.[k]?.note ?? "",
      }))
    : [];

  return (
    <main className="mx-auto max-w-5xl px-6 py-16">
      <header className="mb-10">
        <p className="text-sm uppercase tracking-widest text-accent">
          DesignAdvisor · 资产库
        </p>
        <h1 className="mt-3 text-3xl font-semibold leading-tight">
          Phase 1 #1 · 资产库 MVP
        </h1>
        <p className="mt-3 max-w-2xl text-sm text-ink-50/70">
          消费后端 8 件 fake-load 资产(4 类各 2 件)· 字段对齐
          <code className="mx-1 rounded bg-white/5 px-1.5 py-0.5 text-xs">
            docs/02-设计资产元数据-schema
          </code>
          v0.1 · 命名空间预期对齐
          <code className="mx-1 rounded bg-white/5 px-1.5 py-0.5 text-xs">
            docs/04-可入库资产清单_v0.1
          </code>
          (组件 32 / 页面 19 / 令牌 ~73 / 参考开放)。
        </p>
        <p className="mt-3 text-xs text-ink-50/40">
          <Link href="/" className="text-accent hover:underline">
            ← 返回首页
          </Link>
          <span className="mx-2 text-ink-50/20">|</span>
          <Link href="/dp" className="text-accent hover:underline">
            24 条设计哲学 →
          </Link>
        </p>
      </header>

      {/* 4 类计数卡(命名空间进度,不随过滤项变化) */}
      {kindCards.length > 0 && (
        <section className="mb-8 grid grid-cols-2 gap-3 md:grid-cols-4">
          {kindCards.map((c) => (
            <div
              key={c.key}
              className="rounded-xl border border-white/10 bg-white/[0.02] p-4"
            >
              <p className="text-xs uppercase tracking-widest text-ink-50/40">
                {c.label}
              </p>
              <p className="mt-2 text-2xl font-semibold text-ink-50">
                {c.current}
                <span className="ml-1 text-sm font-normal text-ink-50/40">
                  / {c.target ?? "开放"}
                </span>
              </p>
              <p className="mt-1 text-[10px] text-ink-50/40">{c.note}</p>
            </div>
          ))}
        </section>
      )}

      {/* 过滤表单(GET · URL 状态可分享) */}
      <form
        action="/assets"
        method="get"
        className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center"
      >
        <select
          name="kind"
          defaultValue={kind}
          className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2.5 text-sm text-ink-50 focus:border-accent/60 focus:outline-none"
        >
          {KINDS.map((k) => (
            <option key={k.value} value={k.value}>
              {k.label}
            </option>
          ))}
        </select>
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
        <input
          type="text"
          name="category"
          defaultValue={category}
          placeholder="子分类(例如 button / auth / color)"
          className="flex-1 rounded-lg border border-white/10 bg-white/[0.03] px-4 py-2.5 text-sm text-ink-50 placeholder:text-ink-50/30 focus:border-accent/60 focus:outline-none"
        />
        <button
          type="submit"
          className="rounded-lg border border-accent/40 bg-accent/10 px-5 py-2.5 text-sm font-medium text-accent transition hover:bg-accent/20"
        >
          查询
        </button>
        {(kind || category || status) && (
          <Link
            href="/assets"
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
            {kind
              ? `类型:${KIND_LABELS[kind] ?? kind}`
              : category
                ? `子分类:${category}`
                : status
                  ? `状态:${STATUS_LABELS[status] ?? status}`
                  : "全部 8 件"}
          </p>
          <p className="text-xs text-ink-50/40">命中 {items.length} 件</p>
        </div>

        {items.length === 0 ? (
          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-10 text-center text-sm text-ink-50/50">
            没有命中结果。试试其他过滤条件,或
            <Link href="/assets" className="ml-1 text-accent hover:underline">
              清除筛选
            </Link>
            。
          </div>
        ) : (
          <ul className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {items.map((a) => (
              <li
                key={a.id}
                className="rounded-xl border border-white/10 bg-white/[0.02] p-4 transition hover:border-accent/60"
              >
                <div className="flex items-baseline justify-between gap-3">
                  <span className="font-mono text-xs text-accent">{a.id}</span>
                  <span className="rounded-full bg-white/5 px-2 py-0.5 text-[10px] uppercase tracking-wide text-ink-50/50">
                    {KIND_LABELS[a.kind] ?? a.kind} · v{a.version}
                  </span>
                </div>
                <p className="mt-2 text-sm text-ink-50/80">{a.purpose}</p>
                <div className="mt-3 flex flex-wrap items-center gap-1.5">
                  {a.tags.map((t) => (
                    <span
                      key={t}
                      className="rounded-md border border-white/10 bg-white/[0.03] px-1.5 py-0.5 text-[10px] text-ink-50/50"
                    >
                      #{t}
                    </span>
                  ))}
                </div>
                <div className="mt-3 flex items-center justify-between border-t border-white/5 pt-2 text-[10px] text-ink-50/40">
                  <span>
                    状态 · {STATUS_LABELS[a.status] ?? a.status}
                  </span>
                  <span>
                    代码引用 {a.code_ref_count} · Figma{" "}
                    {a.figma_synced ? "✓" : "待 OAuth"}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <footer className="mt-12 border-t border-white/10 pt-6 text-xs text-ink-50/40">
        <p>
          API:
          <code className="ml-1 rounded bg-white/5 px-1.5 py-0.5">
            /api/v1/assets
          </code>
          +
          <code className="ml-1 rounded bg-white/5 px-1.5 py-0.5">
            /api/v1/assets/summary
          </code>
          · 后端 v0.3(2026-09-01)· Web 消费 v0.4(2026-09-02)
        </p>
        <p className="mt-1">
          不做什么(留待后续):32+19+73 全量回填(需 docs/04 命名空间批量生成脚本)
          · Figma OAuth 真实入库 · 语义搜索(关键词 + 标签 + 视觉相似度)
        </p>
      </footer>
    </main>
  );
}
