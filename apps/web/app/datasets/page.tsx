"use client";

import * as React from "react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { FileUp, Database, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { clientFetch, API_BASE_URL, apiUrl, classifyResponse, failurePresentation } from "@/lib/api";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/app/components/ui/card";
import { Progress } from "@/app/components/ui/feedback";
import { PageHeader } from "@/app/components/data/PageHeader";
import { DataTable } from "@/app/components/data/DataTable";
import { EmptyState, ErrorState, TableSkeleton } from "@/app/components/data/States";
import { useBackendProbe } from "@/app/lib/backendProbe";
import { useLocale } from "@/app/lib/LocaleProvider";
import { t, type Locale } from "@/lib/locale";
import { sampleInfo, starterQuestionsFor, type SampleInfo } from "@/app/lib/sampleData";

type Dataset = {
  id: string;
  filename: string;
  format: string;
  rows: number | null;
  cols: number | null;
  created_at: string | null;
  // The API's own marker for seeded sample data rides along (apps/web/app/lib/sampleData.ts owns the shape);
  // without it a visitor cannot tell a demo row from their own upload.
  metadata?: unknown;
};

async function errorMessage(res: Response, locale: Locale): Promise<string> {
  // Never dump raw response bodies: a misconfigured API URL returns a full
  // HTML error page, which is unreadable and leaks internals. One human line.
  let hint = "";
  try {
    const body = await res.text();
    const clean = body.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
    if (clean) hint = `: ${clean.slice(0, 160)}`;
  } catch {
    hint = "";
  }
  return t(locale, "ds.requestFailed")
    .replace("{status}", String(res.status))
    .replace("{hint}", hint);
}

const MAX_BYTES = 100 * 1024 * 1024;

type QueuedFile = {
  key: string;
  name: string;
  size: number;
  status: "queued" | "uploading" | "done" | "error";
  note?: string;
};

