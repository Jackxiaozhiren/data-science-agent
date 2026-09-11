"use client";

import * as React from "react";
import { Check, Copy } from "lucide-react";
import { Badge } from "@/app/components/ui/badge";
import { DataTable } from "@/app/components/data/DataTable";

export type McpTool = {
  name: string;
  description: string;
  tool_class: string;
  timeout_ms: number | null;
  idempotency: boolean | null;
};

// Client wrapper: column render functions cannot cross the server→client
// boundary, so they are defined here next to the client DataTable.
export function McpTable({ tools }: { tools: McpTool[] }) {
  const [copied, setCopied] = React.useState<string | null>(null);

  async function copyTemplate(name: string) {
    const template = JSON.stringify(
      { jsonrpc: "2.0", method: "tools/call", params: { name, arguments: {} } },
      null,
      2
    );
    try {
      await navigator.clipboard.writeText(template);
      setCopied(name);
      setTimeout(() => setCopied((cur) => (cur === name ? null : cur)), 1600);
    } catch {
      setCopied(null);
    }
  }

  return (
    <DataTable<McpTool & Record<string, unknown>>
      caption="MCP tools"
      keyOf={(t) => t.name}
      rows={tools as (McpTool & Record<string, unknown>)[]}
      columns={[
        { key: "name", header: "Tool", sortable: true, render: (t) => <code className="font-mono text-xs font-medium">{t.name}</code> },
        { key: "description", header: "Description", render: (t) => <span className="block max-w-[420px] text-xs leading-5 text-zinc-600" title={t.description}>{t.description}</span> },
        { key: "tool_class", header: "Class", sortable: true, render: (t) => <Badge variant="secondary">{t.tool_class}</Badge> },
        {
          key: "timeout_ms", header: "Timeout", sortable: true,
          render: (t) => <span className="whitespace-nowrap tabular-nums text-xs">{t.timeout_ms != null ? `${Math.round(t.timeout_ms / 1000)}s` : "—"}</span>,
        },
        {
          key: "idempotency", header: "Idempotent", render: (t) => (
            <span className="text-xs">{t.idempotency ? "yes" : "—"}</span>
          ),
        },
        {
          key: "__tpl", header: "", render: (t) => (
            <button
              type="button"
              onClick={() => copyTemplate(t.name)}
              title={`Copy tools/call template for ${t.name}`}
              aria-label={`Copy call template for ${t.name}`}
              className="inline-flex items-center gap-1 rounded-lg border border-zinc-200 px-2 py-1 text-xs text-zinc-600 hover:bg-zinc-50"
            >
              {copied === t.name ? <Check className="size-3.5" aria-hidden /> : <Copy className="size-3.5" aria-hidden />}
              {copied === t.name ? "Copied" : "Template"}
            </button>
          ),
        },
      ]}
    />
  );
}
