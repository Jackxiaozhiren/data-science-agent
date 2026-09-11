import Link from "next/link";
import { Plug2 } from "lucide-react";
import { apiUrl } from "@/lib/api";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/app/components/ui/card";
import { Badge } from "@/app/components/ui/badge";
import { PageHeader } from "@/app/components/data/PageHeader";
import { StatCard } from "@/app/components/data/StatCard";
import { ErrorState } from "@/app/components/data/States";
import { McpTable, type McpTool } from "@/app/mcp/McpTable";

const endpoints = [
  { m: "GET", p: "/mcp/tools", b: "List the stateless tools." },
  { m: "POST", p: "/mcp/call", b: "Call one tool with explicit handles." },
  { m: "POST", p: "/mcp", b: "JSON-RPC tools/list and tools/call." },
];

async function fetchTools(): Promise<{ tools: McpTool[]; unreachable: boolean }> {
  try {
    const res = await fetch(apiUrl("/mcp/tools"), { cache: "no-store" });
    if (!res.ok) return { tools: [], unreachable: false };
    const d = (await res.json()) as { tools: McpTool[] };
    return { tools: d.tools ?? [], unreachable: false };
  } catch {
    return { tools: [], unreachable: true };
  }
}

export default async function MCPPage() {
  const { tools, unreachable } = await fetchTools();
  const byClass = new Map<string, number>();
  for (const t of tools) byClass.set(t.tool_class, (byClass.get(t.tool_class) ?? 0) + 1);

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Reference · Step 3"
        title="MCP 2026-07-28"
        description={`Stateless core · ${tools.length || 19} tools · No Mcp-Session-Id · cacheHints via cache_hint · Explicit handles: run_id / dataset_id.`}
        actions={
          <Link href="/analysis"><Button size="sm">Back to Analysis →</Button></Link>
        }
      />
      {unreachable && (
        <ErrorState message="Could not reach the MCP endpoint — showing the static reference below instead of a blank page." />
      )}
      {tools.length > 0 ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[...byClass.entries()].map(([cls, n]) => (
              <StatCard key={cls} label={cls} value={String(n)} hint="tools" icon={Plug2} />
            ))}
          </div>
          <Card>
            <CardContent className="p-3 pt-3 sm:p-4 sm:pt-4">
              <McpTable tools={tools} />
            </CardContent>
          </Card>
        </>
      ) : (
        !unreachable && (
          <Card>
            <CardContent className="p-4 pt-4 text-sm text-zinc-500">The MCP endpoint returned no tools.</CardContent>
          </Card>
        )
      )}
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
    </div>
  );
}
