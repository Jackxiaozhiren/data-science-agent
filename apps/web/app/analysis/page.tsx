"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2, Play, ShieldCheck, Repeat2, Zap } from "lucide-react";
import { API_BASE_URL, apiUrl } from "@/lib/api";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/app/components/ui/card";
import { Select, Textarea } from "@/app/components/ui/input";
import { PageHeader } from "@/app/components/data/PageHeader";
import { ErrorState, CardsSkeleton } from "@/app/components/data/States";

type Ds = { id: string; filename: string };

function cleanDetail(value: unknown): string {
  const raw = typeof value === "string" ? value : JSON.stringify(value ?? "");
  return raw.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim().slice(0, 300) || "Analysis request failed.";
}

const examples = [
  "What is driving the target, and which effects are statistically significant?",
  "Compare the main groups and explain the strongest differences.",
  "Find the most important patterns, limitations, and evidence behind them.",
];

function AnalysisWorkspace() {
  const sp = useSearchParams();
  const router = useRouter();
  const initialDs = sp.get("dataset") || "";
  const [datasets, setDatasets] = useState<Ds[]>([]);
  const [datasetId, setDatasetId] = useState(initialDs);
  const [query, setQuery] = useState("Which factors explain the outcome, and are the effects statistically significant?");
  const [err, setErr] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    fetch(apiUrl("/api/v1/datasets/"))
      .then(async (r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<{ datasets: Ds[] }>;
      })
      .then((d) => setDatasets(d.datasets))
      .catch((e) => setErr(`Could not reach the DSA API at ${API_BASE_URL}. ${String(e)}`));
  }, []);

  async function run() {
    setErr(null);
    if (!datasetId || !query.trim()) {
      setErr("Select a dataset and enter a question.");
      return;
    }
    setRunning(true);
    try {
      const res = await fetch(apiUrl("/api/v1/analysis/"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dataset_id: datasetId, user_query: query }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = (data as { detail?: unknown }).detail ?? data;
        setErr(cleanDetail(detail));
        return;
      }
      router.push(`/analysis/${(data as { id: string }).id}`);
    } catch (e) {
      setErr(`Analysis could not start because the DSA API at ${API_BASE_URL} is unavailable. ${String(e)}`);
    } finally {
      setRunning(false);
    }
  }

  const words = query.trim() ? query.trim().split(/\s+/).length : 0;

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Step 2 · Ask a question"
        title="Ask a real data-science question"
        description="DSA will plan the analysis, execute tools, build evidence, and preserve the trace."
      />
      <div className="grid items-start gap-4 lg:grid-cols-[1.25fr_0.75fr]">
        <Card>
          <CardContent className="space-y-4 p-4 pt-4 sm:p-5 sm:pt-5">
            <div>
              <label htmlFor="dataset" className="block text-sm font-medium">Dataset</label>
              <Select id="dataset" value={datasetId} onChange={(e) => setDatasetId(e.target.value)} className="mt-1.5" aria-label="Select dataset">
                <option value="">— select —</option>
                {datasets.map((d) => (
                  <option key={d.id} value={d.id}>{d.filename} ({d.id.slice(0, 8)})</option>
                ))}
              </Select>
              {datasets.length === 0 && (
                <p className="mt-1.5 text-xs text-zinc-500">
                  No datasets loaded. <Link href="/datasets" className="font-medium underline">Upload one in Step 1 →</Link>
                </p>
              )}
            </div>
            <div>
              <div className="flex items-baseline justify-between gap-2">
                <label htmlFor="query" className="block text-sm font-medium">Natural-language question</label>
                <span className="text-xs tabular-nums text-zinc-400" aria-label={`${words} words`}>{query.length} chars · {words} words</span>
              </div>
              <Textarea
                id="query"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                rows={4}
                maxLength={2000}
                className="mt-1.5"
                placeholder="e.g. What is driving churn, and which findings are statistically supported?"
              />
              <div className="mt-2 flex flex-wrap gap-2" aria-label="Example questions">
                {examples.map((example) => (
                  <button
                    key={example}
                    type="button"
                    onClick={() => setQuery(example)}
                    className="max-w-full truncate rounded-full border border-zinc-200 bg-zinc-50 px-3 py-1 text-xs text-zinc-600 hover:bg-zinc-100"
                    title={example}
                  >
                    {example.length > 64 ? `${example.slice(0, 64)}…` : example}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Button onClick={run} disabled={running} aria-busy={running}>
                {running ? <><Loader2 className="size-4 animate-spin" aria-hidden /> Running analysis…</> : <><Play className="size-4" aria-hidden /> Run analysis →</>}
              </Button>
              {running && <p className="text-xs text-zinc-500">Planning and executing tools — this can take a minute.</p>}
            </div>
            {err && <ErrorState message={err} />}
          </CardContent>
        </Card>

        <div className="space-y-3 lg:sticky lg:top-20">
          {[
            { icon: Zap, t: "1. Execute", b: "SQL, statistics, ML, and visualization tools run against your dataset — no invented numbers." },
            { icon: ShieldCheck, t: "2. Verify", b: "Every claim links back to evidence, tool calls, and the pinned dataset hash." },
            { icon: Repeat2, t: "3. Reproduce", b: "Inspect the trace, artifacts, and Markdown report in Step 3." },
          ].map((c) => {
            const Icon = c.icon;
            return (
              <Card key={c.t}>
                <CardContent className="flex gap-3 p-4 pt-4">
                  <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-zinc-100" aria-hidden>
                    <Icon className="size-4 text-zinc-600" />
                  </span>
                  <span>
                    <strong className="text-sm">{c.t}</strong>
                    <p className="mt-1 text-xs leading-5 text-zinc-500">{c.b}</p>
                  </span>
                </CardContent>
              </Card>
            );
          })}
          <Card>
            <CardHeader><CardTitle className="text-sm">New here?</CardTitle></CardHeader>
            <CardContent className="-mt-2 text-xs leading-5 text-zinc-500">
              Start at <Link href="/datasets" className="font-medium text-zinc-900 underline">Step 1 · Bring your data</Link>, then come back to ask.
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

export default function AnalysisPage() {
  return (
    <Suspense fallback={<CardsSkeleton count={2} />}>
      <AnalysisWorkspace />
    </Suspense>
  );
}
