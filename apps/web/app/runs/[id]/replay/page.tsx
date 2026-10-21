import Link from "next/link";
import { History } from "lucide-react";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/app/components/ui/card";
import { PageHeader } from "@/app/components/data/PageHeader";
import { EmptyState } from "@/app/components/data/States";
import { serverLocale } from "@/lib/serverApi";
import { t } from "@/lib/locale";

export default async function ReplayPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const locale = await serverLocale();
  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow={t(locale, "replay.eyebrow")}
        title={t(locale, "replay.title").replace("{id}", id.slice(0, 12))}
        description={t(locale, "replay.desc")}
        actions={
          <Link href={`/analysis/${id}`}><Button variant="secondary" size="sm">{t(locale, "runDetail.inspectTrace")}</Button></Link>
        }
      />
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">{t(locale, "replay.checkpoints")}</CardTitle>
          <CardDescription className="text-xs">{t(locale, "replay.checkpointBody")}</CardDescription>
        </CardHeader>
        <CardContent>
          <EmptyState
            icon={<History className="size-5 text-zinc-400" aria-hidden />}
            title={t(locale, "replay.emptyTitle")}
            description={t(locale, "replay.emptyBody")}
            action={
              <Link href={`/analysis/${id}`}>
                <Button size="sm">{t(locale, "common.backToAnalysis")}</Button>
              </Link>
            }
          />
        </CardContent>
      </Card>
    </div>
  );
}
