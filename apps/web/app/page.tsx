type AnalysisSummary = { id: string; status: string; user_query: string; created_at: string | null };

async function fetchRecent(): Promise<AnalysisSummary[]> {
  try {
    const res = await fetch("http://localhost:8000/api/v1/analysis/", { cache: "no-store" });
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
    <div className="space-y-6">
      <div className="rounded-xl border bg-white p-6">
        <h1 className="text-xl font-semibold">An Evidence-Grounded Autonomous Data Science System</h1>
        <p className="mt-2 text-sm text-zinc-600">Upload a dataset, ask in natural language, get a reproducible analysis with evidence, charts, and a report.</p>
        <div className="mt-4 flex gap-2">
          <a href="/datasets" className="rounded bg-zinc-900 px-3 py-2 text-sm text-white">Upload dataset</a>
          <a href="/analysis" className="rounded border px-3 py-2 text-sm">New analysis</a>
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-4">
        <div className="rounded border bg-white p-3"><div className="text-xs text-zinc-500">Task Success</div><div className="text-lg font-semibold">—</div><div className="text-xs text-zinc-400">from benchmarks/baseline</div></div>
        <div className="rounded border bg-white p-3"><div className="text-xs text-zinc-500">Evidence Coverage</div><div className="text-lg font-semibold">—</div></div>
        <div className="rounded border bg-white p-3"><div className="text-xs text-zinc-500">Reproducibility</div><div className="text-lg font-semibold">L0–L5</div></div>
        <div className="rounded border bg-white p-3"><div className="text-xs text-zinc-500">Avg Latency</div><div className="text-lg font-semibold">—</div></div>
      </div>
      <div className="rounded-xl border bg-white p-4">
        <h2 className="font-medium">Recent analyses</h2>
        {recent.length === 0 ? (
          <p className="mt-2 text-sm text-zinc-500">No analyses yet. Upload a dataset on /datasets.</p>
        ) : (
          <ul className="mt-2 divide-y">
            {recent.map((r) => (
              <li key={r.id} className="flex items-center justify-between py-2 text-sm">
                <span className="truncate pr-4">{r.user_query}</span>
                <a href={`/analysis/${r.id}`} className="shrink-0 rounded border px-2 py-1">{r.status}</a>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
