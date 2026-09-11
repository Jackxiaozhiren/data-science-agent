import Link from "next/link";
import { FileText } from "lucide-react";
import { apiUrl } from "@/lib/api";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent } from "@/app/components/ui/card";
import { PageHeader } from "@/app/components/data/PageHeader";
import { EmptyState, ErrorState } from "@/app/components/data/States";
import { ReportsTable } from "@/app/reports/ReportsTable";

type RunItem = { id: string; dataset_id: string; status: string; user_query: string; created_at: string | null };

async function fetchRuns(): Promise<{ runs: RunItem[]; unreachable: boolean }> {
  try {
    const res = await fetch(apiUrl("/api/v1/analysis/"), { cache: "no-store" });
    if (!res.ok) return { runs: [], unreachable: false };
    const d = (await res.json()) as { analyses: RunItem[] };
    return { runs: d.analyses, unreachable: false };
  } catch {
    return { runs: [], unreachable: true };
  }
}

export default async function ReportsPage() {
  const { runs, unreachable } = await fetchRuns();
  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Step 3 · Reports"
        title="Reports"
        description="Every completed run preserves a reproducible Markdown report. Open a run to preview or download it."
        actions={
          <Link href="/analysis"><Button size="sm">New analysis →</Button></Link>
        }
      />
      {unreachable && (
        <ErrorState message="Could not reach the DSA API — showing an empty report list instead of a blank page." />
      )}
      <Card>
        <CardContent className="p-3 pt-3 sm:p-4 sm:pt-4">
          {runs.length === 0 ? (
            <EmptyState
              icon={<FileText className="size-5 text-zinc-400" aria-hidden />}
              title="No reports yet"
              description="Reports appear here once an analysis run completes."
              action={<Link href="/analysis"><Button size="sm">Start your first analysis →</Button></Link>}
            />
          ) : (
            <ReportsTable runs={runs} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
