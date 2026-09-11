import Link from "next/link";
import { Database, Hash, Table2, FileDigit, ArrowRight, Fingerprint } from "lucide-react";
import { apiUrl } from "@/lib/api";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/app/components/ui/card";
import { Badge } from "@/app/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/app/components/ui/tabs";
import { PageHeader } from "@/app/components/data/PageHeader";
import { StatCard } from "@/app/components/data/StatCard";
import { EmptyState, ErrorState } from "@/app/components/data/States";
import { StatusBadge } from "@/app/components/data/StatusBadge";
import { SchemaTable } from "@/app/datasets/[id]/SchemaTable";

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

async function fetchOne(id: string): Promise<DatasetDetail | null> {
  try {
    const res = await fetch(apiUrl(`/api/v1/datasets/${id}`), { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as DatasetDetail;
  } catch {
    return null;
  }
}

async function fetchAnalyses(datasetId: string): Promise<AnalysisItem[]> {
  try {
    const res = await fetch(apiUrl(`/api/v1/analysis/?dataset_id=${datasetId}`), { cache: "no-store" });
    if (!res.ok) return [];
    const data = (await res.json()) as { analyses: AnalysisItem[] };
    return data.analyses;
  } catch {
    return [];
  }
}

export default async function DatasetDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const ds = await fetchOne(id);
  if (!ds) {
    return (
      <div className="space-y-4">
        <PageHeader eyebrow="Step 1 · Dataset profile" title="Dataset not found" description="The dataset may have been removed, or the DSA API is unavailable." />
        <ErrorState
          message="Dataset not found or the DSA API is unavailable."
          diagnostics={
            <Link href="/datasets"><Button variant="secondary" size="sm">Back to Datasets</Button></Link>
          }
        />
      </div>
    );
  }

  const prof = ds.profile;
  const analyses = await fetchAnalyses(ds.id);
  const shortHash = ds.sha256 ? `${ds.sha256.slice(0, 12)}…` : "—";

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Step 1 · Dataset profile"
        title={ds.filename}
        description={`Format ${ds.format} · ${ds.rows} rows × ${ds.cols} columns${ds.created_at ? ` · Created ${ds.created_at.slice(0, 19).replace("T", " ")}` : ""}`}
        actions={
          <Link href={`/analysis?dataset=${ds.id}`}>
            <Button size="sm">Ask a question about this dataset <ArrowRight className="size-4" aria-hidden /></Button>
          </Link>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Rows" value={String(ds.rows ?? "—")} hint="Profiled rows" icon={Table2} />
        <StatCard label="Columns" value={String(ds.cols ?? "—")} hint="Profiled columns" icon={Database} />
        <StatCard label="Format" value={ds.format || "—"} hint={ds.size_bytes != null ? `${(ds.size_bytes / 1024).toFixed(1)} KB` : "Upload format"} icon={FileDigit} />
        <StatCard label="SHA-256" value={shortHash} hint={ds.sha256 ?? "Hash unavailable"} icon={Hash} accent="emerald" />
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
            <EmptyState title="No profile available" description="This dataset has no computed profile yet." />
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Data quality</CardTitle>
                  <CardDescription className="text-xs">Duplicates and missingness from the profiler.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div className="flex justify-between"><span className="text-zinc-500">Duplicate rows</span><span className="font-medium tabular-nums">{prof.duplicate_rows}</span></div>
                  <div className="flex justify-between"><span className="text-zinc-500">Missing ratio</span><span className="font-medium tabular-nums">{(prof.missing_ratio * 100).toFixed(1)}%</span></div>
                  <div className="flex justify-between"><span className="text-zinc-500">Shape</span><span className="font-medium tabular-nums">{prof.rows} × {prof.columns}</span></div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">First columns</CardTitle>
                  <CardDescription className="text-xs">Showing up to 8 of {prof.column_profiles.length} columns — full list under Schema.</CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-1.5 text-sm">
                    {prof.column_profiles.slice(0, 8).map((c) => (
                      <li key={c.name} className="flex items-center justify-between gap-2">
                        <code className="truncate font-mono text-xs" title={c.name}>{c.name}</code>
                        <Badge variant="secondary">{c.dtype}</Badge>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            </div>
          )}
        </TabsContent>

        <TabsContent value="schema">
          {!prof ? (
            <EmptyState title="No schema available" description="No column profiles were returned for this dataset." />
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
              {analyses.length === 0 ? (
                <EmptyState
                  title="No analyses for this dataset yet"
                  description="Ask the first question — the run will appear here with its evidence chain."
                  action={<Link href={`/analysis?dataset=${ds.id}`}><Button size="sm">Ask a question →</Button></Link>}
                />
              ) : (
                <ul className="divide-y divide-zinc-100">
                  {analyses.map((a) => (
                    <li key={a.id} className="flex items-center justify-between gap-3 py-2.5">
                      <Link href={`/analysis/${a.id}`} className="min-w-0 flex-1 truncate text-sm hover:underline">
                        {a.user_query || a.id}
                      </Link>
                      <StatusBadge status={a.status} />
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="lineage">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm"><Fingerprint className="size-4 text-zinc-500" aria-hidden /> Lineage</CardTitle>
              <CardDescription className="text-xs">Identity and provenance pinned at upload time.</CardDescription>
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
