import Link from "next/link";
import { History } from "lucide-react";
import { apiUrl } from "@/lib/api";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent } from "@/app/components/ui/card";
import { PageHeader } from "@/app/components/data/PageHeader";
import { EmptyState, ErrorState } from "@/app/components/data/States";
import { RunsTable } from "@/app/runs/RunsTable";

type RunItem = { id: string; status: string; user_query: string; created_at: string | null };

async function fetchRuns(): Promise<{ runs: RunItem[]; unreachable: boolean }> {
  try {
    const res = await fetch(apiUrl("/api/v1/analysis/"), { cache: "no-store" });
    if (!res.ok) return { runs: [], unreachable: false };
    const d = (await res.json()) as { analyses: RunItem[] };
    return { runs: d.analyses, unreachable: false };
  } catch {
    return { runs: [], unreachable: true };
  }
}

export default async function RunsPage() {
  const { runs, unreachable } = await fetchRuns();
  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Step 3 · Trace runs"
        title="Runs"
        description="Analysis inspector: Overview, Timeline, Agent Graph, Tool Calls, Evidence, Artifacts, Checkpoints, Failures, Validation, Reproduction."
        actions={
          <Link href="/analysis"><Button size="sm">New run →</Button></Link>
        }
      />
      {unreachable && (
        <ErrorState message="Could not reach the DSA API — showing an empty run list instead of a blank page." />
      )}
      <Card>
        <CardContent className="p-3 pt-3 sm:p-4 sm:pt-4">
          {runs.length === 0 ? (
            <EmptyState
              icon={<History className="size-5 text-zinc-400" aria-hidden />}
              title="No runs yet"
              description="Start an analysis to produce the first inspectable trace."
              action={<Link href="/analysis"><Button size="sm">Back to Analysis →</Button></Link>}
            />
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
