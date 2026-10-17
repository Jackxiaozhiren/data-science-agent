import Link from "next/link";
import { apiUrl, classifyResponse, FAILURE_PRESENTATION, type ApiFailure } from "@/lib/api";
import { serverFetch, ownerFromRequest } from "@/lib/serverApi";
import { withOwnerParam } from "@/lib/owner";
import { PageHeader } from "@/app/components/data/PageHeader";
import { ErrorState } from "@/app/components/data/States";
import { Button } from "@/app/components/ui/button";
import { RunInspector, type RunDetail } from "@/app/analysis/[runId]/RunInspector";

async function fetchRun(id: string): Promise<{ record: RunDetail | null; failure: ApiFailure | null }> {
  try {
    const res = await serverFetch(`/api/v1/analysis/${id}`, { cache: "no-store" });
    const failure = classifyResponse(res);
    if (failure) return { record: null, failure };
    return { record: (await res.json()) as RunDetail, failure: null };
  } catch {
    return { record: null, failure: "transport" };
  }
}

export default async function TracePage({ params, searchParams }: { params: Promise<{ runId: string }>; searchParams: Promise<{ from?: string }> }) {
  const { runId } = await params;
  const { from } = await searchParams;
  const { record: run, failure } = await fetchRun(runId);
  // A 404 is this page's own not-found answer. Every other outcome is a request that failed, and saying
  // "run not found" for it would tell a reader the product has no such run when the API never answered.
  if (!run) {
    const missing = failure === null || failure === "notFound";
    return (
      <div className="space-y-4">
        <PageHeader
          eyebrow="Step 3 · Inspect the evidence"
          title={missing ? "Run not found" : "Run could not be loaded"}
          description={
            missing
              ? `No trace for ${runId} — this API says the run does not exist.`
              : `No trace for ${runId} could be read, so nothing below is a statement about the run.`
          }
        />
        <ErrorState
          message={failure ? FAILURE_PRESENTATION[failure] : `No run ${runId} exists behind this API.`}
          diagnostics={
            <Link href="/analysis"><Button variant="secondary" size="sm">Back to Analysis</Button></Link>
          }
        />
      </div>
    );
  }

  // The three report links open in a new tab, which is a navigation a script cannot attach a header to, so the
  // id travels in the query here and nowhere else. `rel="noreferrer"` on the anchors keeps it out of the
  // `Referer` header; what it cannot avoid is the browser's own history, and `docs/hosted-demo.md` says so.
  const owner = await ownerFromRequest();
  const reportUrl = withOwnerParam(apiUrl(`/api/v1/analysis/${runId}/report?format=markdown`), owner);
  const findingsUrl = withOwnerParam(
    apiUrl(`/api/v1/analysis/${runId}/report?format=markdown&mode=findings`),
    owner,
  );
  const htmlUrl = withOwnerParam(apiUrl(`/api/v1/analysis/${runId}/report?format=html`), owner);
  return <RunInspector run={run} reportUrl={reportUrl} findingsUrl={findingsUrl} htmlUrl={htmlUrl} fromRunId={from} />;
}
