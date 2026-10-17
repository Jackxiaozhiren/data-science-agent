import Link from "next/link";
import { apiUrl, classifyResponse, FAILURE_PRESENTATION, type ApiFailure } from "@/lib/api";
import { serverFetch } from "@/lib/serverApi";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/app/components/ui/card";
import { PageHeader } from "@/app/components/data/PageHeader";
import { StatusBadge } from "@/app/components/data/StatusBadge";
import { ErrorState } from "@/app/components/data/States";

type RunSummary = {
  id: string;
  status: string;
  user_query: string;
  state: {
    objective: string;
    plan: unknown[];
    tool_calls: unknown[];
    evidence: unknown[];
    artifacts: unknown[];
  } | null;
};

async function fetchRun(id: string): Promise<{ record: RunSummary | null; failure: ApiFailure | null }> {
  try {
    const res = await serverFetch(`/api/v1/analysis/${id}`, { cache: "no-store" });
    const failure = classifyResponse(res);
    if (failure) return { record: null, failure };
    return { record: (await res.json()) as RunSummary, failure: null };
  } catch {
    return { record: null, failure: "transport" };
  }
}

export default async function RunDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const { record: run, failure } = await fetchRun(id);
  // A 404 is this page's own not-found answer; every other outcome is a request that failed and must
  // not be reported as an absent run.
  if (failure && failure !== "notFound") {
    return (
      <div className="space-y-4">
        <PageHeader eyebrow="Step 3 · Trace run" title={`Run ${id.slice(0, 12)}`} description="This run could not be loaded." />
        <ErrorState
          message={FAILURE_PRESENTATION[failure]}
          diagnostics={<Link href="/runs"><Button variant="secondary" size="sm">Back to Runs</Button></Link>}
        />
      </div>
    );
  }
  if (!run) {
    return (
      <div className="space-y-4">
        <PageHeader eyebrow="Step 3 · Trace run" title={`Run ${id.slice(0, 12)}`} description="This run could not be loaded." />
        <ErrorState
          message="Run not found or the DSA API is unavailable."
          diagnostics={<Link href="/runs"><Button variant="secondary" size="sm">Back to Runs</Button></Link>}
        />
      </div>
    );
  }
  const st = run.state;
  const counts = [
    { v: String(st?.plan.length ?? 0), l: "Plan steps" },
    { v: String(st?.tool_calls.length ?? 0), l: "Tool calls" },
    { v: String(st?.evidence.length ?? 0), l: "Evidence" },
    { v: String(st?.artifacts.length ?? 0), l: "Artifacts" },
  ];
  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Step 3 · Trace run"
        title={`Run ${id.slice(0, 12)}`}
        description={st?.objective || run.user_query}
        actions={
          <>
            <StatusBadge status={run.status} />
            <Link href={`/analysis/${id}`}><Button size="sm">Open evidence inspector →</Button></Link>
          </>
        }
      />
      <Card>
        <CardContent className="grid grid-cols-2 gap-2 p-4 pt-4 text-center sm:grid-cols-4">
          {counts.map((c) => (
            <div key={c.l}>
              <p className="text-xl font-semibold tabular-nums">{c.v}</p>
              <p className="text-xs text-zinc-500">{c.l}</p>
            </div>
          ))}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Replay / Fork</CardTitle>
          <CardDescription className="text-xs">Replay and fork need a checkpoint API that does not exist in this build.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Link href={`/runs/${id}/replay`}><Button variant="secondary" size="sm">Open replay →</Button></Link>
          <Link href={`/analysis/${id}`}><Button variant="secondary" size="sm">Inspect trace →</Button></Link>
        </CardContent>
      </Card>
      <p className="text-xs text-zinc-400">API: <code className="font-mono">GET /api/v1/analysis/{id}</code></p>
    </div>
  );
}
