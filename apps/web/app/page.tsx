import { apiUrl } from "@/lib/api";

type AnalysisSummary = { id: string; status: string; user_query: string; created_at: string | null };

async function fetchRecent(): Promise<AnalysisSummary[]> {
  try {
    const res = await fetch(apiUrl("/api/v1/analysis/"), { cache: "no-store" });
    if (!res.ok) return [];
    const data = (await res.json()) as { analyses: AnalysisSummary[] };
    return data.analyses.slice(0, 6);
  } catch {
    return [];
  }
}

export default async function Home() {
  const recent = await fetchRecent();

  return (
    <div className="space-y-8">
      <section className="overflow-hidden rounded-2xl border bg-white p-8 sm:p-12">
        <div className="max-w-3xl">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-zinc-500">Verifiable AI data science</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl">The AI data scientist that shows its work.</h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-zinc-600">
            Upload a dataset and ask a question in natural language. DSA runs statistics, SQL, machine learning, and visualization — then preserves the evidence behind every supported finding.
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            <a href="/datasets" className="rounded-lg bg-zinc-900 px-5 py-3 text-sm font-medium text-white">Try with your data →</a>
            <a href="https://github.com/Jackxiaozhiren/data-science-agent" className="rounded-lg border px-5 py-3 text-sm font-medium" target="_blank" rel="noreferrer">View on GitHub ↗</a>
          </div>
          <p className="mt-3 text-xs text-zinc-500">Question → execution → evidence → claim → reproducible report</p>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <div className="rounded-xl border bg-white p-5">
          <div className="text-xs font-semibold uppercase tracking-wider text-zinc-400">01 · Ask</div>
          <h2 className="mt-2 font-semibold">Start with the business question</h2>
          <p className="mt-2 text-sm leading-6 text-zinc-600">Use a CSV, Parquet, JSON, or Excel file and describe what you actually want to learn.</p>
        </div>
        <div className="rounded-xl border bg-white p-5">
          <div className="text-xs font-semibold uppercase tracking-wider text-zinc-400">02 · Analyze</div>
          <h2 className="mt-2 font-semibold">Let tools do the computation</h2>
          <p className="mt-2 text-sm leading-6 text-zinc-600">DSA plans and executes data-science tools instead of inventing numerical results in prose.</p>
        </div>
        <div className="rounded-xl border bg-white p-5">
          <div className="text-xs font-semibold uppercase tracking-wider text-zinc-400">03 · Verify</div>
          <h2 className="mt-2 font-semibold">Inspect where each claim came from</h2>
          <p className="mt-2 text-sm leading-6 text-zinc-600">Review the agent trace, claim-level evidence, validation checks, and reproducible artifacts.</p>
        </div>
      </section>

      <section className="rounded-xl border bg-zinc-950 p-6 text-zinc-100">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-zinc-400">Why DSA</p>
        <div className="mt-4 grid gap-5 md:grid-cols-[1.15fr_0.85fr]">
          <div>
            <h2 className="text-2xl font-semibold">Most AI analysis tools give you an answer. DSA gives you the answer and the evidence behind it.</h2>
            <p className="mt-3 text-sm leading-6 text-zinc-400">That makes generated analysis easier to inspect, challenge, reproduce, and trust.</p>
          </div>
          <pre className="rounded-lg border border-zinc-800 bg-zinc-900 p-4 text-xs leading-6 text-zinc-300">{`Claim\n └── Evidence\n      └── Tool call\n           └── Computation\n                └── Dataset hash`}</pre>
        </div>
      </section>

      <section className="rounded-xl border bg-white p-5">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-zinc-400">Proof, not promises</p>
            <h2 className="mt-1 font-semibold">Recent analyses</h2>
          </div>
          <a href="/analysis" className="text-sm font-medium underline">Start analysis</a>
        </div>
        {recent.length === 0 ? (
          <div className="mt-4 rounded-lg bg-zinc-50 p-4">
            <p className="text-sm text-zinc-600">No analysis runs yet in this environment.</p>
            <a href="/datasets" className="mt-2 inline-block text-sm font-medium underline">Upload a dataset and create the first one →</a>
          </div>
        ) : (
          <ul className="mt-3 divide-y">
            {recent.map((r) => (
              <li key={r.id} className="flex items-center justify-between gap-4 py-3 text-sm">
                <span className="truncate">{r.user_query}</span>
                <a href={`/analysis/${r.id}`} className="shrink-0 rounded border px-2 py-1 text-xs font-medium">{r.status} →</a>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
