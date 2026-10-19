import Link from "next/link";
import { Database, Hash, Table2, FileDigit, ArrowRight, Fingerprint } from "lucide-react";
import { apiUrl, classifyResponse, failurePresentation, type ApiFailure } from "@/lib/api";
import { serverFetch, serverLocale } from "@/lib/serverApi";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/app/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/app/components/ui/tabs";
import { PageHeader } from "@/app/components/data/PageHeader";
import { StatCard } from "@/app/components/data/StatCard";
import { EmptyState, ErrorState } from "@/app/components/data/States";
import { StatusBadge } from "@/app/components/data/StatusBadge";
import { SchemaTable } from "@/app/datasets/[id]/SchemaTable";
import { t } from "@/lib/locale";

type ColumnProfile = {
  name: string;
  dtype: string;
  kind: string;
  null_count: number;
  unique_count: number | null;
  mean?: number;
};

type DatasetDetail = {
  id: string;
  filename: string;
  format: string;
  rows: number;
  cols: number;
  sha256: string | null;
  size_bytes: number | null;
  created_at: string | null;
  profile: {
    rows: number;
    columns: number;
    column_profiles: ColumnProfile[];
    duplicate_rows: number;
    missing_ratio: number;
  } | null;
};

type AnalysisItem = { id: string; status: string; user_query: string; created_at: string | null };

async function fetchOne(id: string): Promise<{ record: DatasetDetail | null; failure: ApiFailure | null }> {
  try {
    const res = await serverFetch(`/api/v1/datasets/${id}`, { cache: "no-store" });
    const failure = classifyResponse(res);
    if (failure) return { record: null, failure };
    return { record: (await res.json()) as DatasetDetail, failure: null };
  } catch {
    return { record: null, failure: "transport" };
  }
}

async function fetchAnalyses(datasetId: string): Promise<{ analyses: AnalysisItem[]; failure: ApiFailure | null }> {
  try {
    const res = await serverFetch(`/api/v1/analysis/?dataset_id=${datasetId}`, { cache: "no-store" });
    const failure = classifyResponse(res);
    if (failure) return { analyses: [], failure };
    const data = (await res.json()) as { analyses: AnalysisItem[] };
    return { analyses: data.analyses, failure: null };
  } catch {
    return { analyses: [], failure: "transport" };
  }
}

