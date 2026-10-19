"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2, Play, ShieldCheck, Repeat2, Zap } from "lucide-react";
import { clientFetch, API_BASE_URL, classifyResponse, failurePresentation, type ApiFailure } from "@/lib/api";
import { t, type Locale } from "@/lib/locale";
import { useLocale } from "@/app/lib/LocaleProvider";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/app/components/ui/card";
import { Select, Textarea } from "@/app/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/app/components/ui/dialog";
import { PageHeader } from "@/app/components/data/PageHeader";
import { ErrorState, CardsSkeleton } from "@/app/components/data/States";
import { useBackendProbe } from "@/app/lib/backendProbe";

type Ds = { id: string; filename: string };

// Inherits the shared wording, and keeps this page's own line for the transport case: which base URL
// was unreachable is the diagnostic a reader needs here. The line itself comes from the locale owner with
// the URL substituted into it, so the sentence is bilingual and the origin is still the running instance's.
function askMessages(locale: Locale): Record<ApiFailure, string> {
  return { ...failurePresentation(locale), transport: t(locale, "ask.transport").replace("{url}", API_BASE_URL) };
}

function cleanDetail(value: unknown, locale: Locale): string {
  const raw = typeof value === "string" ? value : JSON.stringify(value ?? "");
  return raw.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim().slice(0, 300) || t(locale, "ask.requestFailed");
}

// The chips are sentences with a column name in them, so the template belongs to the locale owner and the
// name is substituted here. Building the sentence in the component would put a second copy of the wording
// outside UI_STRINGS, where the parity guard cannot see it.
function chipTemplates(locale: Locale): [(c: string) => string, (c: string) => string, (c: string) => string] {
  const fill = (key: string) => (column: string) => t(locale, key).replaceAll("{c}", column);
  return [fill("ask.chipVary"), fill("ask.chipSpread"), fill("ask.chipExplain")];
}

function columnChips(columns: string[], locale: Locale): string[] {
  const [c0, c1, c2] = columns;
  if (!c0) return [t(locale, "ask.example1"), t(locale, "ask.example2"), t(locale, "ask.example3")];
  const [vary, spread, explain] = chipTemplates(locale);
  return [vary(c0), spread(c1 ?? c0), explain(c2 ?? c0)];
}

