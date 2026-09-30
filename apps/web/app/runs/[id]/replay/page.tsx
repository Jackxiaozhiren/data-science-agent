import Link from "next/link";
import { History } from "lucide-react";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/app/components/ui/card";
import { PageHeader } from "@/app/components/data/PageHeader";
import { EmptyState } from "@/app/components/data/States";

export default async function ReplayPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Step 3 · Replay"
        title={`Replay — ${id.slice(0, 12)}`}
        description="Inspect the recorded trace of this run. Replay and fork are not wired in this build: the engine has no checkpoint API exposed yet."
        actions={
          <Link href={`/analysis/${id}`}><Button variant="secondary" size="sm">Inspect trace →</Button></Link>
        }
      />
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Checkpoints</CardTitle>
          <CardDescription className="text-xs">Checkpoint-grounded replay is under construction — the trace inspector below is fully working.</CardDescription>
        </CardHeader>
        <CardContent>
          <EmptyState
            icon={<History className="size-5 text-zinc-400" aria-hidden />}
            title="Replay controls are under construction"
            description="Replay and fork controls are not wired in this build: no checkpoint API exists yet. Meanwhile, inspect the full evidence chain."
            action={
              <Link href={`/analysis/${id}`}>
                <Button size="sm">Back to Analysis →</Button>
              </Link>
            }
          />
        </CardContent>
      </Card>
    </div>
  );
}
