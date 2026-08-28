import Link from "next/link";

type DesignPrinciple = {
  id: string;
  title: string;
  category: string;
  source: string;
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

// 24 条 DP 分类(从 api/main.py 镜像过来,前端做下拉用,避免初始空 query 时的全量请求分类选择歧义)
const CATEGORIES = [
  { value: "", label: "全部分类" },
  { value: "A·功能形式", label: "A · 功能 / 形式" },
  { value: "B·用户体验", label: "B · 用户体验" },
  { value: "C·逻辑推理", label: "C · 逻辑 / 推理" },
  { value: "D·思想文化", label: "D · 思想 / 文化" },
  { value: "E·实践评审", label: "E · 实践 / 评审" },
];

async function fetchDP(opts: {
  q?: string;
  category?: string;
}): Promise<DesignPrinciple[]> {
  // SSR 阶段直接拼后端绝对 URL,不走 /api/be/* rewrite(rewrite 在客户端 fetch 才有意义)
  // 关键词搜索优先(q 非空时打 /search,否则按 category 过滤 /api/v1/dp)
  const params = new URLSearchParams();
  let path = "/api/v1/dp";
  if (opts.q && opts.q.trim()) {
    path = "/api/v1/dp/search";
    params.set("q", opts.q.trim());
  } else if (opts.category) {
    params.set("category", opts.category);
  }
  const qs = params.toString();
  const url = `${API_BASE.replace(/\/$/, "")}${path}${qs ? `?${qs}` : ""}`;

  try {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) {
      console.error(`[dp/page] fetch ${url} -> ${res.status}`);
      return [];
    }
    return (await res.json()) as DesignPrinciple[];
  } catch (err) {
    console.error(`[dp/page] fetch ${url} failed:`, err);
    return [];
  }
}

export default async function DPPage({
  searchParams,
}: {
  searchParams: { q?: string; category?: string };
}) {
  const q = searchParams.q ?? "";
  const category = searchParams.category ?? "";
  const items = await fetchDP({ q, category });

  return (
    <main className="mx-auto max-w-5xl px-6 py-16">
      <header className="mb-10">
        <p className="text-sm uppercase tracking-widest text-accent">
          DesignAdvisor · 知识库
        </p>
        <h1 className="mt-3 text-3xl font-semibold leading-tight">
          24 条设计哲学
        </h1>
        <p className="mt-3 max-w-2xl text-sm text-ink-50/70">
          从 _DesignLib 10 章盘点提炼 · 数据源 docs/03- 设计哲学清单 v0.1 ·
          Phase 0 #4 飞书 bot 查规范的后端数据已在 Web 端先跑通。
        </p>
        <p className="mt-3 text-xs text-ink-50/40">
          <Link href="/" className="text-accent hover:underline">
            ← 返回首页
          </Link>
        </p>
      </header>

      {/* 搜索 + 分类表单(GET,纯 URL 状态,刷新可分享) */}
      <form
        action="/dp"
        method="get"
        className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-center"
      >
        <input
          type="text"
          name="q"
          defaultValue={q}
          placeholder="搜索关键词,例如 简约 / 用户体验 / DP-01"
          className="flex-1 rounded-lg border border-white/10 bg-white/[0.03] px-4 py-2.5 text-sm text-ink-50 placeholder:text-ink-50/30 focus:border-accent/60 focus:outline-none"
        />
        <select
          name="category"
          defaultValue={category}
          className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2.5 text-sm text-ink-50 focus:border-accent/60 focus:outline-none"
        >
          {CATEGORIES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
        <button
          type="submit"
          className="rounded-lg border border-accent/40 bg-accent/10 px-5 py-2.5 text-sm font-medium text-accent transition hover:bg-accent/20"
        >
          查询
        </button>
        {(q || category) && (
          <Link
            href="/dp"
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
            {q ? `搜索:"${q}"` : category ? `分类:${category}` : "全部 24 条"}
          </p>
          <p className="text-xs text-ink-50/40">命中 {items.length} 条</p>
        </div>

        {items.length === 0 ? (
          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-10 text-center text-sm text-ink-50/50">
            没有命中结果。试试其他关键词,或
            <Link href="/dp" className="ml-1 text-accent hover:underline">
              清除筛选
            </Link>
            。
          </div>
        ) : (
          <ul className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {items.map((dp) => (
              <li
                key={dp.id}
                className="rounded-xl border border-white/10 bg-white/[0.02] p-4 transition hover:border-accent/60"
              >
                <div className="flex items-baseline justify-between gap-3">
                  <span className="font-mono text-xs text-accent">{dp.id}</span>
                  <span className="rounded-full bg-white/5 px-2 py-0.5 text-[10px] uppercase tracking-wide text-ink-50/50">
                    {dp.category}
                  </span>
                </div>
                <h3 className="mt-2 text-base font-medium text-ink-50">
                  {dp.title}
                </h3>
                <p className="mt-2 text-xs text-ink-50/40">
                  来源章节:{dp.source}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>

      <footer className="mt-12 border-t border-white/10 pt-6 text-xs text-ink-50/40">
        <p>
          API:{q ? "/api/v1/dp/search" : "/api/v1/dp"}
          {q ? `?q=${encodeURIComponent(q)}` : category ? `?category=${encodeURIComponent(category)}` : ""} ·
          数据后端 v0.2(2026-08-28)· Web 消费 v0.3(2026-08-29)
        </p>
      </footer>
    </main>
  );
}
