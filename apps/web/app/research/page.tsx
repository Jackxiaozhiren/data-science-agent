import { existsSync, readFileSync, readdirSync } from "fs";
import { join } from "path";

function experiments() {
  try {
    const dir = join(process.cwd(), "research", "results");
    if (!existsSync(dir)) return [];
    return readdirSync(dir).filter((f) => f.startsWith("ablation_")).slice(0, 10);
  } catch {
    return [];
  }
}

export default function ResearchPage() {
  const exps = experiments();
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Research</h1>
      <p className="text-sm text-zinc-600">W2–W10 closure: EvaluationResultV2 (10-dim + 6-level), Benchmark v2 (100 tasks), Ablation A–F, Significance (bootstrap CI / McNemar / Wilcoxon), Reproducibility L0–L5, Failure F01–F15. See <code>docs/benchmark.md</code> and <code>research/paper/V2_paper_draft.md</code>.</p>
      <div className="rounded border bg-white p-4">
        <div className="text-sm font-medium">Recent experiments</div>
        {exps.length ? (
          <ul className="mt-2 list-disc pl-5 text-xs">
            {exps.map((f) => (
              <li key={f}><code>{f}</code></li>
            ))}
          </ul>
        ) : (
          <div className="text-xs text-zinc-500">No results yet — run <code>uv run python research/experiments/run_ablation.py --limit 20 --out research/results</code></div>
        )}
      </div>
      <div className="rounded border bg-white p-4 text-xs">
        Runner provenance: ablation configs at <code>research/experiments/ablation_matrix.py</code> (A LLM-only → F Full). Significance: <code>packages/evaluation/src/dsa_evaluation/significance.py</code>.
      </div>
    </div>
  );
}
