"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { GitCompareArrows } from "lucide-react";
import { API_BASE_URL, apiUrl } from "@/lib/api";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/app/components/ui/card";
import { PageHeader } from "@/app/components/data/PageHeader";
import { StatusBadge } from "@/app/components/data/StatusBadge";
import { EmptyState, ErrorState } from "@/app/components/data/States";
import { CardsSkeleton } from "@/app/components/data/States";

type Full = {
  id: string;
  status: string;
  user_query: string;
  dataset_id: string;
  created_at: string | null;
  state: {
    plan: unknown[];
    tool_calls: { duration_ms: number; status: string }[];
    evidence: unknown[];
    insights: unknown[];
    validation_results: { passed: boolean }[];
    artifacts: unknown[];
  } | null;
};

function metric(a: Full | null, b: Full | null, label: string, pick: (r: Full) => string, num?: (r: Full) => number | null) {
  const av = a ? pick(a) : "—";
  const bv = b ? pick(b) : "—";
  let win: 0 | 1 | 2 = 0;
  if (a && b && num) {
    const an = num(a);
    const bn = num(b);
    if (an != null && bn != null && an !== bn) win = an > bn ? 1 : 2;
  }
  return { label, av, bv, win };
}

function CompareWorkspace() {
  const sp = useSearchParams();
  const aId = sp.get("a") || "";
  const bId = sp.get("b") || "";
  const [a, setA] = useState<Full | null>(null);
  const [b, setB] = useState<Full | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!aId || !bId) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    Promise.all(
      [aId, bId].map((id) =>
        fetch(apiUrl(`/api/v1/analysis/${id}`)).then((r) => (r.ok ? (r.json() as Promise<Full>) : null))
      )
    )
      .then(([ra, rb]) => {
        if (cancelled) return;
        if (!ra || !rb) setErr("One of the runs could not be loaded — it may have been removed.");
        setA(ra);
        setB(rb);
      })
      .catch((e) => {
        if (!cancelled) setErr(`Could not reach the DSA API at ${API_BASE_URL}. ${String(e)}`);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [aId, bId]);

  const valRate = (r: Full) => {
    const v = r.state?.validation_results ?? [];
    return v.length === 0 ? "—" : `${v.filter((x) => x.passed).length}/${v.length}`;
  };
  const valPct = (r: Full) => {
    const v = r.state?.validation_results ?? [];
    return v.length === 0 ? null : v.filter((x) => x.passed).length / v.length;
  };
  const totalMs = (r: Full) => (r.state?.tool_calls ?? []).reduce((s, t) => s + (t.duration_ms || 0), 0);

  const rows =
    a && b
      ? [
          metric(a, b, "Status", (r) => r.status),
          metric(a, b, "Validation", valRate, valPct),
          metric(a, b, "Evidence", (r) => String(r.state?.evidence.length ?? 0), (r) => r.state?.evidence.length ?? null),
          metric(a, b, "Tool calls", (r) => String(r.state?.tool_calls.length ?? 0), (r) => r.state?.tool_calls.length ?? null),
          metric(a, b, "Tool time", (r) => `${totalMs(r)}ms`, totalMs),
          metric(a, b, "Insights", (r) => String(r.state?.insights.length ?? 0), (r) => r.state?.insights.length ?? null),
          metric(a, b, "Artifacts", (r) => String(r.state?.artifacts.length ?? 0), (r) => r.state?.artifacts.length ?? null),
        ]
      : [];

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Step 3 · Compare runs"
        title="Compare runs"
        description="Side-by-side evidence output for two runs. Emerald marks the larger value."
        actions={
          <Link href="/runs"><Button variant="secondary" size="sm">Back to Runs</Button></Link>
        }
      />
      {err && <ErrorState message={err} />}
      {loading ? (
        <CardsSkeleton count={2} />
      ) : !aId || !bId ? (
        <EmptyState
          icon={<GitCompareArrows className="size-5 text-zinc-400" aria-hidden />}
          title="Pick two runs to compare"
          description="Select exactly two runs on the Runs page, then come back here."
          action={<Link href="/runs"><Button size="sm">Go to Runs →</Button></Link>}
        />
      ) : a && b ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2">
            {[a, b].map((r, i) => (
              <Card key={r.id} className="min-w-0">
                <CardHeader>
                  <CardTitle className="font-mono text-sm">{i === 0 ? "A · " : "B · "}{r.id.slice(0, 14)}</CardTitle>
                  <CardDescription className="truncate" title={r.user_query}>{r.user_query}</CardDescription>
                </CardHeader>
                <CardContent className="flex flex-wrap items-center gap-2">
                  <StatusBadge status={r.status} />
                  <Link href={`/analysis/${r.id}`} className="text-xs font-medium underline">Inspect →</Link>
                </CardContent>
              </Card>
            ))}
          </div>
          <Card>
            <CardContent className="space-y-2 p-3 pt-3 sm:p-4 sm:pt-4">
              {rows.map((m) => (
                <div key={m.label} className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 rounded-lg border border-zinc-100 px-3 py-2 text-sm">
                  <span className={`min-w-0 truncate text-right tabular-nums ${m.win === 1 ? "font-semibold text-emerald-700" : ""}`} title={m.av}>
                    {m.label === "Status" && a ? <StatusBadge status={a.status} /> : m.av}
                  </span>
                  <span className="whitespace-nowrap text-[11px] font-medium uppercase tracking-wider text-zinc-400">{m.label}</span>
                  <span className={`min-w-0 truncate tabular-nums ${m.win === 2 ? "font-semibold text-emerald-700" : ""}`} title={m.bv}>
                    {m.label === "Status" && b ? <StatusBadge status={b.status} /> : m.bv}
                  </span>
                </div>
              ))}
            </CardContent>
          </Card>
        </>
      ) : (
        !err && <EmptyState title="Runs unavailable" description="Both runs must exist to compare." />
      )}
    </div>
  );
}

export default function CompareRunsPage() {
  return (
    <Suspense fallback={<CardsSkeleton count={2} />}>
      <CompareWorkspace />
    </Suspense>
  );
}
