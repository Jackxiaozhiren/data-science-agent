"use client";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";

type Ds = { id: string; filename: string };

function AnalysisWorkspace() {
  const sp = useSearchParams();
  const router = useRouter();
  const initialDs = sp.get("dataset") || "";
  const [datasets, setDatasets] = useState<Ds[]>([]);
  const [datasetId, setDatasetId] = useState(initialDs);
  const [query, setQuery] = useState("Analyze correlation, test group differences, and visualize key findings.");
  const [err, setErr] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    fetch("http://localhost:8000/api/v1/datasets/").then((r) => r.json()).then((d: { datasets: Ds[] }) => setDatasets(d.datasets)).catch(() => {});
  }, []);

  async function run() {
    setErr(null);
    if (!datasetId || !query.trim()) { setErr("Select dataset and enter a question."); return; }
    setRunning(true);
    const res = await fetch("http://localhost:8000/api/v1/analysis/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ dataset_id: datasetId, user_query: query }) });
    const data = await res.json().catch(() => ({}));
    setRunning(false);
    if (!res.ok) { setErr(data.detail || JSON.stringify(data)); return; }
    router.push(`/analysis/${data.id}`);
  }

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold">Analysis Workspace</h1>
      <div className="rounded border bg-white p-4 space-y-3">
        <label className="block text-sm">Dataset</label>
        <select value={datasetId} onChange={(e) => setDatasetId(e.target.value)} className="w-full rounded border px-2 py-2 text-sm">
          <option value="">— select —</option>
          {datasets.map((d) => <option key={d.id} value={d.id}>{d.filename} ({d.id.slice(0, 8)})</option>)}
        </select>
        <label className="block text-sm">Natural language question</label>
        <textarea value={query} onChange={(e) => setQuery(e.target.value)} rows={4} className="w-full rounded border px-2 py-2 text-sm" placeholder="e.g. Analyze why revenue declined and forecast next period" />
        <button onClick={run} disabled={running} className="rounded bg-zinc-900 px-4 py-2 text-sm text-white disabled:opacity-50">{running ? "Running…" : "Run analysis"}</button>
        {err && <p className="text-sm text-red-600">{err}</p>}
      </div>
      <p className="text-xs text-zinc-500">Evidence Before Claim · Analysis runs synchronously in MVP; trace appears after completion. Watch GET /api/v1/analysis/{"{id}"}/events for SSE.</p>
    </div>
  );
}

export default function AnalysisPage() {
  return (
    <Suspense fallback={<div className="text-sm text-zinc-500">Loading…</div>}>
      <AnalysisWorkspace />
    </Suspense>
  );
}
