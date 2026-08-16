export default function ResearchPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Research</h1>
      <p className="text-sm text-zinc-600">RQ1–RQ5 · Ablation A–F · Bootstrap CI / McNemar / Wilcoxon · <code>research/paper/outline.md</code></p>
      <div className="rounded border bg-white p-4 text-sm">Results: <code>research/results/</code> (JSON/CSV/Parquet, git_commit + seed + prompt_version)</div>
    </div>
  );
}
