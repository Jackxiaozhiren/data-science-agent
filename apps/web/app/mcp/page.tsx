import Link from "next/link";
import { Plug2 } from "lucide-react";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/app/components/ui/card";
import { Badge } from "@/app/components/ui/badge";
import { PageHeader } from "@/app/components/data/PageHeader";
import { EmptyState } from "@/app/components/data/States";

const endpoints = [
  { m: "GET", p: "/mcp/tools", b: "List the 17 stateless tools." },
  { m: "POST", p: "/mcp/call", b: "Call one tool with explicit handles." },
  { m: "POST", p: "/mcp", b: "JSON-RPC tools/list and tools/call." },
];

export default function MCPPage() {
  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Reference · Step 3"
        title="MCP 2026-07-28"
        description="Stateless core · 17 tools (SAFE_READ/ANALYSIS/COMPUTE/WRITE_ARTIFACT) · No Mcp-Session-Id · cacheHints via cache_hint · Explicit handles: run_id / dataset_id."
        actions={
          <Link href="/analysis"><Button size="sm">Back to Analysis →</Button></Link>
        }
      />
      <div className="flex flex-wrap gap-2">
        {["SAFE_READ", "ANALYSIS", "COMPUTE", "WRITE_ARTIFACT"].map((t) => (
          <Badge key={t} variant="secondary"><Plug2 className="size-3" aria-hidden /> {t}</Badge>
        ))}
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        {endpoints.map((e) => (
          <Card key={e.p}>
            <CardHeader>
              <CardTitle className="font-mono text-sm"><Badge variant="outline">{e.m}</Badge> <span className="ml-1">{e.p}</span></CardTitle>
            </CardHeader>
            <CardContent className="-mt-2 text-xs leading-5 text-zinc-500">{e.b}</CardContent>
          </Card>
        ))}
      </div>
      <EmptyState
        title="Interactive MCP console is under construction"
        description="Tool calls currently run through the analysis workspace, which already pins run_id / dataset_id handles."
        action={<Link href="/analysis"><Button size="sm">Back to Analysis →</Button></Link>}
      />
    </div>
  );
}
