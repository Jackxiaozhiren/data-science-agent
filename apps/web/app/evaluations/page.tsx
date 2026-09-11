import Link from "next/link";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent } from "@/app/components/ui/card";
import { PageHeader } from "@/app/components/data/PageHeader";
import { EmptyState } from "@/app/components/data/States";

const levels = [
  { t: "L1 · Tool Execution", b: "Did each tool run and return?" },
  { t: "L2 · Numerical", b: "Are the numbers right?" },
  { t: "L3 · Statistical Method", b: "Was the right test used?" },
  { t: "L4 · Interpretation", b: "Is the reading of results sound?" },
  { t: "L5 · Evidence", b: "Does each claim point at evidence?" },
  { t: "L6 · Final Report", b: "Is the report reproducible?" },
];

export default function EvaluationsPage() {
  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Evaluation · Step 3"
        title="Evaluations"
        description="V2 evaluation framework (EvaluationResultV2: 10 dims + 6-level breakdown). See docs/evaluation.md."
        actions={
          <Link href="/analysis"><Button size="sm">Back to Analysis →</Button></Link>
        }
      />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {levels.map((l, i) => (
          <Card key={l.t}>
            <CardContent className="p-4 pt-4">
              <p className="text-xs font-semibold uppercase tracking-wider text-zinc-400">Level {i + 1}</p>
              <p className="mt-1 text-sm font-semibold">{l.t}</p>
              <p className="mt-1 text-xs leading-5 text-zinc-500">{l.b}</p>
            </CardContent>
          </Card>
        ))}
      </div>
      <EmptyState
        title="Live evaluation results are under construction"
        description="The framework (10 dims + 6 levels) is specified — scored runs will be listed here. Meanwhile, run an analysis to generate evidence."
        action={<Link href="/analysis"><Button size="sm">Back to Analysis →</Button></Link>}
      />
    </div>
  );
}
