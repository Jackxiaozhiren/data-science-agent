import { readFileSync, existsSync } from "fs";
import { join } from "path";

function benchStats() {
  try {
    const p = join(process.cwd(), "benchmarks", "baseline", "summary.json");
    if (!existsSync(p)) return null;
    return JSON.parse(readFileSync(p, "utf-8"));
  } catch {
    return null;
  }
}

function v2Stats() {
  try {
    const p = join(process.cwd(), "benchmarks", "v2", "catalog.json");
    if (!existsSync(p)) return null;
    const cat = JSON.parse(readFileSync(p, "utf-8"));
    const tasks = cat.tasks || [];
    const byCat: Record<string, number> = {};
    for (const t of tasks) byCat[t.category] = (byCat[t.category] || 0) + 1;
    return { tasks: tasks.length, byCat, datasets: cat.datasets || 30 };
  } catch {
    return null;
  }
}

export default function BenchmarksPage() {
  const base = benchStats();
  const v2 = v2Stats();
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Benchmarks</h1>
      <p className="text-sm text-zinc-600">Frozen baseline (v1) vs V2 (100 tasks). Source: <code>benchmarks/baseline/summary.json</code> (seed 42, 20 datasets) and <code>benchmarks/v2/catalog.json</code> (30 datasets, 11 categories).</p>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded border bg-white p-4">
          <div className="text-sm font-medium">Baseline v1 (frozen)</div>
          {base ? (
            <div className="mt-2 text-sm">
              <div>Tasks: {base.n} · Task Success {base.task_success_rate} · Evidence {base.evidence_coverage}</div>
              <div className="text-xs text-zinc-500">SQL {base.sql_accuracy} · Unsupported {base.unsupported_claim_rate} · mean {base.mean_latency_ms}ms</div>
            </div>
          ) : (
            <div className="text-xs text-zinc-500">Not yet frozen — run <code>uv run dsa --limit 50 --out benchmarks/baseline</code></div>
          )}
        </div>
        <div className="rounded border bg-white p-4">
          <div className="text-sm font-medium">V2 (research)</div>
          {v2 ? (
            <div className="mt-2 text-sm">
              <div>Tasks: {v2.tasks} · Datasets: {v2.datasets}</div>
              <div className="text-xs text-zinc-500 break-all">{Object.entries(v2.byCat).map(([k, n]) => `${k} ${n}`).join(" · ")}</div>
            </div>
          ) : (
            <div className="text-xs text-zinc-500"><code>benchmarks/v2/catalog.json</code> missing</div>
          )}
        </div>
      </div>
      <div className="rounded border bg-white p-4 text-sm">
        Runner: <code>uv run dsa --catalog benchmarks/v2/catalog.json --datasets benchmarks/v2/datasets --limit 100 --out /tmp/v2-bench</code>
      </div>
    </div>
  );
}
