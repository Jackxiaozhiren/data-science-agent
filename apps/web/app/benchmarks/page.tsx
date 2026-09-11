import { readFileSync, existsSync } from "fs";
import { join } from "path";
import { Gauge, FlaskConical } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/app/components/ui/card";
import { PageHeader } from "@/app/components/data/PageHeader";
import { StatCard } from "@/app/components/data/StatCard";
import { EmptyState } from "@/app/components/data/States";
import { CompareBarChart, DonutChart } from "@/app/components/ui/chart";
import { CopyButton } from "@/app/benchmarks/CopyButton";

function firstExisting(...segments: string[]): string | null {
  // process.cwd() is apps/web locally but the repo root in some deploys —
  // try both so frozen benchmark files resolve in either layout.
  const roots = [process.cwd(), join(process.cwd(), "..", "..")];
  for (const r of roots) {
    const p = join(r, ...segments);
    if (existsSync(p)) return p;
  }
  return null;
}

function benchStats(): { n: number; task_success_rate: unknown; evidence_coverage: unknown; sql_accuracy: unknown; unsupported_claim_rate: unknown; mean_latency_ms: unknown; by_category?: Record<string, { n: number; task_success: unknown }> } | null {
  try {
    const p = firstExisting("benchmarks", "baseline", "summary.json");
    if (!p) return null;
    return JSON.parse(readFileSync(p, "utf-8"));
  } catch {
    return null;
  }
}

function v2Stats(): { tasks: number; byCat: Record<string, number>; datasets: number } | null {
  try {
    const p = firstExisting("benchmarks", "v2", "catalog.json");
    if (!p) return null;
    const cat = JSON.parse(readFileSync(p, "utf-8")) as { tasks?: { category: string }[]; datasets?: number };
    const tasks = cat.tasks || [];
    const byCat: Record<string, number> = {};
    for (const t of tasks) byCat[t.category] = (byCat[t.category] || 0) + 1;
    return { tasks: tasks.length, byCat, datasets: cat.datasets || 30 };
  } catch {
    return null;
  }
}

function toPct(v: unknown): number | null {
  if (typeof v === "number") return v <= 1 ? v * 100 : v;
  if (typeof v === "string") {
    const n = parseFloat(v.replace("%", ""));
    if (Number.isNaN(n)) return null;
    return v.includes("%") ? n : n <= 1 ? n * 100 : n;
  }
  return null;
}

const RUNNER_V1 = "uv run dsa --limit 50 --out benchmarks/baseline";
const RUNNER_V2 = "uv run dsa --catalog benchmarks/v2/catalog.json --datasets benchmarks/v2/datasets --limit 100 --out /tmp/v2-bench";

export default function BenchmarksPage() {
  const base = benchStats();
  const v2 = v2Stats();

  const taskSuccess = base ? toPct(base.task_success_rate) : null;
  const evidence = base ? toPct(base.evidence_coverage) : null;
  const sqlAcc = base ? toPct(base.sql_accuracy) : null;
  const hasBars = taskSuccess != null || evidence != null || sqlAcc != null;
  const donut = v2 ? Object.entries(v2.byCat).map(([name, value]) => ({ name, value })) : [];
  const byCatBars = base?.by_category
    ? Object.entries(base.by_category)
        .map(([name, c]) => ({ name, success: toPct(c.task_success) ?? 0, n: c.n }))
        .filter((d) => d.n > 0)
    : [];

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Evaluation · Frozen vs research"
        title="Benchmarks"
        description="Frozen baseline (v1) vs V2 (100 tasks). Source: benchmarks/baseline/summary.json (seed 42, 20 datasets) and benchmarks/v2/catalog.json (30 datasets, 11 categories)."
        actions={<CopyButton text={RUNNER_V2} label="Copy runner" />}
      />

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm"><Gauge className="size-4 text-zinc-500" aria-hidden /> Baseline v1 (frozen)</CardTitle>
          </CardHeader>
          <CardContent>
            {base ? (
              <div className="grid grid-cols-2 gap-3">
                <StatCard label="Tasks" value={String(base.n)} />
                <StatCard label="Task success" value={taskSuccess != null ? `${taskSuccess.toFixed(0)}%` : String(base.task_success_rate)} accent="emerald" />
                <StatCard label="Evidence" value={evidence != null ? `${evidence.toFixed(0)}%` : String(base.evidence_coverage)} accent="emerald" />
                <StatCard label="Mean latency" value={`${String(base.mean_latency_ms)}ms`} hint={`SQL ${String(base.sql_accuracy)} · Unsupported ${String(base.unsupported_claim_rate)}`} />
              </div>
            ) : (
              <EmptyState
                title="Baseline not frozen yet"
                description="No summary.json found in this deployment."
                action={<CopyButton text={RUNNER_V1} label="Copy freeze command" />}
              />
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm"><FlaskConical className="size-4 text-zinc-500" aria-hidden /> V2 (research)</CardTitle>
            <CardDescription className="text-xs">100 tasks · 30 datasets · 11 categories</CardDescription>
          </CardHeader>
          <CardContent>
            {v2 ? (
              <div className="grid grid-cols-2 gap-3">
                <StatCard label="Tasks" value={String(v2.tasks)} />
                <StatCard label="Datasets" value={String(v2.datasets)} />
                <p className="col-span-2 break-words text-xs leading-5 text-zinc-500">
                  {Object.entries(v2.byCat).map(([k, n]) => `${k} ${n}`).join(" · ")}
                </p>
              </div>
            ) : (
              <EmptyState title="V2 catalog missing" description="benchmarks/v2/catalog.json was not found in this deployment." />
            )}
          </CardContent>
        </Card>
      </div>

      {hasBars ? (
        <CompareBarChart
          title="Accuracy comparison"
          description="Task success · evidence coverage · SQL accuracy (v1 frozen)"
          data={[
            { name: "Task success", v1: taskSuccess ?? 0 },
            { name: "Evidence", v1: evidence ?? 0 },
            { name: "SQL acc", v1: sqlAcc ?? 0 },
          ]}
          bars={[{ key: "v1", label: "Baseline v1 (%)", color: "#10b981" }]}
        />
      ) : (
        <EmptyState
          title="No benchmark numbers to chart"
          description="Freeze the baseline to unlock the comparison chart."
          action={<CopyButton text={RUNNER_V1} label="Copy freeze command" />}
        />
      )}

      {donut.length > 0 && (
        <DonutChart title="V2 category distribution" description={`${v2?.tasks} tasks across ${donut.length} categories`} data={donut} />
      )}

      {byCatBars.length > 0 && (
        <CompareBarChart
          title="v1 success by category"
          description={`${byCatBars.length} categories · task success rate (frozen baseline)`}
          data={byCatBars.map((d) => ({ name: d.name, success: Math.round(d.success * 10) / 10 }))}
          bars={[{ key: "success", label: "Task success (%)", color: "#3f3f46" }]}
        />
      )}

      <Card>
        <CardContent className="flex flex-wrap items-center justify-between gap-3 p-4 pt-4">
          <code className="min-w-0 flex-1 break-all font-mono text-xs text-zinc-600">{RUNNER_V2}</code>
          <CopyButton text={RUNNER_V2} label="Copy" />
        </CardContent>
      </Card>
    </div>
  );
}