function AnalysisWorkspace({ locale }: { locale: Locale }) {
  const messages = askMessages(locale);
  const sp = useSearchParams();
  const router = useRouter();
  const initialDs = sp.get("dataset") || "";
  const initialQ = sp.get("q") || t(locale, "ask.defaultQuery");
  const [datasets, setDatasets] = useState<{ items: Ds[]; failure: ApiFailure | null }>({
    items: [],
    failure: null,
  });
  const [datasetId, setDatasetId] = useState(initialDs);
  const [query, setQuery] = useState(initialQ);
  const [columns, setColumns] = useState<string[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  // The dataset list here is empty during a cold start for a different reason than it is empty for a new
  // account, and only the probe can tell them apart (web plan B3/B4).
  const { phase, copy, retry } = useBackendProbe();

  useEffect(() => {
    clientFetch("/api/v1/datasets/")
      .then(async (r) => {
        const failure = classifyResponse(r);
        if (failure) {
          setDatasets({ items: [], failure });
          setErr(messages[failure]);
          return;
        }
        const d = (await r.json()) as { datasets: Ds[] };
        setDatasets({ items: d.datasets, failure: null });
      })
      .catch(() => {
        setDatasets({ items: [], failure: "transport" });
        setErr(messages.transport);
      });
  }, []);

  // Dynamic suggestion chips from the selected dataset's real columns.
  useEffect(() => {
    if (!datasetId) {
      setColumns([]);
      return;
    }
    let cancelled = false;
    clientFetch(`/api/v1/datasets/${datasetId}`)
      .then(async (r) => {
        if (!r.ok) return;
        const d = (await r.json()) as { profile?: { column_profiles?: { name: string }[] } | null };
        if (!cancelled) setColumns((d.profile?.column_profiles ?? []).map((c) => c.name).slice(0, 6));
      })
      .catch(() => {
        if (!cancelled) setColumns([]);
      });
    return () => {
      cancelled = true;
    };
  }, [datasetId]);

  const datasetName = datasets.items.find((d) => d.id === datasetId)?.filename ?? datasetId.slice(0, 12);
  const examples = columnChips(columns, locale);

  async function run() {
    setErr(null);
    setConfirmOpen(false);
    if (!datasetId || !query.trim()) {
      setErr(t(locale, "ask.needBoth"));
      return;
    }
    setRunning(true);
    try {
      const res = await clientFetch("/api/v1/analysis/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dataset_id: datasetId, user_query: query }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = (data as { detail?: unknown }).detail ?? data;
        setErr(cleanDetail(detail, locale));
        return;
      }
      router.push(`/analysis/${(data as { id: string }).id}`);
    } catch (e) {
      setErr(`${t(locale, "ask.couldNotStart").replaceAll("{url}", API_BASE_URL)} ${String(e)}`);
    } finally {
      setRunning(false);
    }
  }

  function askConfirm() {
    setErr(null);
    if (!datasetId || !query.trim()) {
      setErr(t(locale, "ask.needBoth"));
      return;
    }
    setConfirmOpen(true);
  }

  const words = query.trim() ? query.trim().split(/\s+/).length : 0;
  const steps = [
    { icon: Zap, title: "ask.step1", body: "ask.step1Body" },
    { icon: ShieldCheck, title: "ask.step2", body: "ask.step2Body" },
    { icon: Repeat2, title: "ask.step3", body: "ask.step3Body" },
  ];

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow={t(locale, "ask.eyebrow")}
        title={t(locale, "ask.title")}
        description={t(locale, "ask.description")}
      />
      <div className="grid items-start gap-4 lg:grid-cols-[1.25fr_0.75fr]">
        <Card className="min-w-0">
          <CardContent className="space-y-4 p-4 pt-4 sm:p-5 sm:pt-5">
            <div>
              <label htmlFor="dataset" className="block text-sm font-medium">{t(locale, "ask.datasetLabel")}</label>
              <Select id="dataset" value={datasetId} onChange={(e) => setDatasetId(e.target.value)} className="mt-1.5" aria-label={t(locale, "ask.datasetSelectAria")}>
                <option value="">{t(locale, "ask.selectNone")}</option>
                {datasets.items.map((d) => (
                  <option key={d.id} value={d.id}>{d.filename} ({d.id.slice(0, 8)})</option>
                ))}
              </Select>
              {datasets.items.length === 0 && !datasets.failure && (
                phase === "ready" ? (
                  <p className="mt-1.5 text-xs text-zinc-500">
                    {t(locale, "ask.noDatasets")}{" "}
                    <Link href="/datasets" className="font-medium underline">{t(locale, "ask.uploadOne")}</Link>
                  </p>
                ) : (
                  <p className="mt-1.5 text-xs text-amber-800" role="status" aria-live="polite">{copy}</p>
                )
              )}
            </div>
            <div>
              <div className="flex items-baseline justify-between gap-2">
                <label htmlFor="query" className="block text-sm font-medium">{t(locale, "ask.questionLabel")}</label>
                <span className="text-xs tabular-nums text-zinc-400" aria-label={`${words} ${t(locale, "ask.wordCountAria")}`}>
                  {query.length} {t(locale, "ask.charUnit")} · {words} {t(locale, "ask.wordUnit")}
                </span>
              </div>
              <Textarea
                id="query"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                rows={4}
                maxLength={2000}
                className="mt-1.5"
                placeholder={t(locale, "ask.placeholder")}
              />
              <div className="mt-2 flex flex-wrap gap-2" aria-label={t(locale, "ask.examplesAria")}>
                {columns.length > 0 && (
                  <span className="w-full text-[11px] uppercase tracking-wider text-zinc-400">{t(locale, "ask.suggestedFor")}</span>
                )}
                {examples.map((example) => (
                  <button
                    key={example}
                    type="button"
                    onClick={() => setQuery(example)}
                    className="min-w-0 max-w-full truncate rounded-full border border-zinc-200 bg-zinc-50 px-3 py-1 text-xs text-zinc-600 hover:bg-zinc-100"
                    title={example}
                  >
                    {example.length > 64 ? `${example.slice(0, 64)}…` : example}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              {/* Submitting into an instance that has not answered yet queues a request the reader cannot
                  see, so the button says why it is waiting instead of going quiet. */}
              <Button onClick={askConfirm} disabled={running || phase === "warming" || phase === "probing"} aria-busy={running}>
                {running ? <><Loader2 className="size-4 animate-spin" aria-hidden /> {t(locale, "ask.startingButton")}</> : <><Play className="size-4" aria-hidden /> {t(locale, "ask.runNow")}</>}
              </Button>
              {running && <p className="text-xs text-zinc-500">{t(locale, "ask.watchNextPage")}</p>}
              {(phase === "warming" || phase === "probing") && !running && (
                <p className="text-xs text-amber-800" role="status" aria-live="polite">{copy}</p>
              )}
              {phase === "unreachable" && (
                <Button variant="secondary" size="sm" onClick={retry}>{t(locale, "probe.retryCheck")}</Button>
              )}
            </div>
            {err && <ErrorState message={err} />}
          </CardContent>
        </Card>

        <div className="min-w-0 space-y-3 lg:sticky lg:top-20">
          {steps.map((c) => {
            const Icon = c.icon;
            return (
              <Card key={c.title}>
                <CardContent className="flex gap-3 p-4 pt-4">
                  <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-zinc-100" aria-hidden>
                    <Icon className="size-4 text-zinc-600" />
                  </span>
                  <span>
                    <strong className="text-sm">{t(locale, c.title)}</strong>
                    <p className="mt-1 text-xs leading-5 text-zinc-500">{t(locale, c.body)}</p>
                  </span>
                </CardContent>
              </Card>
            );
          })}
          <Card>
            <CardHeader><CardTitle className="text-sm">{t(locale, "ask.newHere")}</CardTitle></CardHeader>
            <CardContent className="-mt-2 text-xs leading-5 text-zinc-500">
              {t(locale, "ask.newHereBodyPre")}{" "}
              <Link href="/datasets" className="font-medium text-zinc-900 underline">{t(locale, "ask.newHereLink")}</Link>
              {t(locale, "ask.newHereBodyPost")}
            </CardContent>
          </Card>
        </div>
      </div>

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent onClose={() => setConfirmOpen(false)}>
          <DialogHeader>
            <DialogTitle>{t(locale, "ask.confirmTitle")}</DialogTitle>
            <DialogDescription>{t(locale, "ask.confirmBody")}</DialogDescription>
          </DialogHeader>
          <dl className="space-y-2 text-sm">
            <div>
              <dt className="text-xs font-medium uppercase tracking-wider text-zinc-400">{t(locale, "ask.datasetLabel")}</dt>
              <dd className="mt-0.5 font-medium">{datasetName}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wider text-zinc-400">
                {t(locale, "ask.questionLabel")} ({query.length} {t(locale, "ask.charUnit")} · {words} {t(locale, "ask.wordUnit")})
              </dt>
              <dd className="mt-0.5 max-h-32 overflow-auto rounded-lg bg-zinc-50 p-2.5 text-sm leading-6">{query}</dd>
            </div>
          </dl>
          <div className="mt-4 flex justify-end gap-2">
            <Button variant="secondary" size="sm" onClick={() => setConfirmOpen(false)}>{t(locale, "ask.back")}</Button>
            <Button size="sm" onClick={run} disabled={running}>
              {running ? t(locale, "ask.starting") : t(locale, "ask.confirmRun")}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function AnalysisPage() {
  const locale = useLocale();
  return (
    <Suspense fallback={<CardsSkeleton count={2} />}>
      <AnalysisWorkspace locale={locale} />
    </Suspense>
  );
}