export default function DatasetsPage() {
  const locale = useLocale();
  const [items, setItems] = useState<Dataset[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [queue, setQueue] = useState<QueuedFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [dragging, setDragging] = useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);
  const busyRef = React.useRef(false);
  // One shared probe tells this page whether the backend answered at all, which is the difference between
  // "this account has no datasets" and "there is nothing there to ask" (web plan B3/B4).
  const { phase, copy, retry } = useBackendProbe();

  const samples = React.useMemo(
    () =>
      items
        .map((d) => ({ id: d.id, filename: d.filename, sample: sampleInfo(d.metadata) }))
        .filter((entry): entry is { id: string; filename: string; sample: SampleInfo } => entry.sample !== null),
    [items]
  );

  async function load() {
    setLoading(true);
    setErr(null);
    const shared = failurePresentation(locale);
    try {
      const res = await clientFetch("/api/v1/datasets/");
      const failure = classifyResponse(res);
      if (failure) {
        setErr(`${shared[failure]} ${t(locale, "ds.checkDiagnostics")}`);
        return;
      }
      const data = (await res.json()) as { datasets: Dataset[] };
      setItems(data.datasets);
    } catch {
      // The base URL is the reader's own diagnostic for the one failure this page cannot describe from a
      // status code: nothing answered at all.
      setErr(`${shared.transport} (${API_BASE_URL})`);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function uploadOne(f: File, key: string) {
    setQueue((q) => q.map((it) => (it.key === key ? { ...it, status: "uploading" as const } : it)));
    const fd = new FormData();
    fd.append("file", f);
    try {
      const res = await clientFetch("/api/v1/datasets/", { method: "POST", body: fd });
      if (!res.ok) {
        const msg = await errorMessage(res, locale);
        setQueue((q) => q.map((it) => (it.key === key ? { ...it, status: "error" as const, note: msg } : it)));
        return;
      }
      setQueue((q) => q.map((it) => (it.key === key ? { ...it, status: "done" as const } : it)));
      await load();
    } catch (e) {
      const msg = t(locale, "ds.uploadUnavailable")
        .replace("{url}", API_BASE_URL)
        .replace("{detail}", String(e));
      setQueue((q) => q.map((it) => (it.key === key ? { ...it, status: "error" as const, note: msg } : it)));
    }
  }

  // Sequential queue: pre-check size locally, warn on duplicate names, then upload one by one.
  async function enqueue(files: File[]) {
    if (files.length === 0 || busyRef.current) return;
    busyRef.current = true;
    setErr(null);
    const existing = new Set(items.map((d) => d.filename.toLowerCase()));
    const additions: QueuedFile[] = [];
    const accepted: { file: File; key: string }[] = [];
    for (const f of files) {
      const key = `${Date.now()}-${Math.random().toString(36).slice(2)}-${f.name}`;
      if (f.size > MAX_BYTES) {
        additions.push({
          key,
          name: f.name,
          size: f.size,
          status: "error",
          note: t(locale, "ds.skipTooLarge")
            .replace("{size}", (f.size / 1048576).toFixed(1))
            .replace("{limit}", String(MAX_BYTES / 1048576)),
        });
        continue;
      }
      const dupNote = existing.has(f.name.toLowerCase()) ? t(locale, "ds.dupNote") : undefined;
      existing.add(f.name.toLowerCase());
      additions.push({ key, name: f.name, size: f.size, status: "queued", note: dupNote });
      accepted.push({ file: f, key });
    }
    setQueue((q) => [...q, ...additions]);
    for (const { file, key } of accepted) {
      await uploadOne(file, key);
    }
    busyRef.current = false;
    if (inputRef.current) inputRef.current.value = "";
  }

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? []);
    await enqueue(files);
  }

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow={t(locale, "ds.eyebrow")}
        title={t(locale, "ds.title")}
        description={t(locale, "ds.description")}
        actions={
          <>
            <Link href="/datasets/compare">
              <Button variant="secondary" size="sm">{t(locale, "ds.compare")}</Button>
            </Link>
            <Link href="/analysis">
              <Button variant="secondary" size="sm">{t(locale, "ds.skipAsk")}</Button>
            </Link>
          </>
        }
      />

      {/* The expectation, stated once here rather than in a toast after the first failure: this demo runs
          on a free instance that sleeps when idle, so the first request can take the better part of a
          minute. Saying it at the entrance is what makes the wait readable instead of suspicious. */}
      <p className="text-xs leading-5 text-zinc-500" data-cold-start-notice="true">
        {phase === "ready" ? t(locale, "ds.coldStart") : copy}
      </p>

      {/* Drag-and-drop upload card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">{t(locale, "ds.uploadTitle")}</CardTitle>
          <CardDescription className="text-xs">{t(locale, "ds.uploadBody")}</CardDescription>
          {/* R-08, said plainly: what the id does, and what it does not do. A line that only promised privacy here
              would be the half-measure the plan warns about, so it names the cookie and the limit together. */}
          <p className="mt-1 text-xs text-zinc-500">{t(locale, "ds.ownerDisclosure")}</p>
        </CardHeader>
        <CardContent>
          <div
            role="button"
            tabIndex={0}
            aria-label={t(locale, "ds.dropZoneAria")}
            onClick={() => inputRef.current?.click()}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
            }}
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              void enqueue(Array.from(e.dataTransfer.files ?? []));
            }}
            className={`flex flex-col items-center rounded-xl border border-dashed px-6 py-8 text-center transition-colors ${dragging ? "border-emerald-400 bg-emerald-50/60" : "border-zinc-300 bg-zinc-50/60 hover:bg-zinc-50"}`}
          >
            <span className="flex size-10 items-center justify-center rounded-full bg-white shadow-sm" aria-hidden>
              <FileUp className="size-5 text-zinc-500" />
            </span>
            <p className="mt-3 text-sm font-medium">{dragging ? t(locale, "ds.dropNow") : t(locale, "ds.dropHere")}</p>
            <p className="mt-1 text-xs text-zinc-500">{t(locale, "ds.sendsToApi")}</p>
            <Button variant="secondary" size="sm" className="mt-3" onClick={(e) => { e.stopPropagation(); inputRef.current?.click(); }}>
              {t(locale, "ds.browse")}
            </Button>
            <input ref={inputRef} type="file" multiple accept=".csv,.parquet,.json,.xlsx,.xls" onChange={onUpload} className="sr-only" aria-label={t(locale, "ds.filesAria")} />
          </div>
          {queue.length > 0 && (
            <ul className="mt-3 space-y-1.5" role="status" aria-label={t(locale, "ds.queueAria")}>
              {queue.slice(-5).map((it) => (
                <li key={it.key} className="flex items-start gap-2 rounded-lg border border-zinc-100 px-2.5 py-1.5 text-xs">
                  {it.status === "done" ? (
                    <CheckCircle2 className="mt-0.5 size-3.5 shrink-0 text-emerald-600" aria-hidden />
                  ) : it.status === "error" ? (
                    <XCircle className="mt-0.5 size-3.5 shrink-0 text-red-500" aria-hidden />
                  ) : (
                    <Loader2 className="mt-0.5 size-3.5 shrink-0 animate-spin text-zinc-400" aria-hidden />
                  )}
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium" title={it.name}>
                      {it.name} <span className="font-normal text-zinc-400">({(it.size / 1024).toFixed(0)} KB)</span>
                    </span>
                    {it.status === "uploading" && <Progress value={60} className="mt-1 h-1.5" />}
                    {it.note && <span className={`mt-0.5 block leading-4 ${it.status === "error" ? "text-red-600" : "text-amber-700"}`}>{it.note}</span>}
                    {it.status === "done" && <span className="text-emerald-700">{t(locale, "ds.uploadedProfiled")}</span>}
                  </span>
                </li>
              ))}
            </ul>
          )}
          {/* While the probe is still waiting, its own notice is the truth on screen: showing "no response
              could be read" next to "waking up, attempt 2 of 4" is the contradiction R-11 exists to remove. */}
          {err && phase !== "warming" && phase !== "probing" && (
            <div className="mt-3"><ErrorState message={err} retry={() => { retry(); void load(); }} /></div>
          )}
        </CardContent>
      </Card>

      {/* R-01: the demo ships sample data, and this says so where a visitor would otherwise wonder whether an
          unfamiliar row is theirs. Nothing here is written for this page: the questions are the committed
          benchmark catalog's own tasks, offered only where the catalog's dataset is byte-identical to this
          sample, and the report link goes to a run this instance made from them. */}
      {samples.length > 0 && (
        <Card data-sample-panel="true">
          <CardHeader>
            <CardTitle className="text-sm">{t(locale, "ds.sampleTitle")}</CardTitle>
            <CardDescription className="text-xs">{t(locale, "ds.sampleBody")}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {samples.map(({ id, filename, sample }) => (
              <div key={id} className="rounded-lg border bg-white p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <code className="block max-w-[220px] truncate font-mono text-xs font-medium" title={filename}>{filename}</code>
                  <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[11px] uppercase tracking-wide text-zinc-600">{t(locale, "ds.sampleChip")}</span>
                  {sample.exampleRunId && (
                    <Link href={`/analysis/${sample.exampleRunId}`} data-example-report={sample.exampleRunId} className="text-xs font-medium underline">
                      {t(locale, "ds.openReport")}
                    </Link>
                  )}
                </div>
                {starterQuestionsFor(sample, locale).length > 0 ? (
                  <ul className="mt-2 flex flex-wrap gap-2">
                    {starterQuestionsFor(sample, locale).map((question) => (
                      <li key={question}>
                        <Link
                          href={`/analysis?dataset=${encodeURIComponent(id)}&q=${encodeURIComponent(question)}`}
                          data-starter-question={question.slice(0, 24)}
                        >
                          <Button variant="secondary" size="sm" title={question}>
                            {t(locale, "ds.askPrefix")}
                            {question.slice(0, 52)}
                            {question.length > 52 ? "…" : ""}
                          </Button>
                        </Link>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-2 text-xs text-zinc-500">{t(locale, "ds.noQuestionForFile")}</p>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Table card */}
      <Card>
        <CardContent className="p-3 pt-3 sm:p-4 sm:pt-4">
          {loading && (phase === "warming" || phase === "probing") ? (
            <div role="status" aria-live="polite" className="space-y-2">
              <p className="text-sm text-amber-800">{copy}</p>
              <p className="text-xs text-zinc-500">{t(locale, "ds.tableFills")}</p>
            </div>
          ) : loading ? (
            <TableSkeleton rows={5} />
          ) : items.length === 0 && !err && phase === "ready" ? (
            <EmptyState
              icon={<Database className="size-5 text-zinc-400" aria-hidden />}
              title={t(locale, "ds.emptyTitle")}
              description={t(locale, "ds.emptyBody")}
              action={
                <Button size="sm" onClick={() => inputRef.current?.click()}>{t(locale, "ds.emptyUpload")}</Button>
              }
            />
          ) : items.length === 0 && !err ? (
            <div role="status" aria-live="polite" className="text-sm text-zinc-600">{copy}</div>
          ) : items.length > 0 ? (
            <DataTable<Dataset & Record<string, unknown>>
              caption="Datasets"
              keyOf={(d) => d.id}
              rows={items as (Dataset & Record<string, unknown>)[]}
              columns={[
                { key: "filename", header: "File", sortable: true, render: (d) => <span className="block max-w-[220px] truncate font-medium" title={d.filename}>{d.filename}</span> },
                { key: "format", header: "Format", sortable: true, render: (d) => <code className="rounded bg-zinc-100 px-1.5 py-0.5 font-mono text-xs">{d.format || "—"}</code> },
                { key: "rows", header: "Rows", sortable: true, render: (d) => <span className="tabular-nums">{d.rows ?? "—"}</span> },
                { key: "cols", header: "Cols", sortable: true, render: (d) => <span className="tabular-nums">{d.cols ?? "—"}</span> },
                { key: "created_at", header: "Created", sortable: true, className: "hidden sm:table-cell", render: (d) => <span className="whitespace-nowrap text-xs text-zinc-500">{d.created_at?.slice(0, 19).replace("T", " ") || "—"}</span> },
                {
                  key: "__actions", header: "", render: (d) => (
                    <span className="flex shrink-0 items-center gap-3 whitespace-nowrap">
                      <Link href={`/datasets/${d.id}`} className="text-xs font-medium text-zinc-600 underline hover:text-zinc-900">View</Link>
                      <Link href={`/analysis?dataset=${d.id}`} className="text-xs font-semibold text-zinc-900 underline">Analyze →</Link>
                    </span>
                  ),
                },
              ]}
            />
          ) : null}
        </CardContent>
      </Card>

      {/* API diagnostics */}
      <details className="rounded-xl border bg-white px-4 py-3 text-sm shadow-sm">
        <summary className="cursor-pointer text-xs font-medium text-zinc-500">{t(locale, "ds.apiDiagnostics")}</summary>
        <p className="mt-2 text-xs leading-5 text-zinc-500">
          Base URL: <code className="font-mono">{API_BASE_URL}</code>
          {" · "}
          <a href={apiUrl("/health")} className="underline" target="_blank" rel="noreferrer">/health</a>
          {" · "}
          <a href={apiUrl("/metrics")} className="underline" target="_blank" rel="noreferrer">/metrics</a>
          {" · "}
          <a href={apiUrl("/version")} className="underline" target="_blank" rel="noreferrer">/version</a>
        </p>
      </details>
    </div>
  );
}
