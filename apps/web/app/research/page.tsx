import { existsSync, readdirSync } from "fs";
import { join } from "path";
import Link from "next/link";
import { FlaskConical, Sigma, Layers } from "lucide-react";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/app/components/ui/card";
import { PageHeader } from "@/app/components/data/PageHeader";
import { StatCard } from "@/app/components/data/StatCard";
import { EmptyState } from "@/app/components/data/States";
import { DataTable } from "@/app/components/data/DataTable";

function experiments(): string[] {
  try {
    const dir = join(process.cwd(), "research", "results");
    if (!existsSync(dir)) return [];
    return readdirSync(dir).filter((f) => f.startsWith("ablation_")).slice(0, 10);
  } catch {
    return [];
  }
}

const RUNNER = "uv run python research/experiments/run_ablation.py --limit 20 --out research/results";

export default function ResearchPage() {
  const exps = experiments();
  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Research · Step 3"
        title="Research"
        description="W2–W10 closure: EvaluationResultV2 (10-dim + 6-level), Benchmark v2 (100 tasks), Ablation A–F, Significance (bootstrap CI / McNemar / Wilcoxon), Reproducibility L0–L5, Failure F01–F15. See docs/benchmark.md and research/paper/V2_paper_draft.md."
        actions={
          <Link href="/analysis"><Button size="sm">Back to Analysis</Button></Link>
        }
      />
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="Ablations" value="A–F" hint="LLM-only → Full" icon={FlaskConical} />
        <StatCard label="Eval dims" value="10-dim" hint="+ 6-level breakdown" icon={Layers} />
        <StatCard label="Significance" value="CI / McNemar" hint="+ Wilcoxon" icon={Sigma} />
      </div>
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Recent experiments ({exps.length})</CardTitle>
          <CardDescription className="text-xs">Ablation result files under research/results.</CardDescription>
        </CardHeader>
        <CardContent>
          {exps.length ? (
            <DataTable<{ name: string } & Record<string, unknown>>
              caption="Recent ablation experiments"
              keyOf={(r) => r.name}
              rows={exps.map((name) => ({ name }))}
              columns={[{ key: "name", header: "File", render: (r) => <code className="font-mono text-xs">{r.name}</code> }]}
            />
          ) : (
            <EmptyState
              title="No results yet"
              description={`Run the ablation runner to produce the first result files: ${RUNNER}`}
            />
          )}
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-4 pt-4 text-xs leading-5 text-zinc-500">
          Runner provenance: ablation configs at <code className="font-mono">research/experiments/ablation_matrix.py</code> (A LLM-only → F Full). Significance: <code className="font-mono">packages/evaluation/src/dsa_evaluation/significance.py</code>.
        </CardContent>
      </Card>
    </div>
  );
}
