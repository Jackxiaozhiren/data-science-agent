"use client";

import * as React from "react";
import Link from "next/link";
import { AlertTriangle, CheckCircle2, Copy, Check, Download, ChevronDown, FileText, XCircle } from "lucide-react";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/app/components/ui/card";
import { Badge } from "@/app/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/app/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow, TableWrapper } from "@/app/components/ui/table";
import { Progress, Separator } from "@/app/components/ui/feedback";
import { PageHeader } from "@/app/components/data/PageHeader";
import { StatusBadge } from "@/app/components/data/StatusBadge";
import { EmptyState } from "@/app/components/data/States";
import { TraceTimeline } from "@/app/components/data/TraceTimeline";
import { ConfidenceBars } from "@/app/components/ui/chart";

export type RunDetail = {
  id: string;
  status: string;
  user_query: string;
  state: {
    objective: string;
    plan: { id: string; name: string; tool: string; description: string }[];
    tool_calls: { call_id: string; tool: string; status: string; duration_ms: number; error?: string | null; input: Record<string, unknown>; output?: unknown }[];
    evidence: { id: string; claim: string; source_type: string; source_id: string; confidence: number; result: Record<string, unknown> }[];
    insights: { id: string; finding: string; evidence_ids: string[]; limitation?: string }[];
    validation_results: { check: string; passed: boolean; message: string }[];
    report_markdown: string | null;
    artifacts: { id: string; type: string; path: string; metadata: Record<string, unknown> }[];
  } | null;
};

function ValidationRing({ passed, total }: { passed: number; total: number }) {
  const pct = total === 0 ? 0 : Math.round((passed / total) * 100);
  const r = 26;
  const c = 2 * Math.PI * r;
  return (
    <div className="flex items-center gap-3" role="img" aria-label={`Validation ${passed} of ${total} passed (${pct}%)`}>
      <svg width="64" height="64" viewBox="0 0 64 64" aria-hidden>
        <circle cx="32" cy="32" r={r} fill="none" stroke="#e4e4e7" strokeWidth="7" />
        <circle
          cx="32" cy="32" r={r} fill="none"
          stroke={pct === 100 ? "#10b981" : pct >= 50 ? "#f59e0b" : "#ef4444"}
          strokeWidth="7" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c - (c * pct) / 100}
          transform="rotate(-90 32 32)"
        />
        <text x="32" y="36" textAnchor="middle" fontSize="13" fontWeight="700" fill="#3f3f46">{pct}%</text>
      </svg>
      <div>
        <p className="text-sm font-semibold">{passed}/{total} checks passed</p>
        <p className="text-xs text-zinc-500">Validation gate for this run</p>
      </div>
    </div>
  );
}

