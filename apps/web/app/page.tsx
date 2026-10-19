import Link from "next/link";
import { BarChart3, MessageCircleQuestion, ShieldCheck, ArrowRight, Github } from "lucide-react";
import { apiUrl, classifyResponse, failurePresentation, type ApiFailure } from "@/lib/api";
import { serverLocale } from "@/lib/serverApi";
import { t } from "@/lib/locale";
import { serverFetch } from "@/lib/serverApi";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent } from "@/app/components/ui/card";
import { PageHeader } from "@/app/components/data/PageHeader";
import { StatCard } from "@/app/components/data/StatCard";
import { StatusBadge } from "@/app/components/data/StatusBadge";
import { EmptyState, ErrorState } from "@/app/components/data/States";
import { HeroVisual } from "@/app/components/data/HeroVisual";
import { firstStarter, sampleInfo, type SampleInfo } from "@/app/lib/sampleData";

type AnalysisSummary = { id: string; status: string; user_query: string; created_at: string | null };

async function fetchRecent(): Promise<{ recent: AnalysisSummary[]; failure: ApiFailure | null }> {
  try {
    const res = await serverFetch("/api/v1/analysis/", { cache: "no-store" });
    const failure = classifyResponse(res);
    if (failure) return { recent: [], failure };
    const data = (await res.json()) as { analyses: AnalysisSummary[] };
    return { recent: data.analyses.slice(0, 6), failure: null };
  } catch {
    return { recent: [], failure: "transport" };
  }
}

async function fetchCounts(): Promise<{ analyses: number | null; datasets: number | null }> {
  try {
    const [a, d] = await Promise.all([
      serverFetch("/api/v1/analysis/", { cache: "no-store" }).then(async (r) =>
        r.ok ? (((await r.json()) as { analyses: unknown[] }).analyses.length as number) : null
      ),
      serverFetch("/api/v1/datasets/", { cache: "no-store" }).then(async (r) =>
        r.ok ? (((await r.json()) as { datasets: unknown[] }).datasets.length as number) : null
      ),
    ]);
    return { analyses: a, datasets: d };
  } catch {
    return { analyses: null, datasets: null };
  }
}

const STEPS = [
  { icon: MessageCircleQuestion, key: "step1" },
  { icon: BarChart3, key: "step2" },
  { icon: ShieldCheck, key: "step3" },
];

type DatasetRow = { id: string; metadata?: unknown };

/** R-01: the sample data the API rebuilt on boot, read through the one marker owner. */
async function fetchSamples(): Promise<{ samples: { id: string; sample: SampleInfo }[]; failure: ApiFailure | null }> {
  try {
    const res = await serverFetch("/api/v1/datasets/", { cache: "no-store" });
    const failure = classifyResponse(res);
    if (failure) return { samples: [], failure };
    const data = (await res.json()) as { datasets: DatasetRow[] };
    const samples = (data.datasets || [])
      .map((row) => ({ id: row.id, sample: sampleInfo(row.metadata) }))
      .filter((entry): entry is { id: string; sample: SampleInfo } => entry.sample !== null);
    return { samples, failure: null };
  } catch {
    return { samples: [], failure: "transport" };
  }
}

