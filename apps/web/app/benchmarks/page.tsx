import { Gauge, FlaskConical } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/app/components/ui/card";
import { PageHeader } from "@/app/components/data/PageHeader";
import { StatCard } from "@/app/components/data/StatCard";
import { EmptyState, ErrorState } from "@/app/components/data/States";
import { CompareBarChart, DonutChart } from "@/app/components/ui/chart";
import { CopyButton } from "@/app/benchmarks/CopyButton";
import { apiUrl, classifyResponse, failurePresentation, type ApiFailure } from "@/lib/api";
import { serverFetch, serverLocale } from "@/lib/serverApi";
import { t } from "@/lib/locale";

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
  const locale = await serverLocale();
  const shared = failurePresentation(locale);
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
        eyebrow={t(locale, "bench.eyebrow")}
        title={t(locale, "bench.title")}
        description={t(locale, "bench.provenance")}
        actions={<CopyButton text={RUNNER_V2} label={t(locale, "bench.copyRunner")} />}
      />

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm"><Gauge className="size-4 text-zinc-500" aria-hidden /> {t(locale, "bench.baselineTitle")}</CardTitle>
          </CardHeader>
          <CardContent>
            {base ? (
              <div className="grid grid-cols-2 gap-3">
                <StatCard label={t(locale, "bench.tasks")} value={String(base.n)} />
                <StatCard label={t(locale, "bench.taskSuccess")} value={taskSuccess != null ? `${taskSuccess.toFixed(0)}%` : String(base.task_success_rate)} accent="emerald" />
                <StatCard label={t(locale, "bench.evidenceLabel")} value={evidence != null ? `${evidence.toFixed(0)}%` : String(base.evidence_coverage)} accent="emerald" />
                <StatCard
                  label={t(locale, "bench.meanLatency")}
                  value={`${String(base.mean_latency_ms)}ms`}
                  hint={t(locale, "bench.latencyHint")
                    .replace("{sql}", String(base.sql_accuracy))
                    .replace("{unsupported}", String(base.unsupported_claim_rate))}
                />
              </div>
            ) : baselineFailure === "notFound" ? (
              <EmptyState
                title={t(locale, "bench.notFrozen")}
                description={t(locale, "bench.notFrozenBody")}
                action={<CopyButton text={RUNNER_V1} label={t(locale, "bench.copyFreeze")} />}
              />
            ) : (
              <ErrorState
                message={baselineFailure ? shared[baselineFailure] : t(locale, "bench.noBaseline")}
              />
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm"><FlaskConical className="size-4 text-zinc-500" aria-hidden /> {t(locale, "bench.v2Title")}</CardTitle>
            <CardDescription className="text-xs">{t(locale, "bench.v2Counts")}</CardDescription>
          </CardHeader>
          <CardContent>
            {v2 ? (
              <div className="grid grid-cols-2 gap-3">
                <StatCard label={t(locale, "bench.tasks")} value={String(v2.tasks)} />
                <StatCard label={t(locale, "bench.datasets")} value={String(v2.datasets)} />
                <p className="col-span-2 break-words text-xs leading-5 text-zinc-500">
                  {Object.entries(v2.by_category).map(([k, n]) => `${k} ${n}`).join(" · ")}
                </p>
              </div>
            ) : catalogFailure === "notFound" ? (
              <EmptyState title={t(locale, "bench.catalogMissing")} description={t(locale, "bench.catalogBody")} />
            ) : (
              <ErrorState message={catalogFailure ? shared[catalogFailure] : t(locale, "bench.noCatalog")} />
            )}
          </CardContent>
        </Card>
      </div>

      {hasBars ? (
        <CompareBarChart
          title={t(locale, "bench.accuracyTitle")}
          description={t(locale, "bench.metrics")}
          data={[
            { name: t(locale, "bench.taskSuccess"), v1: taskSuccess ?? 0 },
            { name: t(locale, "bench.evidenceLabel"), v1: evidence ?? 0 },
            { name: t(locale, "bench.sqlAcc"), v1: sqlAcc ?? 0 },
          ]}
          bars={[{ key: "v1", label: t(locale, "bench.baselineBar"), color: "#10b981" }]}
        />
      ) : baselineFailure === null ? (
        <EmptyState
          title={t(locale, "bench.noNumbers")}
          description={t(locale, "bench.freezeHint")}
          action={<CopyButton text={RUNNER_V1} label={t(locale, "bench.copyFreeze")} />}
        />
      ) : null}

      {donut.length > 0 && (
        <DonutChart
          title={t(locale, "bench.v2Distribution")}
          description={t(locale, "bench.donutDesc")
            .replace("{tasks}", String(v2?.tasks))
            .replace("{categories}", String(donut.length))}
          data={donut}
        />
      )}

      {byCatBars.length > 0 && (
        <CompareBarChart
          title={t(locale, "bench.v1ByCategory")}
          description={t(locale, "bench.byCatDesc").replace("{count}", String(byCatBars.length))}
          data={byCatBars.map((d) => ({ name: d.name, success: Math.round(d.success * 10) / 10 }))}
          bars={[{ key: "success", label: t(locale, "bench.taskSuccessBar"), color: "#3f3f46" }]}
        />
      )}

      <Card>
        <CardContent className="flex flex-wrap items-center justify-between gap-3 p-4 pt-4">
          <code className="min-w-0 flex-1 break-all font-mono text-xs text-zinc-600">{RUNNER_V2}</code>
          <CopyButton text={RUNNER_V2} label={t(locale, "copy.plain")} />
        </CardContent>
      </Card>
    </div>
  );
}
