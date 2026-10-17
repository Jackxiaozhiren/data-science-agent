import { Gauge, FlaskConical } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/app/components/ui/card";
import { PageHeader } from "@/app/components/data/PageHeader";
import { StatCard } from "@/app/components/data/StatCard";
import { EmptyState, ErrorState } from "@/app/components/data/States";
import { CompareBarChart, DonutChart } from "@/app/components/ui/chart";
import { CopyButton } from "@/app/benchmarks/CopyButton";
import { apiUrl, classifyResponse, FAILURE_PRESENTATION, type ApiFailure } from "@/lib/api";
import { serverFetch } from "@/lib/serverApi";

type Baseline = {
  n: number;
  task_success_rate: unknown;
  evidence_coverage: unknown;
  sql_accuracy: unknown;
  unsupported_claim_rate: unknown;
  mean_latency_ms: unknown;
  by_category?: Record<string, { n: number; task_success: unknown }>;
};

type Catalog = { tasks: number; by_category: Record<string, number>; datasets: number | null };

// The page used to open these files with readFileSync, which the web image does not carry
// (docker/Dockerfile.web copies only apps/web) — so a container rendered the empty state and a platform
// build froze the numbers at build time while presenting them as current (audit §168).
type Fetch<T> = { ok: true; value: T } | { ok: false; failure: ApiFailure };

async function getJson<T>(path: string): Promise<Fetch<T>> {
  try {
    const res = await serverFetch(path, { cache: "no-store" });
    const failure = classifyResponse(res);
    if (failure) return { ok: false, failure };
    return { ok: true, value: (await res.json()) as T };
  } catch {
    return { ok: false, failure: "transport" };
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

export default async function BenchmarksPage() {
  const [baseline, catalog] = await Promise.all([
    getJson<Baseline>("/api/v1/benchmarks/baseline"),
    getJson<Catalog>("/api/v1/benchmarks/catalog"),
  ]);
  const base = baseline.ok ? baseline.value : null;
  const v2 = catalog.ok ? catalog.value : null;
  const baselineFailure = baseline.ok ? null : baseline.failure;
  const catalogFailure = catalog.ok ? null : catalog.failure;

  const taskSuccess = base ? toPct(base.task_success_rate) : null;
  const evidence = base ? toPct(base.evidence_coverage) : null;
  const sqlAcc = base ? toPct(base.sql_accuracy) : null;
  const hasBars = taskSuccess != null || evidence != null || sqlAcc != null;
  const donut = v2 ? Object.entries(v2.by_category).map(([name, value]) => ({ name, value })) : [];
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
            ) : baselineFailure === "notFound" ? (
              <EmptyState
                title="Baseline not frozen yet"
                description="The API answered 404: benchmarks/baseline/summary.json is not present in this deployment."
                action={<CopyButton text={RUNNER_V1} label="Copy freeze command" />}
              />
            ) : (
              <ErrorState
                message={baselineFailure ? FAILURE_PRESENTATION[baselineFailure] : "The API returned no baseline."}
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
                  {Object.entries(v2.by_category).map(([k, n]) => `${k} ${n}`).join(" · ")}
                </p>
              </div>
            ) : catalogFailure === "notFound" ? (
              <EmptyState title="V2 catalog missing" description="The API answered 404: benchmarks/v2/catalog.json is not present in this deployment." />
            ) : (
              <ErrorState message={catalogFailure ? FAILURE_PRESENTATION[catalogFailure] : "The API returned no catalog."} />
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
      ) : baselineFailure === null ? (
        <EmptyState
          title="No benchmark numbers to chart"
          description="Freeze the baseline to unlock the comparison chart."
          action={<CopyButton text={RUNNER_V1} label="Copy freeze command" />}
        />
      ) : null}

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
