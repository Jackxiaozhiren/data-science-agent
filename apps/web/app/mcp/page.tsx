import Link from "next/link";
import { Plug2 } from "lucide-react";
import { apiUrl, classifyResponse, failurePresentation, type ApiFailure } from "@/lib/api";
import { serverFetch, serverLocale } from "@/lib/serverApi";
import { t, type Locale } from "@/lib/locale";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/app/components/ui/card";
import { Badge } from "@/app/components/ui/badge";
import { PageHeader } from "@/app/components/data/PageHeader";
import { StatCard } from "@/app/components/data/StatCard";
import { ErrorState } from "@/app/components/data/States";
import { McpTable, type McpTool } from "@/app/mcp/McpTable";

const endpoints = [
  { m: "GET", p: "/mcp/tools", bKey: "mcp.epTools" },
  { m: "POST", p: "/mcp/call", bKey: "mcp.epCall" },
  { m: "POST", p: "/mcp", bKey: "mcp.epRpc" },
];

// Inherits the shared wording, and keeps this page's own line for the transport case: the static
// endpoint reference below is what a reader gets when no response could be read at all.
function mcpMessages(locale: Locale): Record<ApiFailure, string> {
  return { ...failurePresentation(locale), transport: t(locale, "mcp.transport") };
}

async function fetchTools(): Promise<{ tools: McpTool[]; failure: ApiFailure | null }> {
  try {
    const res = await serverFetch("/mcp/tools", { cache: "no-store" });
    const failure = classifyResponse(res);
    if (failure) return { tools: [], failure };
    const d = (await res.json()) as { tools: McpTool[] };
    return { tools: d.tools ?? [], failure: null };
  } catch {
    return { tools: [], failure: "transport" };
  }
}

export default async function MCPPage() {
  const locale = await serverLocale();
  const messages = mcpMessages(locale);
  const { tools, failure } = await fetchTools();
  const byClass = new Map<string, number>();
  for (const t of tools) byClass.set(t.tool_class, (byClass.get(t.tool_class) ?? 0) + 1);

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow={t(locale, "mcp.eyebrow")}
        title="MCP 2026-07-28"
        description={
          tools.length
            ? t(locale, "mcp.summary").replace("{n}", String(tools.length))
            : t(locale, "mcp.summaryNoTools")
        }
        actions={
          <Link href="/analysis"><Button size="sm">{t(locale, "common.backToAnalysis")}</Button></Link>
        }
      />
      {failure && <ErrorState message={messages[failure]} />}
      {tools.length > 0 ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[...byClass.entries()].map(([cls, n]) => (
              <StatCard key={cls} label={cls} value={String(n)} hint={t(locale, "mcp.toolsHint")} icon={Plug2} />
            ))}
          </div>
          <Card>
            <CardContent className="p-3 pt-3 sm:p-4 sm:pt-4">
              <McpTable tools={tools} />
            </CardContent>
          </Card>
        </>
      ) : (
        failure === null && (
          <Card>
            <CardContent className="p-4 pt-4 text-sm text-zinc-500">{t(locale, "mcp.noTools")}</CardContent>
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
            <CardContent className="-mt-2 text-xs leading-5 text-zinc-500">{t(locale, e.bKey)}</CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
