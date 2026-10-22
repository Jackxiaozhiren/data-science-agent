"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertTriangle, CheckCircle2, Copy, Check, Download, ChevronDown, FileText, FileJson, TerminalSquare, BookOpen, XCircle, Send, Loader2, Bell, BellOff } from "lucide-react";
import { clientFetch, apiUrl, classifyResponse, failurePresentation, type ApiFailure } from "@/lib/api";
import { callStatusLabel, checkLabel, t } from "@/lib/locale";
import { useLocale } from "@/app/lib/LocaleProvider";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/app/components/ui/card";
import { Badge } from "@/app/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/app/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow, TableWrapper } from "@/app/components/ui/table";
import { Input } from "@/app/components/ui/input";
import { Progress, Separator } from "@/app/components/ui/feedback";
import { PageHeader } from "@/app/components/data/PageHeader";
import { StatusBadge } from "@/app/components/data/StatusBadge";
import { ReasoningModeBadge, ReasoningModeNotice } from "@/app/components/analysis/ReasoningModeBadge";
import { EmptyState } from "@/app/components/data/States";
import { TraceTimeline } from "@/app/components/data/TraceTimeline";
import { ConfidenceBars } from "@/app/components/ui/chart";
import { Markdown } from "@/app/components/data/Markdown";
import { isInFlightStatus, isReviewStatus, TERMINAL_STATUSES } from "@/app/lib/analysisStatus";
import { limitationSeverity, limitationText } from "@/app/lib/limitations";

