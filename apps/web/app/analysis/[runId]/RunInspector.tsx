"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertTriangle, CheckCircle2, Copy, Check, Download, ChevronDown, FileText, XCircle, Send, Loader2, Bell, BellOff } from "lucide-react";
import { apiUrl } from "@/lib/api";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/app/components/ui/card";
import { Badge } from "@/app/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/app/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow, TableWrapper } from "@/app/components/ui/table";
import { Input } from "@/app/components/ui/input";
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
  dataset_id: string;
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

type Progress = {
  status: string;
  progress_pct: number;
  steps_total: number;
  steps_done: number;
  evidence: number;
  insights: number;
};

const TERMINAL = new Set(["COMPLETED", "FAILED"]);
const DEFAULT_TITLE = "Data Science Agent — Verifiable AI Data Science";

function stripHtml(raw: string): string {
  return raw.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
}

// Live progress: polls the lightweight /progress endpoint every 3s while the
// run is non-terminal. The backend /events SSE is snapshot-style (dumps and
// closes), so polling is the correct transport. Full state refreshes via
// router.refresh() on phase transitions and terminal states.
function useLiveProgress(runId: string, initialStatus: string) {
  const router = useRouter();
  const [prog, setProg] = React.useState<Progress | null>(null);
  const [live, setLive] = React.useState(!TERMINAL.has(initialStatus.trim().toUpperCase()));
  const [notify, setNotify] = React.useState(false);
  const lastStatus = React.useRef(initialStatus);
  const origTitle = React.useRef(typeof document !== "undefined" ? document.title : DEFAULT_TITLE);

  React.useEffect(() => {
    if (!live) return;
    let stop = false;
    const tick = async () => {
      try {
        const r = await fetch(apiUrl(`/api/v1/analysis/${runId}/progress`), { cache: "no-store" });
        if (!r.ok || stop) return;
        const p = (await r.json()) as Progress;
        setProg(p);
        document.title = `(${p.progress_pct}%) Analysis ${runId.slice(0, 8)} — DSA`;
        const terminal = TERMINAL.has(p.status.trim().toUpperCase());
        if (terminal) {
          setLive(false);
          document.title = origTitle.current || DEFAULT_TITLE;
          if (notify && "Notification" in window && Notification.permission === "granted") {
            new Notification(`Analysis ${p.status}`, { body: `Run ${runId.slice(0, 12)} finished with ${p.evidence} evidence.` });
          }
          router.refresh();
        } else if (p.status !== lastStatus.current) {
          lastStatus.current = p.status;
          router.refresh();
        }
      } catch {
        // Transient network blip — next tick retries.
      }
    };
    void tick();
    const id = setInterval(tick, 3000);
    return () => {
      stop = true;
      clearInterval(id);
      document.title = origTitle.current || DEFAULT_TITLE;
    };
  }, [runId, live, notify, router]);

  const toggleNotify = React.useCallback(async () => {
    if (!notify && "Notification" in window && Notification.permission === "default") {
      await Notification.requestPermission();
    }
    setNotify((v) => !v);
  }, [notify]);

  return { prog, live, notify, toggleNotify };
}

const MACHINE = ["Queued", "Planning", "Executing", "Validating", "Done"];

function machineIndex(status: string, stepsDone: number, hasValidation: boolean): number {
  const s = status.trim().toUpperCase();
  if (s === "COMPLETED") return 4;
  if (s === "PENDING" || s === "QUEUED") return 0;
  if (s === "HUMAN_REVIEW") return 3;
  if (s === "FAILED") return -1;
  if (hasValidation) return 3;
  return stepsDone > 0 ? 2 : 1;
}

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

