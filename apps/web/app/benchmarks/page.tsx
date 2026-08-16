export default function BenchmarksPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Benchmarks</h1>
      <p className="text-sm text-zinc-600">Leaderboard: Task Success, Statistical Accuracy, Evidence Coverage, Reproducibility, Latency, Token Cost. Sources: <code>benchmarks/baseline/summary.json</code> (frozen) vs <code>benchmarks/v2/catalog.json</code> (100 tasks, 30 datasets).</p>
      <div className="rounded border bg-white p-4 text-sm">Baseline: <code>docs/v2/Baseline Report.md</code> · API: <code>GET /health /ready /version /metrics</code> · Runner: <code>uv run dsa --catalog benchmarks/v2/catalog.json --datasets benchmarks/v2/datasets --limit 50 --out /tmp/v2-bench</code></div>
    </div>
  );
}
