import Link from "next/link";
import { apiUrl, classifyResponse, failurePresentation, type ApiFailure } from "@/lib/api";
import { serverFetch, serverLocale } from "@/lib/serverApi";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/app/components/ui/card";
import { PageHeader } from "@/app/components/data/PageHeader";
import { StatusBadge } from "@/app/components/data/StatusBadge";
import { ErrorState } from "@/app/components/data/States";
import { t } from "@/lib/locale";

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
  const locale = await serverLocale();
  const shared = failurePresentation(locale);
  const { id } = await params;
  const { record: run, failure } = await fetchRun(id);
  // A 404 is this page's own not-found answer; every other outcome is a request that failed and must
  // not be reported as an absent run.
  if (failure && failure !== "notFound") {
    return (
      <div className="space-y-4">
        <PageHeader eyebrow={t(locale, "runDetail.eyebrow")} title={`Run ${id.slice(0, 12)}`} description={t(locale, "runDetail.couldNotLoad")} />
        <ErrorState
          message={shared[failure]}
          diagnostics={<Link href="/runs"><Button variant="secondary" size="sm">{t(locale, "cmp.back")}</Button></Link>}
        />
      </div>
    );
  }
  if (!run) {
    return (
      <div className="space-y-4">
        <PageHeader eyebrow={t(locale, "runDetail.eyebrow")} title={`Run ${id.slice(0, 12)}`} description={t(locale, "runDetail.couldNotLoad")} />
        <ErrorState
          message={t(locale, "runDetail.notFoundBody")}
          diagnostics={<Link href="/runs"><Button variant="secondary" size="sm">{t(locale, "cmp.back")}</Button></Link>}
        />
      </div>
    );
  }
  const st = run.state;
  const counts = [
    { v: String(st?.plan.length ?? 0), l: t(locale, "runDetail.planSteps") },
    { v: String(st?.tool_calls.length ?? 0), l: t(locale, "insp.statToolCalls") },
    { v: String(st?.evidence.length ?? 0), l: t(locale, "insp.statEvidence") },
    { v: String(st?.artifacts.length ?? 0), l: t(locale, "insp.statArtifacts") },
  ];
  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow={t(locale, "runDetail.eyebrow")}
        title={`Run ${id.slice(0, 12)}`}
        description={st?.objective || run.user_query}
        actions={
          <>
            <StatusBadge status={run.status} />
            <Link href={`/analysis/${id}`}><Button size="sm">{t(locale, "runDetail.openInspector")}</Button></Link>
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
          <CardTitle className="text-sm">{t(locale, "runDetail.replayFork")}</CardTitle>
          <CardDescription className="text-xs">Replay and fork need a checkpoint API that does not exist in this build.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Link href={`/runs/${id}/replay`}><Button variant="secondary" size="sm">{t(locale, "runDetail.openReplay")}</Button></Link>
          <Link href={`/analysis/${id}`}><Button variant="secondary" size="sm">{t(locale, "runDetail.inspectTrace")}</Button></Link>
        </CardContent>
      </Card>
      <p className="text-xs text-zinc-400">API: <code className="font-mono">GET /api/v1/analysis/{id}</code></p>
    </div>
  );
}
