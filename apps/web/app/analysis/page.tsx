"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { API_BASE_URL, apiUrl } from "@/lib/api";

type Ds = { id: string; filename: string };

function AnalysisWorkspace() {
  const sp = useSearchParams();
  const router = useRouter();
  const initialDs = sp.get("dataset") || "";
  const [datasets, setDatasets] = useState<Ds[]>([]);
  const [datasetId, setDatasetId] = useState(initialDs);
  const [query, setQuery] = useState("Which factors explain the outcome, and are the effects statistically significant?");
  const [err, setErr] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    fetch(apiUrl("/api/v1/datasets/"))
      .then(async (r) => {
        if (!r.ok) throw new Error(await r.text());
        return r.json() as Promise<{ datasets: Ds[] }>;
      })
      .then((d) => setDatasets(d.datasets))
      .catch((e) => setErr(`Could not reach the DSA API at ${API_BASE_URL}. ${String(e)}`));
  }, []);

  async function run() {
    setErr(null);
    if (!datasetId || !query.trim()) {
      setErr("Select a dataset and enter a question.");
      return;
    }

    setRunning(true);
    try {
      const res = await fetch(apiUrl("/api/v1/analysis/"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dataset_id: datasetId, user_query: query }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setErr(data.detail || JSON.stringify(data));
        return;
      }
      router.push(`/analysis/${data.id}`);
    } catch (e) {
      setErr(`Analysis could not start because the DSA API at ${API_BASE_URL} is unavailable. ${String(e)}`);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <p className="text-xs font-medium uppercase tracking-[0.18em] text-zinc-500">Step 2</p>
        <h1 className="text-lg font-semibold">Ask a real data-science question</h1>
        <p className="mt-1 text-sm text-zinc-600">DSA will plan the analysis, execute tools, build evidence, and preserve the trace.</p>
      </div>

      <div className="space-y-3 rounded border bg-white p-4">
        <label className="block text-sm font-medium">Dataset</label>
        <select
          value={datasetId}
          onChange={(e) => setDatasetId(e.target.value)}
          className="w-full rounded border px-2 py-2 text-sm"
        >
          <option value="">— select —</option>
          {datasets.map((d) => (
            <option key={d.id} value={d.id}>{d.filename} ({d.id.slice(0, 8)})</option>
          ))}
        </select>

        <label className="block text-sm font-medium">Natural-language question</label>
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          rows={4}
          className="w-full rounded border px-2 py-2 text-sm"
          placeholder="e.g. What is driving churn, and which findings are statistically supported?"
        />
        <div className="flex flex-wrap gap-2 text-xs">
          {[
            "What is driving the target, and which effects are statistically significant?",
            "Compare the main groups and explain the strongest differences.",
            "Find the most important patterns, limitations, and evidence behind them.",
          ].map((example) => (
            <button
              key={example}
              type="button"
              onClick={() => setQuery(example)}
              className="rounded-full border bg-zinc-50 px-3 py-1 text-zinc-600 hover:bg-zinc-100"
            >
              {example}
            </button>
          ))}
        </div>

        <button
          onClick={run}
          disabled={running}
          className="rounded bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {running ? "Running analysis…" : "Run analysis →"}
        </button>
        {err && <p className="text-sm text-red-600">{err}</p>}
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded border bg-white p-3 text-sm"><strong>1. Execute</strong><p className="mt-1 text-xs text-zinc-500">SQL, statistics, ML, and visualization tools.</p></div>
        <div className="rounded border bg-white p-3 text-sm"><strong>2. Verify</strong><p className="mt-1 text-xs text-zinc-500">Claims link back to evidence and tool calls.</p></div>
        <div className="rounded border bg-white p-3 text-sm"><strong>3. Reproduce</strong><p className="mt-1 text-xs text-zinc-500">Inspect the trace and generated artifacts.</p></div>
      </div>
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
