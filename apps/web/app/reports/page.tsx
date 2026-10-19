import Link from "next/link";
import { FileText } from "lucide-react";
import { apiUrl, classifyResponse, failurePresentation, type ApiFailure } from "@/lib/api";
import { serverFetch, serverLocale } from "@/lib/serverApi";
import { t, type Locale } from "@/lib/locale";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent } from "@/app/components/ui/card";
import { PageHeader } from "@/app/components/data/PageHeader";
import { EmptyState, ErrorState } from "@/app/components/data/States";
import { ReportsTable } from "@/app/reports/ReportsTable";

type RunItem = { id: string; dataset_id: string; status: string; user_query: string; created_at: string | null };

// Inherits the shared wording, and keeps this page's own line for the transport case: the report list
// below really is a fallback rendering, not a statement about stored reports.
function reportsMessages(locale: Locale): Record<ApiFailure, string> {
  return { ...failurePresentation(locale), transport: t(locale, "reports.transport") };
}

async function fetchRuns(): Promise<{ runs: RunItem[]; failure: ApiFailure | null }> {
  try {
    const res = await serverFetch("/api/v1/analysis/", { cache: "no-store" });
    const failure = classifyResponse(res);
    if (failure) return { runs: [], failure };
    const d = (await res.json()) as { analyses: RunItem[] };
    return { runs: d.analyses, failure: null };
  } catch {
    return { runs: [], failure: "transport" };
  }
}

async function fetchDatasetNames(): Promise<{ names: Map<string, string>; failure: ApiFailure | null }> {
  try {
    const res = await serverFetch("/api/v1/datasets/", { cache: "no-store" });
    const failure = classifyResponse(res);
    if (failure) return { names: new Map(), failure };
    const d = (await res.json()) as { datasets: { id: string; filename: string }[] };
    return { names: new Map(d.datasets.map((x) => [x.id, x.filename])), failure: null };
  } catch {
    return { names: new Map(), failure: "transport" };
  }
}

export default async function ReportsPage() {
  const locale = await serverLocale();
  const messages = reportsMessages(locale);
  const [{ runs, failure: runsFailure }, { names, failure: namesFailure }] = await Promise.all([
    fetchRuns(),
    fetchDatasetNames(),
  ]);
  // The dataset names only label the groups; a failure there is still a failed request, so it is told
  // with the run list's own outcome instead of leaving every group on a fallback id.
  const failure = runsFailure ?? namesFailure;
  const groups = new Map<string, RunItem[]>();
  for (const r of runs) {
    const key = r.dataset_id || "unknown";
    const arr = groups.get(key) ?? [];
    arr.push(r);
    groups.set(key, arr);
  }
  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Step 3 · Reports"
        title="Reports"
        description="Every completed run preserves a reproducible Markdown report. Open a run to preview or download it."
        actions={
          <Link href="/analysis"><Button size="sm">New analysis →</Button></Link>
        }
      />
      {failure && <ErrorState message={messages[failure]} />}
      <Card>
        <CardContent className="p-3 pt-3 sm:p-4 sm:pt-4">
          {runs.length === 0 ? (
            runsFailure === null && (
              <EmptyState
                icon={<FileText className="size-5 text-zinc-400" aria-hidden />}
                title="No reports yet"
                description="Reports appear here once an analysis run completes."
                action={<Link href="/analysis"><Button size="sm">Start your first analysis →</Button></Link>}
              />
            )
          ) : (
            <div className="space-y-2">
              {[...groups.entries()].map(([dsId, items], gi) => (
                <details key={dsId} open={gi === 0} className="rounded-xl border border-zinc-100">
                  <summary className="cursor-pointer px-3 py-2.5 text-sm font-medium hover:bg-zinc-50">
                    {names.get(dsId) ?? (dsId === "unknown" ? "Unknown dataset" : `Dataset ${dsId.slice(0, 8)}`)}
                    <span className="ml-2 font-mono text-xs font-normal text-zinc-400">{items.length} report{items.length === 1 ? "" : "s"}</span>
                  </summary>
                  <div className="border-t border-zinc-100 p-3 sm:p-4">
                    <ReportsTable runs={items} />
                  </div>
                </details>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
