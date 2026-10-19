import Link from "next/link";
import { History } from "lucide-react";
import { apiUrl, classifyResponse, failurePresentation, type ApiFailure } from "@/lib/api";
import { serverFetch, serverLocale } from "@/lib/serverApi";
import { t, type Locale } from "@/lib/locale";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent } from "@/app/components/ui/card";
import { PageHeader } from "@/app/components/data/PageHeader";
import { EmptyState, ErrorState } from "@/app/components/data/States";
import { RunsTable } from "@/app/runs/RunsTable";

type RunItem = { id: string; status: string; user_query: string; created_at: string | null };

// Inherits the shared wording, and keeps this page's own line for the case it already handled: the
// transport failure is what readers hit on the hosted demo, and "an empty list instead of a blank
// page" is the sentence that tells them a fallback is in play.
function runsMessages(locale: Locale): Record<ApiFailure, string> {
  return { ...failurePresentation(locale), transport: t(locale, "runs.transport") };
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

export default async function RunsPage() {
  const locale = await serverLocale();
  const messages = runsMessages(locale);
  const { runs, failure } = await fetchRuns();
  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Step 3 · Trace runs"
        title="Runs"
        description="Analysis inspector: Overview, Timeline, Agent Graph, Tool Calls, Evidence, Artifacts, Failures, Validation, Reproduction."
        actions={
          <Link href="/analysis"><Button size="sm">New run →</Button></Link>
        }
      />
      {failure && <ErrorState message={messages[failure]} />}
      <Card>
        <CardContent className="p-3 pt-3 sm:p-4 sm:pt-4">
          {runs.length === 0 ? (
            failure === null && (
              <EmptyState
                icon={<History className="size-5 text-zinc-400" aria-hidden />}
                title="No runs yet"
                description="Start an analysis to produce the first inspectable trace."
                action={<Link href="/analysis"><Button size="sm">Back to Analysis →</Button></Link>}
              />
            )
          ) : (
            <RunsTable runs={runs} />
          )}
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-4 pt-4 text-xs leading-5 text-zinc-500">
          Trace from <code className="font-mono">GET /api/v1/analysis/{"{id}"}</code> · SSE: <code className="font-mono">/events</code> · Evidence graph at <code className="font-mono">/evidence/{"{evidence_id}"}</code>
        </CardContent>
      </Card>
    </div>
  );
}