function ApprovalCard({ runId }: { runId: string }) {
  const router = useRouter();
  const [note, setNote] = React.useState("Approved by human");
  const [busy, setBusy] = React.useState(false);
  const [err, setErr] = React.useState<string | null>(null);

  async function approve() {
    setBusy(true);
    setErr(null);
    try {
      const res = await fetch(apiUrl(`/api/v1/analysis/${runId}/approve`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ note }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = (data as { detail?: unknown }).detail;
        setErr(typeof detail === "string" ? stripHtml(detail).slice(0, 300) : `Approval failed (HTTP ${res.status}).`);
        return;
      }
      router.refresh();
    } catch (e) {
      setErr(`Approval request failed. ${String(e)}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="border-amber-200 bg-amber-50/60">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm"><AlertTriangle className="size-4 text-amber-600" aria-hidden /> Human review requested</CardTitle>
        <CardDescription className="text-xs">This run is paused at a review gate. Approve to mark it COMPLETED.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div>
          <label htmlFor="approval-note" className="block text-xs font-medium text-amber-900">Approval note</label>
          <Input id="approval-note" value={note} onChange={(e) => setNote(e.target.value)} className="mt-1 bg-white" maxLength={300} />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button size="sm" onClick={approve} disabled={busy}>
            {busy ? <><Loader2 className="size-4 animate-spin" aria-hidden /> Approving…</> : <><Check className="size-4" aria-hidden /> Approve run</>}
          </Button>
          {err && <p className="text-xs text-red-600" role="alert">{err}</p>}
        </div>
      </CardContent>
    </Card>
  );
}

function FailureCard({ run }: { run: RunDetail }) {
  const st = run.state;
  const failed = (st?.tool_calls ?? []).filter((tc) => tc.status !== "ok");
  const [copied, setCopied] = React.useState(false);
  if (run.status !== "FAILED" && failed.length === 0) return null;

  async function copyDiagnostics() {
    const payload = JSON.stringify(
      {
        run_id: run.id,
        status: run.status,
        query: run.user_query,
        failures: failed.map((tc) => ({ tool: tc.tool, call_id: tc.call_id, error: tc.error ?? null })),
      },
      null,
      2
    );
    try {
      await navigator.clipboard.writeText(payload);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  }

  return (
    <Card className="border-red-200 bg-red-50/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm text-red-800"><XCircle className="size-4" aria-hidden /> This run failed{failed.length > 0 ? ` — ${failed.length} tool call${failed.length === 1 ? "" : "s"} errored` : ""}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {failed.map((tc) => (
          <div key={tc.call_id} className="rounded-lg border border-red-200 bg-white p-2.5 text-xs leading-5">
            <code className="font-mono font-semibold">{tc.tool}</code>
            <code className="ml-2 font-mono text-zinc-400">{tc.call_id.slice(0, 12)}</code>
            <p className="mt-1 break-words text-red-700">{stripHtml(String(tc.error ?? "Unknown error")).slice(0, 500)}</p>
          </div>
        ))}
        <div className="flex flex-wrap gap-2 pt-1">
          <Button variant="secondary" size="sm" onClick={copyDiagnostics}>
            {copied ? <><Check className="size-3.5" aria-hidden /> Copied</> : <><Copy className="size-3.5" aria-hidden /> Copy diagnostics</>}
          </Button>
          {run.dataset_id && (
            <Link href={`/analysis?dataset=${run.dataset_id}&q=${encodeURIComponent(run.user_query)}`}>
              <Button variant="secondary" size="sm">Rerun with same question →</Button>
            </Link>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function FollowUpBox({ run }: { run: RunDetail }) {
  const router = useRouter();
  const [q, setQ] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [err, setErr] = React.useState<string | null>(null);

  async function submit() {
    setErr(null);
    if (!q.trim()) {
      setErr("Enter a follow-up question.");
      return;
    }
    if (!run.dataset_id) {
      setErr("This run has no linked dataset, so a follow-up cannot be started.");
      return;
    }
    setBusy(true);
    try {
      const res = await fetch(apiUrl("/api/v1/analysis/"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dataset_id: run.dataset_id, user_query: q }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = (data as { detail?: unknown }).detail ?? data;
        setErr(typeof detail === "string" ? stripHtml(detail).slice(0, 300) : "Follow-up could not start.");
        return;
      }
      router.push(`/analysis/${(data as { id: string }).id}?from=${run.id}`);
    } catch (e) {
      setErr(`Follow-up could not start. ${String(e)}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Ask a follow-up</CardTitle>
        <CardDescription className="text-xs">Runs on the same dataset — the new run links back here as its parent.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        <label htmlFor="followup" className="sr-only">Follow-up question</label>
        <textarea
          id="followup"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          rows={2}
          maxLength={2000}
          placeholder="e.g. Now break that down by the largest group…"
          className="flex min-h-[64px] w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm leading-6 shadow-sm placeholder:text-zinc-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400"
        />
        <div className="flex flex-wrap items-center gap-2">
          <Button size="sm" onClick={submit} disabled={busy}>
            {busy ? <><Loader2 className="size-4 animate-spin" aria-hidden /> Starting…</> : <><Send className="size-4" aria-hidden /> Run follow-up</>}
          </Button>
          {err && <p className="text-xs text-red-600" role="alert">{err}</p>}
        </div>
      </CardContent>
    </Card>
  );
}

export function RunInspector({ run, reportUrl, fromRunId }: { run: RunDetail; reportUrl: string; fromRunId?: string }) {
  const st = run.state;
  const [copied, setCopied] = React.useState(false);
  const [traceFilter, setTraceFilter] = React.useState<"all" | "ok" | "error">("all");
  const [traceQuery, setTraceQuery] = React.useState("");
  const validations = st?.validation_results ?? [];
  const passed = validations.filter((v) => v.passed).length;
  const { prog, live, notify, toggleNotify } = useLiveProgress(run.id, run.status);
  const statusNow = prog?.status ?? run.status;
  const stepsDone = prog?.steps_done ?? st?.tool_calls.length ?? 0;
  const stepsTotal = prog?.steps_total ?? st?.plan.length ?? 0;
  const isReview = statusNow.trim().toUpperCase() === "HUMAN_REVIEW";

  const toolCalls = React.useMemo(() => {
    const all = st?.tool_calls ?? [];
    return all.filter((tc) => {
      if (traceFilter === "ok" && tc.status !== "ok") return false;
      if (traceFilter === "error" && tc.status === "ok") return false;
      if (traceQuery && !tc.tool.toLowerCase().includes(traceQuery.toLowerCase())) return false;
      return true;
    });
  }, [st?.tool_calls, traceFilter, traceQuery]);
  const maxDuration = Math.max(1, ...(st?.tool_calls ?? []).map((tc) => tc.duration_ms));

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

  const mi = machineIndex(statusNow, stepsDone, validations.length > 0);

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Step 3 · Inspect the evidence"
        title={`Analysis ${run.id.slice(0, 12)}`}
        description={`Objective: ${st?.objective || run.user_query}`}
        actions={
          <>
            <StatusBadge status={statusNow} />
            {st?.report_markdown && (
              <a href={reportUrl} target="_blank" rel="noreferrer">
                <Button variant="secondary" size="sm"><Download className="size-4" aria-hidden /> Download report</Button>
              </a>
            )}
          </>
        }
      />

      {fromRunId && (
        <p className="rounded-xl border border-zinc-200 bg-white px-4 py-2.5 text-xs text-zinc-600 shadow-sm">
          Follow-up of <Link href={`/analysis/${fromRunId}`} className="font-mono font-medium text-zinc-900 underline">run-{fromRunId.slice(0, 12)}</Link>
          {" · "}<Link href={`/analysis/${fromRunId}`} className="underline">View parent trace →</Link>
        </p>
      )}

      {(live || isReview) && (
        <Card aria-live="polite">
          <CardContent className="space-y-2.5 p-4 pt-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-medium">
                {isReview ? "Paused for human review" : <>Running… step {Math.min(stepsDone + 1, Math.max(stepsTotal, 1))} of {Math.max(stepsTotal, 1)}</>}
              </p>
              <div className="flex items-center gap-3">
                <span className="text-xs tabular-nums text-zinc-500">
                  {prog ? `${prog.progress_pct}% · ${prog.evidence} evidence · ${prog.insights} insights` : "Connecting to live progress…"}
                </span>
                <button
                  type="button"
                  onClick={toggleNotify}
                  aria-pressed={notify}
                  title={notify ? "Notification on completion: on" : "Notify me when done"}
                  className="inline-flex items-center gap-1 rounded-lg border border-zinc-200 px-2 py-1 text-xs text-zinc-600 hover:bg-zinc-50"
                >
                  {notify ? <Bell className="size-3.5" aria-hidden /> : <BellOff className="size-3.5" aria-hidden />}
                  {notify ? "Notifying" : "Notify me"}
                </button>
              </div>
            </div>
            <Progress value={prog?.progress_pct ?? 0} aria-label="Run progress" />
            <ol className="flex flex-wrap items-center gap-1.5" aria-label="Run phase">
              {MACHINE.map((m, i) => (
                <li key={m} className="flex items-center gap-1.5">
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${i < mi ? "bg-emerald-50 text-emerald-700" : i === mi ? "bg-amber-50 text-amber-800" : "bg-zinc-100 text-zinc-500"}`}>
                    {i < mi ? "✓ " : ""}{m}
                  </span>
                  {i < MACHINE.length - 1 && <span aria-hidden className="text-zinc-300">→</span>}
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>
      )}

      {isReview && <ApprovalCard runId={run.id} />}
      <FailureCard run={run} />

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
            <CardContent className="space-y-3 p-3 pt-3 sm:p-4 sm:pt-4">
              <div className="flex flex-wrap items-center gap-2">
                <div role="group" aria-label="Filter by status" className="inline-flex rounded-lg bg-zinc-100 p-1 text-xs font-medium">
                  {(["all", "ok", "error"] as const).map((f) => (
                    <button
                      key={f}
                      type="button"
                      onClick={() => setTraceFilter(f)}
                      aria-pressed={traceFilter === f}
                      className={`rounded-md px-3 py-1 capitalize ${traceFilter === f ? "bg-white text-zinc-900 shadow-sm" : "text-zinc-500 hover:text-zinc-900"}`}
                    >
                      {f === "ok" ? "OK" : f === "error" ? "Errors" : "All"}
                    </button>
                  ))}
                </div>
                <label htmlFor="trace-search" className="sr-only">Search tools</label>
                <Input
                  id="trace-search"
                  value={traceQuery}
                  onChange={(e) => setTraceQuery(e.target.value)}
                  placeholder="Search tools…"
                  className="h-8 w-44"
                />
                <span className="text-xs text-zinc-400" aria-live="polite">{toolCalls.length} of {st?.tool_calls.length ?? 0} calls</span>
              </div>
              {(st?.tool_calls.length ?? 0) === 0 ? (
                <EmptyState title="No tool calls" description="This run has no recorded tool executions yet." />
              ) : toolCalls.length === 0 ? (
                <EmptyState title="No calls match" description="Adjust the status filter or search text." />
              ) : (
                <TableWrapper>
                  <Table>
                    <caption className="sr-only">Agent tool calls</caption>
                    <TableHeader>
                      <TableRow><TableHead>Tool</TableHead><TableHead>Status</TableHead><TableHead>Duration</TableHead><TableHead>Call ID</TableHead><TableHead /></TableRow>
                    </TableHeader>
                    <TableBody>
                      {toolCalls.map((tc) => (
                        <React.Fragment key={tc.call_id}>
                          <TableRow>
                            <TableCell><code className="font-mono text-xs">{tc.tool}</code></TableCell>
                            <TableCell>
                              <Badge variant={tc.status === "ok" ? "success" : "destructive"}>{tc.status}</Badge>
                            </TableCell>
                            <TableCell>
                              <span className="flex items-center gap-2">
                                <span className="h-1.5 w-14 overflow-hidden rounded-full bg-zinc-100" aria-hidden>
                                  <span className="block h-full rounded-full bg-zinc-700" style={{ width: `${Math.round((tc.duration_ms / maxDuration) * 100)}%` }} />
                                </span>
                                <span className="tabular-nums">{tc.duration_ms}ms</span>
                              </span>
                            </TableCell>
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

      <FollowUpBox run={run} />

      <p className="text-xs text-zinc-400">
        Full trace via <code className="font-mono">GET /api/v1/analysis/{run.id}</code> · Evidence graph at{" "}
        <code className="font-mono">/evidence/{"{evidence_id}"}</code> · <Link href="/runs" className="underline">All runs</Link>
      </p>
    </div>
  );
}
