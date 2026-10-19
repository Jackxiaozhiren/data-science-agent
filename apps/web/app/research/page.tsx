import Link from "next/link";
import { FlaskConical, Sigma, Layers } from "lucide-react";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/app/components/ui/card";
import { PageHeader } from "@/app/components/data/PageHeader";
import { StatCard } from "@/app/components/data/StatCard";
import { EmptyState, ErrorState } from "@/app/components/data/States";
import { ExperimentsTable } from "@/app/research/ExperimentsTable";
import { TrackedExperimentsTable } from "@/app/research/TrackedExperimentsTable";
import { apiUrl, classifyResponse, failurePresentation, type ApiFailure } from "@/lib/api";
import { serverFetch, serverLocale } from "@/lib/serverApi";
import { t } from "@/lib/locale";

type Tracked = { id: string; name: string; run_id: string; created_at: string | null };

async function fetchTracked(): Promise<{ rows: Tracked[]; failure: ApiFailure | null }> {
  try {
    const res = await serverFetch("/api/v1/experiments/?limit=20", { cache: "no-store" });
    const failure = classifyResponse(res);
    if (failure) return { rows: [], failure };
    const d = (await res.json()) as { experiments: Tracked[] };
    return { rows: Array.isArray(d.experiments) ? d.experiments : [], failure: null };
  } catch {
    return { rows: [], failure: "transport" };
  }
}

// research/results is a repository path, not something the web image ships, so the list comes from the
// API that now carries it (audit §168). The cap stays where the page had it.
async function fetchExperiments(): Promise<{ files: string[]; failure: ApiFailure | null }> {
  try {
    const res = await serverFetch("/api/v1/research/experiments", { cache: "no-store" });
    const failure = classifyResponse(res);
    if (failure) return { files: [], failure };
    const d = (await res.json()) as { experiments: string[] };
    return { files: Array.isArray(d.experiments) ? d.experiments : [], failure: null };
  } catch {
    return { files: [], failure: "transport" };
  }
}

const RUNNER = "uv run python research/experiments/run_ablation.py --limit 20 --out research/results";

export default async function ResearchPage() {
  const locale = await serverLocale();
  const shared = failurePresentation(locale);
  const [experiments, trackedRuns] = await Promise.all([fetchExperiments(), fetchTracked()]);
  const exps = experiments.files;
  const expsFailure = experiments.failure;
  const { rows: tracked, failure: trackedFailure } = trackedRuns;
  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Research · Step 3"
        title="Research"
        description={t(locale, "rs.closure")}
        actions={
          <Link href="/analysis"><Button size="sm">{t(locale, "rs.back")}</Button></Link>
        }
      />
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="Ablations" value="A–F" hint="LLM-only → Full" icon={FlaskConical} />
        <StatCard label="Eval dims" value="10-dim" hint="+ 6-level breakdown" icon={Layers} />
        <StatCard label="Significance" value="CI / McNemar" hint="+ Wilcoxon" icon={Sigma} />
      </div>
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Recent experiments ({exps.length})</CardTitle>
          <CardDescription className="text-xs">{t(locale, "rs.ablationNote")}</CardDescription>
        </CardHeader>
        <CardContent>
          {exps.length ? (
            <ExperimentsTable files={exps} />
          ) : expsFailure === "notFound" ? (
            <EmptyState
              title={t(locale, "rs.notShipped")}
              description={t(locale, "rs.notShippedBody")}
            />
          ) : expsFailure ? (
            <ErrorState message={shared[expsFailure]} />
          ) : (
            <EmptyState
              title={t(locale, "rs.noResults")}
              description={`Run the ablation runner to produce the first result files: ${RUNNER}`}
            />
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">API-tracked experiments ({tracked.length})</CardTitle>
          <CardDescription className="text-xs">{t(locale, "rs.recordedNote")}</CardDescription>
        </CardHeader>
        <CardContent>
          {trackedFailure ? (
            <ErrorState message={shared[trackedFailure]} />
          ) : tracked.length ? (
            <TrackedExperimentsTable rows={tracked} />
          ) : (
            <EmptyState
              title={t(locale, "rs.noRuns")}
              description={t(locale, "rs.noRunsBody")}
            />
          )}
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-4 pt-4 text-xs leading-5 text-zinc-500">
          Runner provenance: ablation configs at <code className="break-all font-mono">research/experiments/ablation_matrix.py</code> (A LLM-only → F Full). Significance: <code className="break-all font-mono">packages/evaluation/src/dsa_evaluation/significance.py</code>.
        </CardContent>
      </Card>
    </div>
  );
}
