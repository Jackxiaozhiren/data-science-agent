import Link from "next/link";
import { TriangleAlert } from "lucide-react";
import { apiUrl } from "@/lib/api";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/app/components/ui/card";
import { Badge } from "@/app/components/ui/badge";
import { PageHeader } from "@/app/components/data/PageHeader";
import { StatCard } from "@/app/components/data/StatCard";
import { EmptyState, ErrorState } from "@/app/components/data/States";

const groups = [
  { t: "Planning failures", b: "F01–F05 · wrong plan, missing tool, bad parameters", v: "outline" as const },
  { t: "Execution failures", b: "F06–F10 · tool errors, retries, timeouts", v: "secondary" as const },
  { t: "Evidence failures", b: "F11–F15 · unsupported claims, missing links", v: "warning" as const },
];

type ToolCall = { call_id: string; tool: string; status: string; error?: string | null };

async function fetchFailureStats(): Promise<{
  unreachable: boolean;
  runsScanned: number;
  failedCalls: number;
  byTool: { tool: string; count: number; runs: number; sample: string }[];
}> {
  const empty = { unreachable: false, runsScanned: 0, failedCalls: 0, byTool: [] };
  try {
    const listRes = await fetch(apiUrl("/api/v1/analysis/"), { cache: "no-store" });
    if (!listRes.ok) return empty;
    const ids = ((await listRes.json()) as { analyses: { id: string }[] }).analyses.map((a) => a.id);
    const agg = new Map<string, { count: number; runs: Set<string>; sample: string }>();
    let failedCalls = 0;
    await Promise.all(
      ids.map(async (id) => {
        try {
          const r = await fetch(apiUrl(`/api/v1/analysis/${id}/artifacts`), { cache: "no-store" });
          if (!r.ok) return;
          const d = (await r.json()) as { tool_calls?: ToolCall[] };
          for (const tc of d.tool_calls ?? []) {
            if (tc.status === "ok") continue;
            failedCalls += 1;
            const e = agg.get(tc.tool) ?? { count: 0, runs: new Set<string>(), sample: "" };
            e.count += 1;
            e.runs.add(id);
            if (!e.sample && tc.error) {
              e.sample = String(tc.error).replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim().slice(0, 160);
            }
            agg.set(tc.tool, e);
          }
        } catch {
          // One unreadable run must not sink the whole page.
        }
      })
    );
    const byTool = [...agg.entries()]
      .map(([tool, v]) => ({ tool, count: v.count, runs: v.runs.size, sample: v.sample || "—" }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 8);
    return { unreachable: false, runsScanned: ids.length, failedCalls, byTool };
  } catch {
    return { ...empty, unreachable: true };
  }
}

export default async function FailuresPage() {
  const stats = await fetchFailureStats();
  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Evaluation · Step 3"
        title="Failure Analysis"
        description={`Taxonomy F01–F15 · Aggregated from ${stats.runsScanned} runs in this environment · Recovery rate · Agent/tool with most errors · Unsupported claim rate.`}
        actions={
          <Link href="/analysis"><Button size="sm">Back to Analysis →</Button></Link>
        }
      />
      {stats.unreachable && (
        <ErrorState message="Could not reach the DSA API — showing taxonomy reference only." />
      )}
      <div className="grid gap-3 sm:grid-cols-3">
        <StatCard label="Runs scanned" value={String(stats.runsScanned)} />
        <StatCard label="Failed tool calls" value={String(stats.failedCalls)} accent={stats.failedCalls > 0 ? "red" : "emerald"} />
        <StatCard label="Tools affected" value={String(stats.byTool.length)} />
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        {groups.map((g) => (
          <Card key={g.t}>
            <CardContent className="p-4 pt-4">
              <Badge variant={g.v}>{g.t}</Badge>
              <p className="mt-2 text-xs leading-5 text-zinc-500">{g.b}</p>
            </CardContent>
          </Card>
        ))}
      </div>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm"><TriangleAlert className="size-4 text-amber-600" aria-hidden /> Failure log — top tools by error count</CardTitle>
          <CardDescription className="text-xs">Taxonomy source: <code className="break-all font-mono">packages/evidence/src/dsa_evidence/failure_taxonomy.py</code></CardDescription>
        </CardHeader>
        <CardContent>
          {stats.byTool.length === 0 ? (
            <EmptyState
              title="No failures logged in this environment"
              description="When runs fail, they will be classified F01–F15 here with recovery rates. Meanwhile, inspect a live trace."
              action={<Link href="/runs"><Button size="sm">View runs →</Button></Link>}
            />
          ) : (
            <ul className="divide-y divide-zinc-100">
              {stats.byTool.map((t, i) => (
                <li key={t.tool} className="flex items-start gap-3 py-2.5">
                  <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-red-50 font-mono text-[11px] text-red-700">{i + 1}</span>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm"><code className="font-mono text-xs font-semibold">{t.tool}</code>
                      <span className="ml-2 text-xs tabular-nums text-zinc-500">{t.count} error{t.count === 1 ? "" : "s"} · {t.runs} run{t.runs === 1 ? "" : "s"}</span>
                    </p>
                    <p className="mt-0.5 truncate text-xs text-zinc-500" title={t.sample}>{t.sample}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
