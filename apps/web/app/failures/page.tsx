import Link from "next/link";
import { TriangleAlert } from "lucide-react";
import { apiUrl, classifyResponse, failurePresentation, type ApiFailure } from "@/lib/api";
import { serverFetch, serverLocale } from "@/lib/serverApi";
import { t, type Locale } from "@/lib/locale";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/app/components/ui/card";
import { Badge } from "@/app/components/ui/badge";
import { PageHeader } from "@/app/components/data/PageHeader";
import { StatCard } from "@/app/components/data/StatCard";
import { EmptyState, ErrorState } from "@/app/components/data/States";

const groups = [
  { titleKey: "failures.planning", bodyKey: "failures.f01", v: "outline" as const },
  { titleKey: "failures.execution", bodyKey: "failures.f06", v: "secondary" as const },
  { titleKey: "failures.evidence", bodyKey: "failures.f11", v: "warning" as const },
];

type ToolCall = { call_id: string; tool: string; status: string; error?: string | null };

type FailureStats = {
  failure: ApiFailure | null;
  runsScanned: number;
  failedCalls: number;
  byTool: { tool: string; count: number; runs: number; sample: string }[];
};

// Inherits the shared wording, and keeps this page's own line for the transport case: the taxonomy
// cards below are static, so "reference only" is what a reader is actually left with.
function failuresMessages(locale: Locale): Record<ApiFailure, string> {
  return { ...failurePresentation(locale), transport: t(locale, "failures.transport") };
}

async function fetchFailureStats(): Promise<FailureStats> {
  const empty: FailureStats = { failure: null, runsScanned: 0, failedCalls: 0, byTool: [] };
  try {
    const listRes = await serverFetch("/api/v1/analysis/", { cache: "no-store" });
    const listFailure = classifyResponse(listRes);
    if (listFailure) return { ...empty, failure: listFailure };
    const ids = ((await listRes.json()) as { analyses: { id: string }[] }).analyses.map((a) => a.id);
    const agg = new Map<string, { count: number; runs: Set<string>; sample: string }>();
    let failedCalls = 0;
    await Promise.all(
      ids.map(async (id) => {
        try {
          const r = await serverFetch(`/api/v1/analysis/${id}/artifacts`, { cache: "no-store" });
          if (!r.ok) return;
          const d = (await r.json()) as { tool_calls?: ToolCall[] };
          for (const tc of d.tool_calls ?? []) {
            if (tc.status === "ok") continue;
            failedCalls += 1;
            const e = agg.get(tc.tool) ?? { count: 0, runs: new Set<string>(), sample: "" };
            e.count += 1;
            e.runs.add(id);
            if (!e.sample && tc.error) {
              e.sample = String(tc.error).replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim().slice(0, 160);
            }
            agg.set(tc.tool, e);
          }
        } catch {
          // One unreadable run must not sink the whole page.
        }
      })
    );
    const byTool = [...agg.entries()]
      .map(([tool, v]) => ({ tool, count: v.count, runs: v.runs.size, sample: v.sample || "—" }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 8);
    return { failure: null, runsScanned: ids.length, failedCalls, byTool };
  } catch {
    return { ...empty, failure: "transport" };
  }
}

export default async function FailuresPage() {
  const locale = await serverLocale();
  const messages = failuresMessages(locale);
  const stats = await fetchFailureStats();
  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow={t(locale, "failures.eyebrow")}
        title={t(locale, "failures.title")}
        description={t(locale, "failures.descBody").replace("{n}", String(stats.runsScanned))}
        actions={
          <Link href="/analysis"><Button size="sm">{t(locale, "common.backToAnalysis")}</Button></Link>
        }
      />
      {stats.failure && <ErrorState message={messages[stats.failure]} />}
      <div className="grid gap-3 sm:grid-cols-3">
        <StatCard label={t(locale, "failures.runsScanned")} value={String(stats.runsScanned)} />
        <StatCard label={t(locale, "failures.failedCalls")} value={String(stats.failedCalls)} accent={stats.failedCalls > 0 ? "red" : "emerald"} />
        <StatCard label={t(locale, "failures.toolsAffected")} value={String(stats.byTool.length)} />
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        {groups.map((g) => (
          <Card key={g.titleKey}>
            <CardContent className="p-4 pt-4">
              <Badge variant={g.v}>{t(locale, g.titleKey)}</Badge>
              <p className="mt-2 text-xs leading-5 text-zinc-500">{t(locale, g.bodyKey)}</p>
            </CardContent>
          </Card>
        ))}
      </div>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm"><TriangleAlert className="size-4 text-amber-600" aria-hidden /> {t(locale, "failures.logTitle")}</CardTitle>
          <CardDescription className="text-xs">{t(locale, "failures.taxonomySource")} <code className="break-all font-mono">packages/evidence/src/dsa_evidence/failure_taxonomy.py</code></CardDescription>
        </CardHeader>
        <CardContent>
          {stats.byTool.length === 0 ? (
            stats.failure === null && (
              <EmptyState
                title={t(locale, "failures.noneTitle")}
                description={t(locale, "failures.noneBody")}
                action={<Link href="/runs"><Button size="sm">{t(locale, "failures.viewRuns")}</Button></Link>}
              />
            )
          ) : (
            <ul className="divide-y divide-zinc-100">
              {stats.byTool.map((row, i) => (
                <li key={row.tool} className="flex items-start gap-3 py-2.5">
                  <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-red-50 font-mono text-[11px] text-red-700">{i + 1}</span>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm"><code className="font-mono text-xs font-semibold">{row.tool}</code>
                      <span className="ml-2 text-xs tabular-nums text-zinc-500">{t(locale, row.count === 1 ? "failures.errorOne" : "failures.errorMany").replace("{n}", String(row.count))} · {t(locale, row.runs === 1 ? "failures.runOne" : "failures.runMany").replace("{n}", String(row.runs))}</span>
                    </p>
                    <p className="mt-0.5 truncate text-xs text-zinc-500" title={row.sample}>{row.sample}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