export default async function Home() {
  const [locale, { recent, failure }, counts, seeded] = await Promise.all([
    serverLocale(),
    fetchRecent(),
    fetchCounts(),
    fetchSamples(),
  ]);
  const shared = failurePresentation(locale);
  const starter = firstStarter(seeded.samples, locale);
  const exampleRunId = seeded.samples.find((entry) => entry.sample.exampleRunId)?.sample.exampleRunId ?? null;

  return (
    <div className="space-y-6">
      {/* Hero — the single gradient + grid + beam accent on the site */}
      <section className="relative overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-sm">
        <div aria-hidden className="bg-grid-zinc pointer-events-none absolute inset-0" />
        <div aria-hidden className="pointer-events-none absolute -right-24 -top-24 size-72 rounded-full bg-emerald-100/70 blur-3xl" />
        <div aria-hidden className="pointer-events-none absolute inset-x-0 top-0 h-px overflow-hidden">
          <div className="animate-beam h-px w-1/3 bg-gradient-to-r from-transparent via-emerald-400 to-transparent" />
        </div>
        <div className="relative grid gap-6 p-6 sm:p-10 lg:grid-cols-[1.15fr_0.85fr] lg:items-center">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-zinc-500">{t(locale, "home.eyebrow")}</p>
            <h1 className="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl">{t(locale, "home.title")}</h1>
            <p className="mt-4 max-w-2xl text-sm leading-6 text-zinc-600 sm:text-base sm:leading-7">{t(locale, "home.body")}</p>
            <div className="mt-6 flex flex-wrap gap-3">
              {starter ? (
                <Link
                  href={`/analysis?dataset=${encodeURIComponent(starter.datasetId)}&q=${encodeURIComponent(starter.question)}`}
                  data-start-here="true"
                >
                  <Button size="lg" title={starter.question}>
                    {t(locale, "home.cta.askSample")}{" "}
                    <span className="max-w-[18ch] truncate sm:max-w-[34ch]">
                      {starter.question.replace(/^(Summarize|Provide)[,:]? ?/i, "").slice(0, 46)}…
                    </span>{" "}
                    <ArrowRight className="size-4" aria-hidden />
                  </Button>
                </Link>
              ) : (
                <Link href="/datasets" data-start-here="upload">
                  <Button size="lg">{t(locale, "home.cta.tryYourData")} <ArrowRight className="size-4" aria-hidden /></Button>
                </Link>
              )}
              {exampleRunId && (
                <Link href={`/analysis/${exampleRunId}`} data-example-report={exampleRunId}>
                  <Button variant="secondary" size="lg">{t(locale, "home.cta.openExample")} <ArrowRight className="size-4" aria-hidden /></Button>
                </Link>
              )}
              <a href="https://github.com/Jackxiaozhiren/data-science-agent" target="_blank" rel="noreferrer">
                <Button variant="secondary" size="lg"><Github className="size-4" aria-hidden /> {t(locale, "home.cta.github")}</Button>
              </a>
            </div>
            <p className="mt-3 text-xs text-zinc-500">
              {starter ? t(locale, "home.heroNote.sample") : t(locale, "home.heroNote.flow")}
            </p>
          </div>
          <HeroVisual />
        </div>
      </section>

      {/* Stats strip — live counts when the API is reachable, placeholders otherwise */}
      <section aria-label={t(locale, "home.stats.aria")} className="grid gap-4 sm:grid-cols-3">
        <StatCard label={t(locale, "home.stats.analyses")} value={counts.analyses != null ? String(counts.analyses) : "—"} hint={counts.analyses != null ? t(locale, "home.stats.runsHere") : t(locale, "home.stats.connectApi")} />
        <StatCard label={t(locale, "home.stats.datasets")} value={counts.datasets != null ? String(counts.datasets) : "—"} hint={counts.datasets != null ? t(locale, "home.stats.uploaded") : t(locale, "home.stats.connectApi")} />
        <StatCard label={t(locale, "home.stats.coverage")} value="—" hint={t(locale, "home.stats.coverageHint")} accent="emerald" />
      </section>

      {/* 3 steps */}
      <section className="grid gap-4 md:grid-cols-3">
        {STEPS.map((s) => {
          const Icon = s.icon;
          return (
            <Card key={s.key}>
              <CardContent className="p-5 pt-5">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-zinc-400">
                  <Icon className="size-4 text-zinc-500" aria-hidden /> {t(locale, `home.${s.key}.label`)}
                </div>
                <h2 className="mt-2 font-semibold tracking-tight">{t(locale, `home.${s.key}.title`)}</h2>
                <p className="mt-2 text-sm leading-6 text-zinc-600">{t(locale, `home.${s.key}.body`)}</p>
              </CardContent>
            </Card>
          );
        })}
      </section>

      {/* Why DSA */}
      <section className="rounded-xl border border-zinc-800 bg-zinc-950 p-6 text-zinc-100 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-zinc-400">{t(locale, "home.why.eyebrow")}</p>
        <div className="mt-4 grid gap-5 md:grid-cols-[1.15fr_0.85fr] md:items-center">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight">{t(locale, "home.why.title")}</h2>
            <p className="mt-3 text-sm leading-6 text-zinc-400">{t(locale, "home.why.body")}</p>
            <Link href="/analysis" className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-emerald-300 hover:underline">
              {t(locale, "home.why.link")} <ArrowRight className="size-4" aria-hidden />
            </Link>
          </div>
          <pre className="overflow-x-auto rounded-lg border border-zinc-800 bg-zinc-900 p-4 font-mono text-xs leading-6 text-zinc-300">{t(locale, "home.why.chain")}</pre>
        </div>
      </section>

      {/* Recent analyses */}
      <section>
        <PageHeader
          eyebrow={t(locale, "home.recent.eyebrow")}
          title={t(locale, "home.recent.title")}
          description={t(locale, "home.recent.description")}
          actions={
            <Link href="/analysis">
              <Button variant="secondary" size="sm">{t(locale, "home.recent.start")}</Button>
            </Link>
          }
        />
        <Card className="mt-3">
          <CardContent className="p-3 pt-3 sm:p-4 sm:pt-4">
            {failure ? (
              <ErrorState message={shared[failure]} />
            ) : recent.length === 0 ? (
              <EmptyState
                title={t(locale, "home.recent.emptyTitle")}
                description={t(locale, "home.recent.emptyBody")}
                action={
                  <Link href="/datasets">
                    <Button size="sm">{t(locale, "home.recent.upload")}</Button>
                  </Link>
                }
              />
            ) : (
              <ul className="divide-y divide-zinc-100">
                {recent.map((r) => (
                  <li key={r.id} className="flex items-center justify-between gap-3 py-2.5">
                    <Link href={`/analysis/${r.id}`} className="min-w-0 flex-1 truncate text-sm hover:underline">
                      {r.user_query || r.id}
                    </Link>
                    <StatusBadge status={r.status} />
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