export default async function DatasetDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const locale = await serverLocale();
  const shared = failurePresentation(locale);
  const { id } = await params;
  const { record: ds, failure } = await fetchOne(id);
  // A 404 is this page's own not-found answer; every other outcome is a request that failed and must
  // not be reported as an absent dataset.
  if (failure && failure !== "notFound") {
    return (
      <div className="space-y-4">
        <PageHeader eyebrow="Step 1 · Dataset profile" title={t(locale, "dsd.unavailable")} description={t(locale, "dsd.requestFailed")} />
        <ErrorState
          message={shared[failure]}
          diagnostics={
            <Link href="/datasets"><Button variant="secondary" size="sm">{t(locale, "dsd.back")}</Button></Link>
          }
        />
      </div>
    );
  }
  if (!ds) {
    return (
      <div className="space-y-4">
        <PageHeader eyebrow="Step 1 · Dataset profile" title={t(locale, "dsd.notFound")} description={t(locale, "dsd.requestFailedBody")} />
        <ErrorState
          message={t(locale, "dsd.notFoundBody")}
          diagnostics={
            <Link href="/datasets"><Button variant="secondary" size="sm">{t(locale, "dsd.back")}</Button></Link>
          }
        />
      </div>
    );
  }

  const prof = ds.profile;
  const { analyses, failure: analysesFailure } = await fetchAnalyses(ds.id);
  const shortHash = ds.sha256 ? `${ds.sha256.slice(0, 12)}…` : "—";

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Step 1 · Dataset profile"
        title={ds.filename}
        description={`Format ${ds.format} · ${ds.rows} rows × ${ds.cols} columns${ds.created_at ? ` · Created ${ds.created_at.slice(0, 19).replace("T", " ")}` : ""}`}
        actions={
          <Link href={`/analysis?dataset=${ds.id}`}>
            <Button size="sm">{t(locale, "dsd.askTitle")} <ArrowRight className="size-4" aria-hidden /></Button>
          </Link>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label={t(locale, "dsd.rows")} value={String(ds.rows ?? "—")} hint={t(locale, "dsd.hintRows")} icon={Table2} />
        <StatCard label={t(locale, "dsd.columns")} value={String(ds.cols ?? "—")} hint={t(locale, "dsd.hintColumns")} icon={Database} />
        <StatCard label={t(locale, "dsd.format")} value={ds.format || "—"} hint={ds.size_bytes != null ? `${(ds.size_bytes / 1024).toFixed(1)} KB` : t(locale, "dsd.uploadFormat")} icon={FileDigit} />
        <StatCard label={"SHA-256"} value={shortHash} hint={ds.sha256 ?? t(locale, "dsd.hashUnavailable")} icon={Hash} accent="emerald" />
      </div>

      <Tabs defaultValue="preview">
        <TabsList>
          <TabsTrigger value="preview">Preview</TabsTrigger>
          <TabsTrigger value="schema">Schema</TabsTrigger>
          <TabsTrigger value="analyses">Analyses ({analyses.length})</TabsTrigger>
          <TabsTrigger value="lineage">Lineage</TabsTrigger>
        </TabsList>

        <TabsContent value="preview">
          {!prof ? (
            <EmptyState title={t(locale, "dsd.noProfile")} description={t(locale, "dsd.noProfileBody")} />
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">{t(locale, "dsd.qualityTitle")}</CardTitle>
                  <CardDescription className="text-xs">{t(locale, "dsd.qualitySub")}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div className="flex justify-between"><span className="text-zinc-500">{t(locale, "dsd.dupRows")}</span><span className="font-medium tabular-nums">{prof.duplicate_rows}</span></div>
                  <div className="flex justify-between"><span className="text-zinc-500">{t(locale, "dsd.missingRatio")}</span><span className="font-medium tabular-nums">{(prof.missing_ratio * 100).toFixed(1)}%</span></div>
                  <div className="flex justify-between"><span className="text-zinc-500">Shape</span><span className="font-medium tabular-nums">{prof.rows} × {prof.columns}</span></div>
                </CardContent>
              </Card>
              <Card className="min-w-0">
                <CardHeader>
                  <CardTitle className="text-sm">{t(locale, "dsd.colHealth")}</CardTitle>
                  <CardDescription className="text-xs">Null share per column — over 20% gets flagged. Showing up to 8 of {prof.column_profiles.length}.</CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2.5 text-sm">
                    {prof.column_profiles.slice(0, 8).map((c) => {
                      const nullPct = prof.rows > 0 ? (c.null_count / prof.rows) * 100 : 0;
                      const flagged = nullPct > 20;
                      return (
                        <li key={c.name}>
                          <div className="flex items-center justify-between gap-2">
                            <code className="min-w-0 flex-1 truncate font-mono text-xs" title={c.name}>{c.name}</code>
                            <span className={`shrink-0 text-xs tabular-nums ${flagged ? "font-semibold text-amber-700" : "text-zinc-500"}`}>
                              {flagged ? `⚠ ${nullPct.toFixed(1)}% null` : t(locale, "dsd.nullRatio").replace("{pct}", nullPct.toFixed(1))} · {c.unique_count ?? "—"} uniq
                            </span>
                          </div>
                          <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-zinc-100" role="img" aria-label={`${c.name}: ${nullPct.toFixed(1)}% null values`}>
                            <div
                              className={`h-full rounded-full ${flagged ? "bg-amber-400" : "bg-emerald-500"}`}
                              style={{ width: `${Math.max(2, Math.min(100, nullPct))}%` }}
                            />
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                </CardContent>
              </Card>
            </div>
          )}
        </TabsContent>

        <TabsContent value="schema">
          {!prof ? (
            <EmptyState title={t(locale, "dsd.noSchema")} description={t(locale, "dsd.noSchemaBody")} />
          ) : (
            <Card>
              <CardContent className="p-3 pt-3 sm:p-4 sm:pt-4">
                <SchemaTable columns={prof.column_profiles} filename={ds.filename} />
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="analyses">
          <Card>
            <CardContent className="p-3 pt-3 sm:p-4 sm:pt-4">
              {analysesFailure ? (
                <ErrorState message={shared[analysesFailure]} />
              ) : analyses.length === 0 ? (
                <EmptyState
                  title={t(locale, "dsd.noAnalyses")}
                  description={t(locale, "dsd.noAnalysesBody")}
                  action={<Link href={`/analysis?dataset=${ds.id}`}><Button size="sm">{t(locale, "dsd.askCta")}</Button></Link>}
                />
              ) : (
                <>
                  <p className="mb-2 text-xs text-zinc-500">{t(locale, "dsd.chainSub")}</p>
                  <ul className="divide-y divide-zinc-100">
                    {analyses.map((a, i) => (
                      <li key={a.id} className="flex items-center gap-3 py-2.5">
                        <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-zinc-100 font-mono text-[11px] text-zinc-500" title={`Session #${analyses.length - i}`}>
                          {analyses.length - i}
                        </span>
                        <Link href={`/analysis/${a.id}`} className="min-w-0 flex-1 truncate text-sm hover:underline">
                          {a.user_query || a.id}
                        </Link>
                        <StatusBadge status={a.status} />
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="lineage">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm"><Fingerprint className="size-4 text-zinc-500" aria-hidden /> Lineage</CardTitle>
              <CardDescription className="text-xs">{t(locale, "dsd.provenanceSub")}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 font-mono text-xs">
              <p className="break-all"><span className="font-sans text-zinc-500">dataset_id · </span>{ds.id}</p>
              <p className="break-all"><span className="font-sans text-zinc-500">sha256 · </span>{ds.sha256 ?? "—"}</p>
              <p><span className="font-sans text-zinc-500">source · </span>upload via POST /api/v1/datasets/</p>
              <p><span className="font-sans text-zinc-500">downstream · </span>{analyses.length} linked analysis run{analyses.length === 1 ? "" : "s"}</p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
