import Link from "next/link";

const modules = [
  {
    key: "assets",
    title: "设计资产库",
    desc: "组件 / 页面 / 设计令牌 / 参考,统一元数据,可语义检索",
  },
  {
    key: "tokens",
    title: "设计令牌同步",
    desc: "颜色 / 字体 / 间距 / 阴影,与 Figma + 前端双向同步,偏移告警",
  },
  {
    key: "review",
    title: "设计评审协作",
    desc: "上传 → @评审人 → 结构化意见 → 决策可追溯,版本对比可视化",
  },
  {
    key: "ai-draft",
    title: "AI 草稿生成器",
    desc: "基于现有规范 + 需求,生成 Figma JSON / HTML+CSS 草稿(只做草稿)",
  },
  {
    key: "inspiration",
    title: "设计灵感库",
    desc: "一键收藏外部参考,内部共享,积累团队审美资产",
  },
];

export default function HomePage() {
  return (
    <main className="mx-auto max-w-5xl px-6 py-16">
      <header className="mb-12">
        <p className="text-sm uppercase tracking-widest text-accent">
          DesignAdvisor · v0.3
        </p>
        <h1 className="mt-3 text-4xl font-semibold leading-tight">
          27-设计-Design Level
        </h1>
        <p className="mt-4 max-w-2xl text-ink-50/70">
          把设计资产管理从文件夹 / Sketch 库 / Figma 链接散落状态,整合为可被 AI
          调用、可被设计师搜索、可被产品研发引用的统一设计中枢。
        </p>
      </header>

      <section className="mb-10 rounded-2xl border border-accent/30 bg-accent/5 p-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs uppercase tracking-widest text-accent">
              知识库 · Phase 0 #4 前置
            </p>
            <h2 className="mt-2 text-xl font-medium">24 条设计哲学</h2>
            <p className="mt-1 text-sm text-ink-50/60">
              从 _DesignLib 10 章盘点提炼 · 飞书 bot 查规范的后端数据,Web 端先跑通
            </p>
          </div>
          <Link
            href="/dp"
            className="rounded-lg border border-accent/40 bg-accent/20 px-5 py-2.5 text-sm font-medium text-accent transition hover:bg-accent/30"
          >
            浏览 24 条 →
          </Link>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {modules.map((m) => (
          <article
            key={m.key}
            className="rounded-xl border border-white/10 bg-white/[0.02] p-5 transition hover:border-accent/60"
          >
            <h2 className="text-lg font-medium">{m.title}</h2>
            <p className="mt-2 text-sm text-ink-50/60">{m.desc}</p>
          </article>
        ))}
      </section>

      <footer className="mt-16 border-t border-white/10 pt-6 text-xs text-ink-50/40">
        <p>
          工程状态:v0.1 · Next.js 14 + Tailwind 骨架就位 · FastAPI 健康检查
          <code className="ml-1 rounded bg-white/5 px-1.5 py-0.5">/healthz</code>
        </p>
        <p className="mt-1">
          详细计划见
          <Link
            href="/项目开发计划.md"
            className="ml-1 text-accent underline-offset-4 hover:underline"
          >
            项目开发计划.md
          </Link>
        </p>
      </footer>
    </main>
  );
}