export function RunInspector({ run, reportUrl }: { run: RunDetail; reportUrl: string }) {
  const st = run.state;
  const [copied, setCopied] = React.useState(false);
  const validations = st?.validation_results ?? [];
  const passed = validations.filter((v) => v.passed).length;

  async function copyReport() {
    if (!st?.report_markdown) return;
    try {
      await navigator.clipboard.writeText(st.report_markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Step 3 · Inspect the evidence"
        title={`Analysis ${run.id.slice(0, 12)}`}
        description={`Objective: ${st?.objective || run.user_query}`}
        actions={
          <>
            <StatusBadge status={run.status} />
            {st?.report_markdown && (
              <a href={reportUrl} target="_blank" rel="noreferrer">
                <Button variant="secondary" size="sm"><Download className="size-4" aria-hidden /> Download report</Button>
              </a>
            )}
          </>
        }
      />

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="trace">Trace ({st?.tool_calls.length ?? 0})</TabsTrigger>
          <TabsTrigger value="evidence">Evidence ({st?.evidence.length ?? 0})</TabsTrigger>
          <TabsTrigger value="insights">Insights ({st?.insights.length ?? 0})</TabsTrigger>
          <TabsTrigger value="artifacts">Artifacts & Report</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <div className="grid items-start gap-4 lg:grid-cols-[1.2fr_0.8fr]">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Plan timeline</CardTitle>
                <CardDescription className="text-xs">Ordered steps the agent planned before executing tools.</CardDescription>
              </CardHeader>
              <CardContent>
                <TraceTimeline
                  steps={(st?.plan ?? []).map((s, i) => ({
                    id: s.id, name: s.name, tool: s.tool, description: s.description,
                    status: run.status === "COMPLETED" ? "done" : i === 0 && run.status === "RUNNING" ? "active" : run.status === "COMPLETED" ? "done" : "todo",
                  }))}
                />
              </CardContent>
            </Card>
            <div className="space-y-4">
              <Card>
                <CardHeader><CardTitle className="text-sm">Validation</CardTitle></CardHeader>
                <CardContent className="space-y-3">
                  <ValidationRing passed={passed} total={validations.length} />
                  <Separator />
                  <ul className="space-y-1.5 text-sm">
                    {validations.length === 0 && <li className="text-xs text-zinc-500">No validation results.</li>}
                    {validations.map((v, i) => (
                      <li key={i} className={`flex items-start gap-2 text-xs leading-5 ${v.passed ? "text-emerald-700" : "text-red-600"}`}>
                        {v.passed ? <CheckCircle2 className="mt-0.5 size-3.5 shrink-0" aria-hidden /> : <XCircle className="mt-0.5 size-3.5 shrink-0" aria-hidden />}
                        <span><strong>{v.check}:</strong> {v.message}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="grid grid-cols-3 gap-2 p-4 pt-4 text-center">
                  {[
                    { v: String(st?.tool_calls.length ?? 0), l: "Tool calls" },
                    { v: String(st?.evidence.length ?? 0), l: "Evidence" },
                    { v: String(st?.artifacts.length ?? 0), l: "Artifacts" },
                  ].map((s) => (
                    <div key={s.l}>
                      <p className="text-xl font-semibold tabular-nums">{s.v}</p>
                      <p className="text-xs text-zinc-500">{s.l}</p>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="trace">
          <Card>
            <CardContent className="p-3 pt-3 sm:p-4 sm:pt-4">
              {(st?.tool_calls.length ?? 0) === 0 ? (
                <EmptyState title="No tool calls" description="This run has no recorded tool executions yet." />
              ) : (
                <TableWrapper>
                  <Table>
                    <caption className="sr-only">Agent tool calls</caption>
                    <TableHeader>
                      <TableRow><TableHead>Tool</TableHead><TableHead>Status</TableHead><TableHead>Duration</TableHead><TableHead>Call ID</TableHead><TableHead /></TableRow>
                    </TableHeader>
                    <TableBody>
                      {(st?.tool_calls ?? []).map((tc) => (
                        <React.Fragment key={tc.call_id}>
                          <TableRow>
                            <TableCell><code className="font-mono text-xs">{tc.tool}</code></TableCell>
                            <TableCell>
                              <Badge variant={tc.status === "ok" ? "success" : "destructive"}>{tc.status}</Badge>
                            </TableCell>
                            <TableCell className="tabular-nums">{tc.duration_ms}ms</TableCell>
                            <TableCell><code className="font-mono text-xs">{tc.call_id.slice(0, 12)}</code></TableCell>
                            <TableCell>
                              <details>
                                <summary className="inline-flex cursor-pointer items-center gap-1 text-xs font-medium text-zinc-600 hover:text-zinc-900">
                                  <ChevronDown className="size-3" aria-hidden /> input/output
                                </summary>
                                <div className="mt-2 space-y-2">
                                  <div>
                                    <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">Input</p>
                                    <pre className="mt-1 max-h-48 overflow-auto rounded-lg bg-zinc-950 p-2 font-mono text-[11px] leading-5 text-zinc-200">{JSON.stringify(tc.input, null, 2)}</pre>
                                  </div>
                                  <div>
                                    <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">Output{tc.error ? " · error" : ""}</p>
                                    <pre className="mt-1 max-h-48 overflow-auto rounded-lg bg-zinc-950 p-2 font-mono text-[11px] leading-5 text-zinc-200">{tc.error ?? JSON.stringify(tc.output ?? null, null, 2)}</pre>
                                  </div>
                                </div>
                              </details>
                            </TableCell>
                          </TableRow>
                        </React.Fragment>
                      ))}
                    </TableBody>
                  </Table>
                </TableWrapper>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="evidence">
          <div className="space-y-4">
            {(st?.evidence.length ?? 0) > 0 && (
              <ConfidenceBars values={(st?.evidence ?? []).map((e) => e.confidence)} />
            )}
            {(st?.evidence.length ?? 0) === 0 && (
              <EmptyState title="No evidence" description="No claim-level evidence was preserved for this run." />
            )}
            <ul className="grid gap-3">
              {(st?.evidence ?? []).map((ev) => (
                <li key={ev.id}>
                  <Card>
                    <CardContent className="space-y-2 p-4 pt-4">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <code className="font-mono text-xs text-zinc-500">{ev.id} · {ev.source_type} → {ev.source_id}</code>
                        <span className="text-xs font-medium tabular-nums text-emerald-700">conf {ev.confidence.toFixed(2)}</span>
                      </div>
                      <Progress value={ev.confidence * 100} aria-label={`Confidence ${ev.confidence.toFixed(2)}`} />
                      <p className="text-sm font-medium leading-6">{ev.claim}</p>
                      <details>
                        <summary className="cursor-pointer text-xs font-medium text-zinc-600 hover:text-zinc-900">Result JSON</summary>
                        <pre className="mt-2 max-h-56 overflow-auto rounded-lg bg-zinc-950 p-3 font-mono text-[11px] leading-5 text-zinc-200">{JSON.stringify(ev.result, null, 2)}</pre>
                      </details>
                    </CardContent>
                  </Card>
                </li>
              ))}
            </ul>
          </div>
        </TabsContent>

        <TabsContent value="insights">
          <div className="space-y-3">
            {(st?.insights.length ?? 0) === 0 && (
              <EmptyState title="No insights" description="No summarized findings were produced for this run." />
            )}
            {(st?.insights ?? []).map((ins) => (
              <Card key={ins.id}>
                <CardContent className="space-y-2 p-4 pt-4">
                  <p className="text-sm leading-6">{ins.finding}</p>
                  <p className="text-xs text-zinc-500">Evidence: {ins.evidence_ids.join(", ") || "—"}</p>
                  {ins.limitation && (
                    <p className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-2.5 text-xs leading-5 text-amber-800" role="note">
                      <AlertTriangle className="mt-0.5 size-3.5 shrink-0" aria-hidden />
                      <span><strong>Limitation:</strong> {ins.limitation}</span>
                    </p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="artifacts">
          <div className="grid items-start gap-4 lg:grid-cols-[0.9fr_1.1fr]">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Artifacts ({st?.artifacts.length ?? 0})</CardTitle>
                <CardDescription className="text-xs">Files generated during the run.</CardDescription>
              </CardHeader>
              <CardContent>
                {(st?.artifacts.length ?? 0) === 0 ? (
                  <p className="text-sm text-zinc-500">No artifacts.</p>
                ) : (
                  <ul className="space-y-1.5">
                    {(st?.artifacts ?? []).map((a) => (
                      <li key={a.id} className="flex items-center gap-2 font-mono text-xs">
                        <FileText className="size-3.5 shrink-0 text-zinc-400" aria-hidden />
                        <span className="truncate" title={a.path}>{a.type} — {a.path}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex-row items-center justify-between space-y-0">
                <div>
                  <CardTitle className="text-sm">Report preview</CardTitle>
                  <CardDescription className="text-xs">Reproducible Markdown preserved with the run.</CardDescription>
                </div>
                {st?.report_markdown && (
                  <Button variant="secondary" size="sm" onClick={copyReport}>
                    {copied ? <><Check className="size-3.5" aria-hidden /> Copied</> : <><Copy className="size-3.5" aria-hidden /> Copy Markdown</>}
                  </Button>
                )}
              </CardHeader>
              <CardContent>
                {st?.report_markdown ? (
                  <>
                    <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-lg bg-zinc-950 p-3 text-xs leading-6 text-zinc-200">{st.report_markdown.slice(0, 6000)}</pre>
                    <a href={reportUrl} target="_blank" rel="noreferrer" className="mt-3 inline-block text-sm font-medium underline">
                      Open full Markdown report ↗
                    </a>
                  </>
                ) : (
                  <EmptyState title="No report yet" description="The Markdown report is generated when the run completes." />
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      <p className="text-xs text-zinc-400">
        Full trace via <code className="font-mono">GET /api/v1/analysis/{run.id}</code> · Evidence graph at{" "}
        <code className="font-mono">/evidence/{"{evidence_id}"}</code> · <Link href="/runs" className="underline">All runs</Link>
      </p>
    </div>
  );
}
