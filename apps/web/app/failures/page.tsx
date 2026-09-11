import Link from "next/link";
import { TriangleAlert } from "lucide-react";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/app/components/ui/card";
import { Badge } from "@/app/components/ui/badge";
import { PageHeader } from "@/app/components/data/PageHeader";
import { EmptyState } from "@/app/components/data/States";

const groups = [
  { t: "Planning failures", b: "F01–F05 · wrong plan, missing tool, bad parameters", v: "outline" as const },
  { t: "Execution failures", b: "F06–F10 · tool errors, retries, timeouts", v: "secondary" as const },
  { t: "Evidence failures", b: "F11–F15 · unsupported claims, missing links", v: "warning" as const },
];

export default function FailuresPage() {
  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Evaluation · Step 3"
        title="Failure Analysis"
        description="Taxonomy F01–F15 · Failure log · Recovery rate · Agent/tool with most errors · Average retries · Unsupported claim rate."
        actions={
          <Link href="/analysis"><Button size="sm">Back to Analysis →</Button></Link>
        }
      />
      <div className="grid gap-3 sm:grid-cols-3">
        {groups.map((g) => (
          <Card key={g.t}>
            <CardContent className="p-4 pt-4">
              <Badge variant={g.v}>{g.t}</Badge>
              <p className="mt-2 text-xs leading-5 text-zinc-500">{g.b}</p>
            </CardContent>
          </Card>
        ))}
      </div>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm"><TriangleAlert className="size-4 text-amber-600" aria-hidden /> Failure log</CardTitle>
          <CardDescription className="text-xs">Taxonomy source: packages/evidence/src/dsa_evidence/failure_taxonomy.py</CardDescription>
        </CardHeader>
        <CardContent>
          <EmptyState
            title="No failures logged in this environment"
            description="When runs fail, they will be classified F01–F15 here with recovery rates. Meanwhile, inspect a live trace."
            action={<Link href="/runs"><Button size="sm">View runs →</Button></Link>}
          />
        </CardContent>
      </Card>
    </div>
  );
}
