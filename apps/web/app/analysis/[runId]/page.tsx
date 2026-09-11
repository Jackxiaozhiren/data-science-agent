import Link from "next/link";
import { apiUrl } from "@/lib/api";
import { PageHeader } from "@/app/components/data/PageHeader";
import { ErrorState } from "@/app/components/data/States";
import { Button } from "@/app/components/ui/button";
import { RunInspector, type RunDetail } from "@/app/analysis/[runId]/RunInspector";

async function fetchRun(id: string): Promise<RunDetail | null> {
  try {
    const res = await fetch(apiUrl(`/api/v1/analysis/${id}`), { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as RunDetail;
  } catch {
    return null;
  }
}

export default async function TracePage({ params, searchParams }: { params: Promise<{ runId: string }>; searchParams: Promise<{ from?: string }> }) {
  const { runId } = await params;
  const { from } = await searchParams;
  const run = await fetchRun(runId);
  if (!run) {
    return (
      <div className="space-y-4">
        <PageHeader eyebrow="Step 3 · Inspect the evidence" title="Run not found" description={`No trace for ${runId} — the run may not exist or the API is unreachable.`} />
        <ErrorState
          message="Run not found or the DSA API is unavailable."
          diagnostics={
            <Link href="/analysis"><Button variant="secondary" size="sm">Back to Analysis</Button></Link>
          }
        />
      </div>
    );
  }

  const reportUrl = apiUrl(`/api/v1/analysis/${runId}/report?format=markdown`);
  return <RunInspector run={run} reportUrl={reportUrl} fromRunId={from} />;
}
