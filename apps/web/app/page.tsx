import Link from "next/link";
import { BarChart3, MessageCircleQuestion, ShieldCheck, ArrowRight, Github } from "lucide-react";
import { apiUrl } from "@/lib/api";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent } from "@/app/components/ui/card";
import { PageHeader } from "@/app/components/data/PageHeader";
import { StatCard } from "@/app/components/data/StatCard";
import { StatusBadge } from "@/app/components/data/StatusBadge";
import { EmptyState } from "@/app/components/data/States";
import { HeroVisual } from "@/app/components/data/HeroVisual";

type AnalysisSummary = { id: string; status: string; user_query: string; created_at: string | null };

async function fetchRecent(): Promise<AnalysisSummary[]> {
  try {
    const res = await fetch(apiUrl("/api/v1/analysis/"), { cache: "no-store" });
    if (!res.ok) return [];
    const data = (await res.json()) as { analyses: AnalysisSummary[] };
    return data.analyses.slice(0, 6);
  } catch {
    return [];
  }
}

async function fetchCounts(): Promise<{ analyses: number | null; datasets: number | null }> {
  try {
    const [a, d] = await Promise.all([
      fetch(apiUrl("/api/v1/analysis/"), { cache: "no-store" }).then(async (r) =>
        r.ok ? (((await r.json()) as { analyses: unknown[] }).analyses.length as number) : null
      ),
      fetch(apiUrl("/api/v1/datasets/"), { cache: "no-store" }).then(async (r) =>
        r.ok ? (((await r.json()) as { datasets: unknown[] }).datasets.length as number) : null
      ),
    ]);
    return { analyses: a, datasets: d };
  } catch {
    return { analyses: null, datasets: null };
  }
}

const steps = [
  { icon: MessageCircleQuestion, no: "01 · Ask", title: "Start with the business question", body: "Use a CSV, Parquet, JSON, or Excel file and describe what you actually want to learn." },
  { icon: BarChart3, no: "02 · Analyze", title: "Let tools do the computation", body: "DSA plans and executes data-science tools instead of inventing numerical results in prose." },
  { icon: ShieldCheck, no: "03 · Verify", title: "Inspect where each claim came from", body: "Review the agent trace, claim-level evidence, validation checks, and reproducible artifacts." },
];

export default async function Home() {
  const [recent, counts] = await Promise.all([fetchRecent(), fetchCounts()]);

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
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-zinc-500">Verifiable AI data science</p>
            <h1 className="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl">The AI data scientist that shows its work.</h1>
            <p className="mt-4 max-w-2xl text-sm leading-6 text-zinc-600 sm:text-base sm:leading-7">
              Upload a dataset and ask a question in natural language. DSA runs statistics, SQL, machine learning, and visualization — then preserves the evidence behind every supported finding.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link href="/datasets">
                <Button size="lg">Try with your data <ArrowRight className="size-4" aria-hidden /></Button>
              </Link>
              <a href="https://github.com/Jackxiaozhiren/data-science-agent" target="_blank" rel="noreferrer">
                <Button variant="secondary" size="lg"><Github className="size-4" aria-hidden /> View on GitHub ↗</Button>
              </a>
            </div>
            <p className="mt-3 text-xs text-zinc-500">Question → execution → evidence → claim → reproducible report</p>
          </div>
          <HeroVisual />
        </div>
      </section>

      {/* Stats strip — live counts when the API is reachable, placeholders otherwise */}
      <section aria-label="Project statistics" className="grid gap-4 sm:grid-cols-3">
        <StatCard label="Analyses" value={counts.analyses != null ? String(counts.analyses) : "—"} hint={counts.analyses != null ? "Runs in this environment" : "Connect the API to see live counts"} />
        <StatCard label="Datasets" value={counts.datasets != null ? String(counts.datasets) : "—"} hint={counts.datasets != null ? "Uploaded files" : "Connect the API to see live counts"} />
        <StatCard label="Evidence coverage" value="—" hint="Computed per run · see Evaluation" accent="emerald" />
      </section>

      {/* 3 steps */}
      <section className="grid gap-4 md:grid-cols-3">
        {steps.map((s) => {
          const Icon = s.icon;
          return (
            <Card key={s.no}>
              <CardContent className="p-5 pt-5">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-zinc-400">
                  <Icon className="size-4 text-zinc-500" aria-hidden /> {s.no}
                </div>
                <h2 className="mt-2 font-semibold tracking-tight">{s.title}</h2>
                <p className="mt-2 text-sm leading-6 text-zinc-600">{s.body}</p>
              </CardContent>
            </Card>
          );
        })}
      </section>

      {/* Why DSA */}
      <section className="rounded-xl border border-zinc-800 bg-zinc-950 p-6 text-zinc-100 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-zinc-400">Why DSA</p>
        <div className="mt-4 grid gap-5 md:grid-cols-[1.15fr_0.85fr] md:items-center">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight">Most AI analysis tools give you an answer. DSA gives you the answer and the evidence behind it.</h2>
            <p className="mt-3 text-sm leading-6 text-zinc-400">That makes generated analysis easier to inspect, challenge, reproduce, and trust.</p>
            <Link href="/analysis" className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-emerald-300 hover:underline">
              Start with Step 2 · Ask <ArrowRight className="size-4" aria-hidden />
            </Link>
          </div>
          <pre className="overflow-x-auto rounded-lg border border-zinc-800 bg-zinc-900 p-4 font-mono text-xs leading-6 text-zinc-300">{`Claim\n └── Evidence\n      └── Tool call\n           └── Computation\n                └── Dataset hash`}</pre>
        </div>
      </section>

      {/* Recent analyses */}
      <section>
        <PageHeader
          eyebrow="Step 3 · Proof, not promises"
          title="Recent analyses"
          description="Latest runs in this environment. Open one to inspect its evidence chain."
          actions={
            <Link href="/analysis">
              <Button variant="secondary" size="sm">Start analysis</Button>
            </Link>
          }
        />
        <Card className="mt-3">
          <CardContent className="p-3 pt-3 sm:p-4 sm:pt-4">
            {recent.length === 0 ? (
              <EmptyState
                title="No analysis runs yet in this environment"
                description="Upload a dataset and create the first run to see the evidence chain in action."
                action={
                  <Link href="/datasets">
                    <Button size="sm">Upload a dataset →</Button>
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
