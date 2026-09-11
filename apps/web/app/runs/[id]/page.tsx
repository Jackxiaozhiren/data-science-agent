import Link from "next/link";
import { apiUrl } from "@/lib/api";
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

async function fetchRun(id: string): Promise<RunSummary | null> {
  try {
    const res = await fetch(apiUrl(`/api/v1/analysis/${id}`), { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as RunSummary;
  } catch {
    return null;
  }
}

export default async function RunDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const run = await fetchRun(id);
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
          <CardDescription className="text-xs">Checkpoint #12 → Replay or Fork (Run #124 → Run #124-Fork-A).</CardDescription>
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
