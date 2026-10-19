import Link from "next/link";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent } from "@/app/components/ui/card";
import { PageHeader } from "@/app/components/data/PageHeader";
import { EmptyState } from "@/app/components/data/States";
import { serverLocale } from "@/lib/serverApi";
import { t } from "@/lib/locale";

const levels = [
  { nameKey: "eval.l1", qKey: "eval.l1q" },
  { nameKey: "eval.l2", qKey: "eval.l2q" },
  { nameKey: "eval.l3", qKey: "eval.l3q" },
  { nameKey: "eval.l4", qKey: "eval.l4q" },
  { nameKey: "eval.l5", qKey: "eval.l5q" },
  { nameKey: "eval.l6", qKey: "eval.l6q" },
];

export default async function EvaluationsPage() {
  const locale = await serverLocale();
  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow={t(locale, "eval.eyebrow")}
        title={t(locale, "eval.title")}
        description={t(locale, "eval.desc")}
        actions={
          <Link href="/analysis"><Button size="sm">{t(locale, "common.backToAnalysis")}</Button></Link>
        }
      />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {levels.map((l, i) => (
          <Card key={l.nameKey}>
            <CardContent className="p-4 pt-4">
              <p className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                {t(locale, "eval.level").replace("{n}", String(i + 1))}
              </p>
              <p className="mt-1 text-sm font-semibold">{`L${i + 1} · ${t(locale, l.nameKey)}`}</p>
              <p className="mt-1 text-xs leading-5 text-zinc-500">{t(locale, l.qKey)}</p>
            </CardContent>
          </Card>
        ))}
      </div>
      <EmptyState
        title={t(locale, "eval.emptyTitle")}
        description={t(locale, "eval.emptyBody")}
        action={<Link href="/analysis"><Button size="sm">{t(locale, "common.backToAnalysis")}</Button></Link>}
      />
    </div>
  );
}