export type RunDetail = {
  id: string;
  status: string;
  user_query: string;
  dataset_id: string;
  error?: string | null;
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

const TERMINAL = new Set<string>(TERMINAL_STATUSES);

function stripHtml(raw: string): string {
  return raw.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
}

// Live progress: polls the lightweight /progress endpoint every 3s while the
// run is non-terminal. /events became a live stream when the run stopped
// blocking its own create call (R-03), but a poll is the transport that
// survives a buffering proxy and costs one small row read; the stream is for
// clients that want the event sequence itself. Full state refreshes via
// router.refresh() on phase transitions and terminal states.
function useLiveProgress(runId: string, initialStatus: string) {
  const locale = useLocale();
  const router = useRouter();
  const [prog, setProg] = React.useState<Progress | null>(null);
  const [live, setLive] = React.useState(!TERMINAL.has(initialStatus.trim().toUpperCase()));
  const [notify, setNotify] = React.useState(false);
  const [notifyBlocked, setNotifyBlocked] = React.useState(false);
  const lastStatus = React.useRef(initialStatus);
  // The title this page had before the poll started rewriting it. The fallback is the dictionary's own
  // product title, not a second copy of it -- the sweep in tests/contract/test_web_locale_parity.py refuses a
  // page that keeps its own version of a sentence the locale owner has.
  const origTitle = React.useRef(
    typeof document !== "undefined" ? document.title : t(locale, "meta.title")
  );

  React.useEffect(() => {
    if (!live) return;
    let stop = false;
    const tick = async () => {
      try {
        const r = await clientFetch(`/api/v1/analysis/${runId}/progress`, { cache: "no-store" });
        if (!r.ok || stop) return;
        const p = (await r.json()) as Progress;
        setProg(p);
        document.title = t(locale, "run.liveTitle")
          .replace("{pct}", String(p.progress_pct))
          .replace("{id}", runId.slice(0, 8));
        const terminal = TERMINAL.has(p.status.trim().toUpperCase());
        if (terminal) {
          setLive(false);
          document.title = origTitle.current || t(locale, "meta.title");
          if (notify && "Notification" in window && Notification.permission === "granted") {
            new Notification(t(locale, "run.notifyTitle").replace("{status}", p.status), {
              body: t(locale, "run.notifyBody")
                .replace("{id}", runId.slice(0, 12))
                .replace("{evidence}", String(p.evidence)),
            });
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
      document.title = origTitle.current || t(locale, "meta.title");
    };
  }, [runId, live, notify, router, locale]);

  const toggleNotify = React.useCallback(async () => {
    if (notify) {
      setNotify(false);
      return;
    }
    // The control must not claim a delivery the browser will refuse. `requestPermission()` resolves to
    // "denied" wherever the visitor dismissed the prompt or the context forbids notifications -- and headless
    // or permission-policy-restricted browsers resolve it without ever showing a prompt -- so the *result*,
    // never the click, decides whether this reads as on. A denied visitor gets the reason, not a bell that
    // will stay quiet until the run finishes.
    if (typeof window === "undefined" || !("Notification" in window)) {
      setNotifyBlocked(true);
      return;
    }
    let permission: NotificationPermission = Notification.permission;
    if (permission !== "granted") {
      permission = await Notification.requestPermission().catch(() => "denied" as NotificationPermission);
    }
    if (permission !== "granted") {
      setNotifyBlocked(true);
      return;
    }
    setNotifyBlocked(false);
    setNotify(true);
  }, [notify]);

  return { prog, live, notify, notifyBlocked, toggleNotify };
}

// The five stage names a reader sees under the status badge. They are the interface's words for where a
// run is, not the API's status tokens -- those stay untranslated in the badge and the JSON.
const MACHINE = ["insp.machineQueued", "insp.machinePlanning", "insp.machineExecuting",
  "insp.machineValidating", "insp.machineDone"];


function machineIndex(status: string, stepsDone: number, hasValidation: boolean): number {
  const s = status.trim().toUpperCase();
  if (s === "COMPLETED") return 4;
  if (isInFlightStatus(status) && (s === "UNDERSTANDING" || s === "PLANNING" || s === "DATA_PROFILING")) return 0;
  if (isReviewStatus(status) || s === "VALIDATION" || s === "SYNTHESIS") return 3;
  if (s === "FAILED") return -1;
  if (hasValidation) return 3;
  return stepsDone > 0 ? 2 : 1;
}

function ValidationRing({ passed, total }: { passed: number; total: number }) {
  const locale = useLocale();
  const pct = total === 0 ? 0 : Math.round((passed / total) * 100);
  const r = 26;
  const c = 2 * Math.PI * r;
  return (
    <div className="flex items-center gap-3" role="img" aria-label={t(locale, "insp.validationAria").replace("{passed}", String(passed)).replace("{total}", String(total)).replace("{pct}", String(pct))}>
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
        <p className="text-sm font-semibold">{t(locale, "insp.checksPassed").replace("{passed}", String(passed)).replace("{total}", String(total))}</p>
        <p className="text-xs text-zinc-500">{t(locale, "insp.validationSub")}</p>
      </div>
    </div>
  );
}

function ApprovalCard({ runId }: { runId: string }) {
  const locale = useLocale();
  const router = useRouter();
  const [note, setNote] = React.useState(t(locale, "insp.approvalNote"));
  const [busy, setBusy] = React.useState(false);
  const [err, setErr] = React.useState<string | null>(null);

  async function approve() {
    setBusy(true);
    setErr(null);
    try {
      const res = await clientFetch(`/api/v1/analysis/${runId}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ note }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = (data as { detail?: unknown }).detail;
        setErr(
          typeof detail === "string"
            ? stripHtml(detail).slice(0, 300)
            : t(locale, "run.approvalFailed").replace("{status}", String(res.status))
        );
        return;
      }
      router.refresh();
    } catch (e) {
      setErr(t(locale, "run.approvalUnavailable").replace("{detail}", String(e)));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="border-amber-200 bg-amber-50/60">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm"><AlertTriangle className="size-4 text-amber-600" aria-hidden /> {t(locale, "insp.reviewTitle")}</CardTitle>
        <CardDescription className="text-xs">{t(locale, "insp.reviewBody")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div>
          <label htmlFor="approval-note" className="block text-xs font-medium text-amber-900">{t(locale, "insp.approvalLabel")}</label>
          <Input id="approval-note" value={note} onChange={(e) => setNote(e.target.value)} className="mt-1 bg-white" maxLength={300} />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button size="sm" onClick={approve} disabled={busy}>
            {busy ? <><Loader2 className="size-4 animate-spin" aria-hidden /> {t(locale, "insp.approving")}</> : <><Check className="size-4" aria-hidden /> {t(locale, "insp.approve")}</>}
          </Button>
          {err && <p className="text-xs text-red-600" role="alert">{err}</p>}
        </div>
      </CardContent>
    </Card>
  );
}

function FailureCard({ run }: { run: RunDetail }) {
  const locale = useLocale();
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
        error: run.error ?? null,
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
        <CardTitle className="flex items-center gap-2 text-sm text-red-800"><XCircle className="size-4" aria-hidden /> {t(locale, "insp.runFailed")}
          {failed.length > 0
            ? ` ${t(locale, failed.length === 1 ? "insp.failedCallsOne" : "insp.failedCallsMany").replace("{n}", String(failed.length))}`
            : ""}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {run.error && (
          <p className="rounded-lg border border-red-200 bg-white p-2.5 text-xs leading-5">
            <strong>{t(locale, "insp.colReason")}</strong>
            <span className="ml-1 break-words text-red-700">{stripHtml(String(run.error)).slice(0, 500)}</span>
          </p>
        )}
        {failed.map((tc) => (
          <div key={tc.call_id} className="rounded-lg border border-red-200 bg-white p-2.5 text-xs leading-5">
            <code className="font-mono font-semibold">{tc.tool}</code>
            <code className="ml-2 font-mono text-zinc-400">{tc.call_id.slice(0, 12)}</code>
            <p className="mt-1 break-words text-red-700">{stripHtml(String(tc.error ?? t(locale, "insp.unknownError"))).slice(0, 500)}</p>
          </div>
        ))}
        <div className="flex flex-wrap gap-2 pt-1">
          <Button variant="secondary" size="sm" onClick={copyDiagnostics}>
            {copied ? <><Check className="size-3.5" aria-hidden /> {t(locale, "insp.copied")}</> : <><Copy className="size-3.5" aria-hidden /> {t(locale, "insp.copyDiagnostics")}</>}
          </Button>
          {run.dataset_id && (
            <Link href={`/analysis?dataset=${run.dataset_id}&q=${encodeURIComponent(run.user_query)}`}>
              <Button variant="secondary" size="sm">{t(locale, "insp.rerun")}</Button>
            </Link>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function FollowUpBox({ run }: { run: RunDetail }) {
  const locale = useLocale();
  const router = useRouter();
  const [q, setQ] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [err, setErr] = React.useState<string | null>(null);

  async function submit() {
    setErr(null);
    if (!q.trim()) {
      setErr(t(locale, "insp.followupEmpty"));
      return;
    }
    if (!run.dataset_id) {
      setErr(t(locale, "insp.noDatasetFollowup"));
      return;
    }
    setBusy(true);
    try {
      const res = await clientFetch("/api/v1/analysis/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dataset_id: run.dataset_id, user_query: q }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = (data as { detail?: unknown }).detail ?? data;
        setErr(typeof detail === "string" ? stripHtml(detail).slice(0, 300) : t(locale, "insp.followupFailed"));
        return;
      }
      router.push(`/analysis/${(data as { id: string }).id}?from=${run.id}`);
    } catch (e) {
      setErr(t(locale, "insp.followupUnavailable").replace("{detail}", String(e)));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">{t(locale, "insp.followupTitle")}</CardTitle>
        <CardDescription className="text-xs">{t(locale, "insp.followupBody")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        <label htmlFor="followup" className="sr-only">{t(locale, "insp.followupLabel")}</label>
        <textarea
          id="followup"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          rows={2}
          maxLength={2000}
          placeholder={t(locale, "insp.followupPh")}
          className="flex min-h-[64px] w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm leading-6 shadow-sm placeholder:text-zinc-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400"
        />
        <div className="flex flex-wrap items-center gap-2">
          <Button size="sm" onClick={submit} disabled={busy}>
            {busy ? <><Loader2 className="size-4 animate-spin" aria-hidden /> {t(locale, "insp.starting")}</> : <><Send className="size-4" aria-hidden /> {t(locale, "insp.runFollowup")}</>}
          </Button>
          {err && <p className="text-xs text-red-600" role="alert">{err}</p>}
        </div>
      </CardContent>
    </Card>
  );
}

export function RunInspector({ run, reportUrl, findingsUrl, htmlUrl, fromRunId }: { run: RunDetail; reportUrl: string; findingsUrl?: string; htmlUrl?: string; fromRunId?: string }) {
  const locale = useLocale();
  const shared = failurePresentation(locale);
  const st = run.state;
  const [copied, setCopied] = React.useState(false);
  const [traceFilter, setTraceFilter] = React.useState<"all" | "ok" | "error">("all");
  const [traceQuery, setTraceQuery] = React.useState("");
  const [tab, setTab] = React.useState("overview");
  const [highlightCall, setHighlightCall] = React.useState<string | null>(null);
  const [highlightEvidence, setHighlightEvidence] = React.useState<string | null>(null);
  const validations = st?.validation_results ?? [];
  const passed = validations.filter((v) => v.passed).length;
  const limitations = (st?.insights ?? []).filter((i) => i.limitation);
  const severeCount = limitations.filter((i) => limitationSeverity(i.limitation ?? "") === "error").length;
  const { prog, live, notify, notifyBlocked, toggleNotify } = useLiveProgress(run.id, run.status);
  const statusNow = prog?.status ?? run.status;
  const stepsDone = prog?.steps_done ?? st?.tool_calls.length ?? 0;
  const stepsTotal = prog?.steps_total ?? st?.plan.length ?? 0;
  const isReview = isReviewStatus(statusNow);

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
  // Reverse index: tool call_id -> evidence ids citing it (for trace→evidence links).
  const callToEvidence = React.useMemo(() => {
    const m = new Map<string, string[]>();
    for (const ev of st?.evidence ?? []) {
      const arr = m.get(ev.source_id) ?? [];
      arr.push(ev.id);
      m.set(ev.source_id, arr);
    }
    return m;
  }, [st?.evidence]);

  // Cross-tab jump with 2s highlight + scroll into view.
  function jumpToCall(callId: string) {
    setTab("trace");
    setTraceFilter("all");
    setTraceQuery("");
    setHighlightCall(callId);
    setTimeout(() => setHighlightCall((cur) => (cur === callId ? null : cur)), 2000);
  }
  function jumpToEvidence(evId: string) {
    setTab("evidence");
    setHighlightEvidence(evId);
    setTimeout(() => setHighlightEvidence((cur) => (cur === evId ? null : cur)), 2000);
  }
  React.useEffect(() => {
    const id = highlightCall ? `tc-${CSS.escape(highlightCall)}` : highlightEvidence ? `ev-${CSS.escape(highlightEvidence)}` : null;
    if (!id) return;
    // Wait a tick for the tab panel to mount before scrolling.
    const t = setTimeout(() => {
      document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 60);
    return () => clearTimeout(t);
  }, [highlightCall, highlightEvidence, tab]);

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

  function downloadReport() {
    if (!st?.report_markdown) return;
    const blob = new Blob([st.report_markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `dsa-report-${run.id.slice(0, 12)}.md`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  const [bundle, setBundle] = React.useState<"idle" | "sending" | "saved" | ApiFailure>("idle");

  async function downloadBundle() {
    setBundle("sending");
    try {
      const res = await clientFetch(`/api/v1/analysis/${run.id}/bundle`, { cache: "no-store" });
      const failure = classifyResponse(res);
      if (failure) {
        setBundle(failure);
        return;
      }
      const url = URL.createObjectURL(await res.blob());
      const a = document.createElement("a");
      a.href = url;
      a.download = `${run.id}-bundle.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      setBundle("saved");
    } catch {
      setBundle("transport");
    }
  }

  // Artifacts grouped by kind. The stored paths are server-local and there is no per-file serving route,
  // so the honest action on a row is copy-path, not a fake link; the whole set leaves through
  // /bundle below, which is the only thing a visitor can keep when the host's filesystem is not durable.
  const artifactGroups = React.useMemo(() => {
    const groups = new Map<string, NonNullable<RunDetail["state"]>["artifacts"]>();
    for (const a of st?.artifacts ?? []) {
      const kind = String(a.metadata?.kind ?? a.type ?? "other");
      const arr = groups.get(kind) ?? [];
      arr.push(a);
      groups.set(kind, arr);
    }
    return [...groups.entries()];
  }, [st?.artifacts]);

  function kindIcon(kind: string) {
    if (kind.includes("markdown") || kind === "report") return FileText;
    if (kind.includes("json") || kind.includes("experiment") || kind.includes("evidence")) return FileJson;
    if (kind.includes("reproduce") || kind.includes("script") || kind.endsWith(".sh")) return TerminalSquare;
    if (kind.includes("notebook") || kind.includes("ipynb")) return BookOpen;
    return FileText;
  }

  const mi = machineIndex(statusNow, stepsDone, validations.length > 0);

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow={t(locale, "analysis.eyebrow")}
        title={t(locale, "insp.analysisTitle").replace("{id}", run.id.slice(0, 12))}
        description={t(locale, "insp.objectivePrefix").replace("{value}", st?.objective || run.user_query)}
        actions={
          <>
            <StatusBadge status={statusNow} />
            <ReasoningModeBadge />
            {st?.report_markdown && (
              <a href={reportUrl} target="_blank" rel="noreferrer">
                <Button variant="secondary" size="sm"><Download className="size-4" aria-hidden /> {t(locale, "insp.downloadReport")}</Button>
              </a>
            )}
            {st?.report_markdown && findingsUrl && (
              <a href={findingsUrl} target="_blank" rel="noreferrer">
                <Button
                  variant="secondary"
                  size="sm"
                  title={t(locale, "insp.plainTitle")}
                >
                  <Download className="size-4" aria-hidden /> {t(locale, "insp.downloadPlain")}
                </Button>
              </a>
            )}
            {st?.report_markdown && htmlUrl && (
              <a href={htmlUrl} target="_blank" rel="noreferrer">
                <Button
                  variant="secondary"
                  size="sm"
                  title={t(locale, "insp.offlineTitle")}
                >
                  <Download className="size-4" aria-hidden /> {t(locale, "insp.downloadOffline")}
                </Button>
              </a>
            )}
            <Button
              variant="secondary"
              size="sm"
              onClick={downloadBundle}
              disabled={bundle === "sending"}
              title={t(locale, "insp.bundleTitle")}
            >
              {bundle === "sending" ? (
                <Loader2 className="size-4 animate-spin" aria-hidden />
              ) : (
                <Download className="size-4" aria-hidden />
              )}{" "}
              {t(locale, "insp.downloadBundle")}
            </Button>
          </>
        }
      />

      <ReasoningModeNotice />

      {bundle !== "idle" && bundle !== "sending" && (
        <p
          role="status"
          aria-live="polite"
          className={`rounded-xl border px-4 py-2.5 text-xs shadow-sm ${
            bundle === "saved"
              ? "border-zinc-200 bg-white text-zinc-600"
              : "border-amber-200 bg-amber-50/60 text-amber-900"
          }`}
        >
          {bundle === "saved"
            ? t(locale, "run.bundleSaved")
            : bundle === "notFound"
              ? t(locale, "run.bundleUnavailable").replace("{line}", shared.notFound)
              : shared[bundle]}
        </p>
      )}

      {fromRunId && (
        <p className="rounded-xl border border-zinc-200 bg-white px-4 py-2.5 text-xs text-zinc-600 shadow-sm">
          {t(locale, "insp.followupOf")} <Link href={`/analysis/${fromRunId}`} className="font-mono font-medium text-zinc-900 underline">{fromRunId}</Link>
          {" · "}<Link href={`/analysis/${fromRunId}`} className="underline">{t(locale, "insp.viewParent")}</Link>
        </p>
      )}

      {(live || isReview) && (
        <Card aria-live="polite">
          <CardContent className="space-y-2.5 p-4 pt-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-medium">
                {isReview ? (
                  t(locale, "insp.pausedReview")
                ) : (
                  <>
                    {t(locale, "insp.runningStep")
                      .replace("{done}", String(Math.min(stepsDone + 1, Math.max(stepsTotal, 1))))
                      .replace("{total}", String(Math.max(stepsTotal, 1)))}
                  </>
                )}
              </p>
              <div className="flex items-center gap-3">
                <span className="text-xs tabular-nums text-zinc-500">
                  {prog
                    ? t(locale, "insp.liveProgress")
                        .replace("{pct}", String(prog.progress_pct))
                        .replace("{evidence}", String(prog.evidence))
                        .replace("{insights}", String(prog.insights))
                    : t(locale, "insp.liveConnecting")}
                </span>
                <button
                  type="button"
                  onClick={toggleNotify}
                  aria-pressed={notify}
                  title={
                    notifyBlocked
                      ? t(locale, "insp.notifyBlockedWhy")
                      : notify
                        ? t(locale, "insp.notifyAriaOn")
                        : t(locale, "insp.notifyAriaOff")
                  }
                  className="inline-flex items-center gap-1 rounded-lg border border-zinc-200 px-2 py-1 text-xs text-zinc-600 hover:bg-zinc-50"
                >
                  {notify ? <Bell className="size-3.5" aria-hidden /> : <BellOff className="size-3.5" aria-hidden />}
                  {notifyBlocked
                    ? t(locale, "insp.notifyBlocked")
                    : notify
                      ? t(locale, "insp.notifying")
                      : t(locale, "insp.notify")}
                </button>
              </div>
            </div>
            <Progress value={prog?.progress_pct ?? 0} aria-label={t(locale, "insp.progressAria")} />
            <ol className="flex flex-wrap items-center gap-1.5" aria-label={t(locale, "insp.phaseAria")}>
              {MACHINE.map((m, i) => (
                <li key={m} className="flex items-center gap-1.5">
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${i < mi ? "bg-emerald-50 text-emerald-700" : i === mi ? "bg-amber-50 text-amber-800" : "bg-zinc-100 text-zinc-500"}`}>
                    {i < mi ? "✓ " : ""}{t(locale, m)}
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

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="overview">{t(locale, "insp.tabOverview")}</TabsTrigger>
          <TabsTrigger value="trace">{t(locale, "insp.tabTrace").replace("{n}", String(st?.tool_calls.length ?? 0))}</TabsTrigger>
          <TabsTrigger value="evidence">{t(locale, "insp.tabEvidence").replace("{n}", String(st?.evidence.length ?? 0))}</TabsTrigger>
          <TabsTrigger value="insights">{t(locale, "insp.tabInsights").replace("{n}", String(st?.insights.length ?? 0))}</TabsTrigger>
          <TabsTrigger value="artifacts">{t(locale, "insp.tabArtifacts")}</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          {limitations.length > 0 && (
            <button
              type="button"
              onClick={() => setTab("insights")}
              className={`mb-4 flex w-full items-center gap-2 rounded-xl border p-3 text-left text-xs leading-5 shadow-sm ${severeCount > 0 ? "border-red-200 bg-red-50/60 text-red-800" : "border-amber-200 bg-amber-50/60 text-amber-800"}`}
            >
              <AlertTriangle className="size-4 shrink-0" aria-hidden />
              <span>
                <strong>
                  {t(locale, limitations.length === 1 ? "insp.caveatOne" : "insp.caveatMany").replace("{n}", String(limitations.length))}
                  {severeCount > 0 ? t(locale, "insp.criticalSuffix").replace("{n}", String(severeCount)) : ""}
                </strong>
                {t(locale, "insp.caveatTail")}
              </span>
            </button>
          )}
          <div className="grid items-start gap-4 lg:grid-cols-[1.2fr_0.8fr]">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">{t(locale, "insp.planTitle")}</CardTitle>
                <CardDescription className="text-xs">{t(locale, "insp.planSub")}</CardDescription>
              </CardHeader>
              <CardContent>
                <TraceTimeline locale={locale}
                  steps={(st?.plan ?? []).map((s, i) => ({
                    id: s.id, name: s.name, tool: s.tool, description: s.description,
                    status: run.status === "COMPLETED" || i < stepsDone
                      ? "done"
                      : isInFlightStatus(run.status) && i === stepsDone
                        ? "active"
                        : "todo",
                  }))}
                />
              </CardContent>
            </Card>
            <div className="space-y-4">
              <Card>
                <CardHeader><CardTitle className="text-sm">{t(locale, "insp.validationTitle")}</CardTitle></CardHeader>
                <CardContent className="space-y-3">
                  <ValidationRing passed={passed} total={validations.length} />
                  <Separator />
                  <ul className="space-y-1.5 text-sm">
                    {validations.length === 0 && <li className="text-xs text-zinc-500">{t(locale, "insp.noValidation")}</li>}
                    {validations.map((v, i) => (
                      <li key={i} className={`flex items-start gap-2 text-xs leading-5 ${v.passed ? "text-emerald-700" : "text-red-600"}`}>
                        {v.passed ? <CheckCircle2 className="mt-0.5 size-3.5 shrink-0" aria-hidden /> : <XCircle className="mt-0.5 size-3.5 shrink-0" aria-hidden />}
                        <span><strong>{checkLabel(locale, v.check)}:</strong> {v.message}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="grid grid-cols-3 gap-2 p-4 pt-4 text-center">
                  {[
                    { v: String(st?.tool_calls.length ?? 0), l: t(locale, "insp.statToolCalls") },
                    { v: String(st?.evidence.length ?? 0), l: t(locale, "insp.statEvidence") },
                    { v: String(st?.artifacts.length ?? 0), l: t(locale, "insp.statArtifacts") },
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
                <div role="group" aria-label={t(locale, "insp.filterAria")} className="inline-flex rounded-lg bg-zinc-100 p-1 text-xs font-medium">
                  {(["all", "ok", "error"] as const).map((f) => (
                    <button
                      key={f}
                      type="button"
                      onClick={() => setTraceFilter(f)}
                      aria-pressed={traceFilter === f}
                      className={`rounded-md px-3 py-1 capitalize ${traceFilter === f ? "bg-white text-zinc-900 shadow-sm" : "text-zinc-500 hover:text-zinc-900"}`}
                    >
                      {t(locale, f === "ok" ? "insp.filterOk" : f === "error" ? "insp.filterErrors" : "insp.filterAll")}
                    </button>
                  ))}
                </div>
                <label htmlFor="trace-search" className="sr-only">{t(locale, "insp.searchLabel")}</label>
                <Input
                  id="trace-search"
                  value={traceQuery}
                  onChange={(e) => setTraceQuery(e.target.value)}
                  placeholder={t(locale, "insp.searchPh")}
                  className="h-8 w-44"
                />
                <span className="text-xs text-zinc-400" aria-live="polite">{t(locale, "insp.callsProgress").replace("{shown}", String(toolCalls.length)).replace("{total}", String(st?.tool_calls.length ?? 0))}</span>
              </div>
              {(st?.tool_calls.length ?? 0) === 0 ? (
                <EmptyState title={t(locale, "insp.noToolsTitle")} description={t(locale, "insp.noToolsBody")} />
              ) : toolCalls.length === 0 ? (
                <EmptyState title={t(locale, "insp.noMatchTitle")} description={t(locale, "insp.noMatchBody")} />
              ) : (
                <TableWrapper>
                  <Table>
                    <caption className="sr-only">{t(locale, "insp.toolCallsCaption")}</caption>
                    <TableHeader>
                      <TableRow><TableHead>{t(locale, "insp.colTool")}</TableHead><TableHead>{t(locale, "insp.colStatus")}</TableHead><TableHead>{t(locale, "insp.colDuration")}</TableHead><TableHead>{t(locale, "insp.colCallId")}</TableHead><TableHead /></TableRow>
                    </TableHeader>
                    <TableBody>
                      {toolCalls.map((tc) => (
                        <React.Fragment key={tc.call_id}>
                          <TableRow
                            id={`tc-${tc.call_id}`}
                            className={highlightCall === tc.call_id ? "bg-amber-50" : undefined}
                          >
                            <TableCell><code className="font-mono text-xs">{tc.tool}</code></TableCell>
                            <TableCell>
                              <Badge variant={tc.status === "ok" ? "success" : "destructive"}>{callStatusLabel(locale, tc.status)}</Badge>
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
                              {(callToEvidence.get(tc.call_id) ?? []).length > 0 && (
                                <span className="mb-1 flex flex-wrap gap-1">
                                  {(callToEvidence.get(tc.call_id) ?? []).map((eid) => (
                                    <button
                                      key={eid}
                                      type="button"
                                      onClick={() => jumpToEvidence(eid)}
                                      title={t(locale, "insp.viewEvidenceTitle").replace("{eid}", eid)}
                                      className="rounded bg-emerald-50 px-1.5 py-0.5 font-mono text-[11px] text-emerald-700 hover:bg-emerald-100"
                                    >
                                      {eid}
                                    </button>
                                  ))}
                                </span>
                              )}
                              <details>
                                <summary className="inline-flex cursor-pointer items-center gap-1 text-xs font-medium text-zinc-600 hover:text-zinc-900">
                                  <ChevronDown className="size-3" aria-hidden /> {t(locale, "insp.ioSummary")}
                                </summary>
                                <div className="mt-2 space-y-2">
                                  <div>
                                    <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">{t(locale, "insp.colInput")}</p>
                                    <pre className="mt-1 max-h-48 overflow-auto rounded-lg bg-zinc-950 p-2 font-mono text-[11px] leading-5 text-zinc-200">{JSON.stringify(tc.input, null, 2)}</pre>
                                  </div>
                                  <div>
                                    <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">{t(locale, "insp.outputLabel")}{tc.error ? t(locale, "insp.outputErrorSuffix") : ""}</p>
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
              <EmptyState title={t(locale, "insp.noEvidenceTitle")} description={t(locale, "insp.noEvidenceBody")} />
            )}
            <ul className="grid gap-3">
              {(st?.evidence ?? []).map((ev) => (
                <li key={ev.id} id={`ev-${ev.id}`} className="scroll-mt-24">
                  <Card className={highlightEvidence === ev.id ? "border-amber-300 bg-amber-50/50" : undefined}>
                    <CardContent className="space-y-2 p-4 pt-4">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <code className="font-mono text-xs text-zinc-500">{ev.id} · {ev.source_type} → {ev.source_id}</code>
                        <span className="flex items-center gap-2">
                          <span className="text-xs font-medium tabular-nums text-emerald-700">{t(locale, "insp.confidence").replace("{value}", ev.confidence.toFixed(2))}</span>
                          {(callToEvidence.has(ev.source_id) || (st?.tool_calls ?? []).some((tc) => tc.call_id === ev.source_id)) && (
                            <button
                              type="button"
                              onClick={() => jumpToCall(ev.source_id)}
                              className="rounded-lg border border-zinc-200 bg-white px-2 py-0.5 text-xs font-medium text-zinc-600 hover:bg-zinc-50"
                            >
                              {t(locale, "insp.viewToolCall")}
                            </button>
                          )}
                        </span>
                      </div>
                      <Progress value={ev.confidence * 100} aria-label={t(locale, "insp.confidenceAria").replace("{value}", ev.confidence.toFixed(2))} />
                      <p className="text-sm font-medium leading-6">{ev.claim}</p>
                      <details>
                        <summary className="cursor-pointer text-xs font-medium text-zinc-600 hover:text-zinc-900">{t(locale, "insp.resultJson")}</summary>
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
              <EmptyState title={t(locale, "insp.noInsightsTitle")} description={t(locale, "insp.noInsightsBody")} />
            )}
            {(st?.insights ?? []).map((ins) => (
              <Card key={ins.id}>
                <CardContent className="space-y-2 p-4 pt-4">
                  <p className="text-sm leading-6">{ins.finding}</p>
                  <p className="text-xs text-zinc-500">{t(locale, "insp.evidencePrefix")} {ins.evidence_ids.join(", ") || "—"}</p>
                  {ins.limitation && (() => {
                    const sev = limitationSeverity(ins.limitation);
                    const caveat = limitationText(ins.limitation, locale);
                    return (
                      <p
                        role="note"
                        className={`flex items-start gap-2 rounded-lg border p-2.5 text-xs leading-5 ${sev === "error" ? "border-red-200 bg-red-50 text-red-800" : "border-amber-200 bg-amber-50 text-amber-800"}`}
                      >
                        <AlertTriangle className="mt-0.5 size-3.5 shrink-0" aria-hidden />
                        <span><strong>{t(locale, sev === "error" ? "insp.limitationCritical" : "insp.limitationPlain")}</strong> {caveat}</span>
                      </p>
                    );
                  })()}
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="artifacts">
          <div className="grid items-start gap-4 lg:grid-cols-[0.9fr_1.1fr]">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">{t(locale, "insp.artifactsTitle").replace("{n}", String(st?.artifacts.length ?? 0))}</CardTitle>
                <CardDescription className="text-xs">{t(locale, "insp.artifactsBody")}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {(st?.artifacts.length ?? 0) === 0 && (
                  <p className="text-sm text-zinc-500">{t(locale, "insp.noArtifacts")}</p>
                )}
                {artifactGroups.map(([kind, items]) => {
                  const Icon = kindIcon(kind);
                  return (
                    <div key={kind}>
                      <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-zinc-400">{kind} ({items.length})</p>
                      <ul className="space-y-1.5">
                        {items.map((a) => (
                          <li key={a.id} className="flex items-center gap-2 rounded-lg border border-zinc-100 px-2 py-1.5">
                            <Icon className="size-3.5 shrink-0 text-zinc-400" aria-hidden />
                            <span className="min-w-0 flex-1 truncate font-mono text-xs" title={a.path}>{a.path.split("/").pop()}</span>
                            <button
                              type="button"
                              onClick={() => navigator.clipboard.writeText(a.path).catch(() => {})}
                              title={t(locale, "insp.copyPathTitle").replace("{path}", a.path)}
                              aria-label={t(locale, "insp.copyPathAria").replace("{name}", a.path.split("/").pop() ?? "")}
                              className="shrink-0 rounded p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700"
                            >
                              <Copy className="size-3.5" aria-hidden />
                            </button>
                          </li>
                        ))}
                      </ul>
                    </div>
                  );
                })}
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex-row items-center justify-between space-y-0">
                <div>
                  <CardTitle className="text-sm">{t(locale, "insp.reportTitle")}</CardTitle>
                  <CardDescription className="text-xs">{t(locale, "insp.reportSub")}</CardDescription>
                </div>
                {st?.report_markdown && (
                  <div className="flex gap-2">
                    <Button variant="secondary" size="sm" onClick={copyReport}>
                      {copied ? <><Check className="size-3.5" aria-hidden /> {t(locale, "insp.copied")}</> : <><Copy className="size-3.5" aria-hidden /> {t(locale, "insp.copyMarkdown")}</>}
                    </Button>
                    <Button variant="secondary" size="sm" onClick={downloadReport}>
                      <Download className="size-3.5" aria-hidden /> .md
                    </Button>
                  </div>
                )}
              </CardHeader>
              <CardContent>
                {st?.report_markdown ? (
                  <>
                    <div className="max-h-96 overflow-auto rounded-lg border border-zinc-100 p-3">
                      <Markdown text={st.report_markdown.slice(0, 6000)} />
                      {st.report_markdown.length > 6000 && (
                        <p className="mt-2 text-xs text-zinc-400">{t(locale, "insp.reportTruncated")}</p>
                      )}
                    </div>
                    <a href={reportUrl} target="_blank" rel="noreferrer" className="mt-3 inline-block text-sm font-medium underline">
                      {t(locale, "insp.openReport")}
                    </a>
                  </>
                ) : (
                  <EmptyState title={t(locale, "insp.noReportTitle")} description={t(locale, "insp.noReportBody")} />
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      <FollowUpBox run={run} />

      <p className="text-xs text-zinc-400">
        {t(locale, "insp.fullTraceVia")} <code className="font-mono">GET /api/v1/analysis/{run.id}</code> · {t(locale, "runsPage.evidenceGraphAt")}{" "}
        <code className="font-mono">/evidence/{"{evidence_id}"}</code> · <Link href="/runs" className="underline">{t(locale, "insp.allRuns")}</Link>
      </p>
    </div>
  );
}
