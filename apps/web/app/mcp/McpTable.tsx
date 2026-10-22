"use client";

import * as React from "react";
import { Check, Copy } from "lucide-react";
import { Badge } from "@/app/components/ui/badge";
import { DataTable } from "@/app/components/data/DataTable";
import { useLocale } from "@/app/lib/LocaleProvider";
import { t } from "@/lib/locale";

export type McpTool = {
  name: string;
  description: string;
  tool_class: string;
  timeout_ms: number | null;
  idempotency: boolean | null;
  inputSchema?: { properties?: Record<string, { type?: string | string[] }>; required?: string[] };
};

type JsonSchemaLike = NonNullable<McpTool["inputSchema"]>;

// The template used to carry `arguments: {}` for every tool, which meant the one thing it was copied for --
// a call that works -- failed on every tool with a required parameter. Placeholders are typed so the shape is
// right and obviously meant to be replaced.
function requiredArguments(schema: JsonSchemaLike | undefined): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  const required = new Set(schema?.required ?? []);
  for (const [key, spec] of Object.entries(schema?.properties ?? {})) {
    if (!required.has(key)) continue;
    const type = Array.isArray(spec?.type) ? spec.type.find((entry) => entry !== "null") : spec?.type;
    if (type === "integer" || type === "number") out[key] = 0;
    else if (type === "boolean") out[key] = true;
    else if (type === "array") out[key] = [];
    else if (type === "object") out[key] = {};
    else out[key] = "<required>";
  }
  return out;
}

// Client wrapper: column render functions cannot cross the server→client
// boundary, so they are defined here next to the client DataTable.
export function McpTable({ tools }: { tools: McpTool[] }) {
  const locale = useLocale();
  const [copied, setCopied] = React.useState<string | null>(null);

  async function copyTemplate(tool: McpTool) {
    const template = JSON.stringify(
      {
        jsonrpc: "2.0",
        method: "tools/call",
        params: { name: tool.name, arguments: requiredArguments(tool.inputSchema) },
      },
      null,
      2
    );
    try {
      await navigator.clipboard.writeText(template);
      setCopied(tool.name);
      setTimeout(() => setCopied((cur) => (cur === tool.name ? null : cur)), 1600);
    } catch {
      setCopied(null);
    }
  }

  const tpl = (key: string, name: string) => t(locale, key).replace("{name}", name);

  return (
    <DataTable<McpTool & Record<string, unknown>>
      caption={t(locale, "mcp.toolsCaption")}
      keyOf={(tool) => tool.name}
      rows={tools as (McpTool & Record<string, unknown>)[]}
      columns={[
        { key: "name", header: t(locale, "col.tool"), sortable: true, render: (tool) => <code className="font-mono text-xs font-medium">{tool.name}</code> },
        { key: "description", header: t(locale, "col.description"), render: (tool) => <span className="block max-w-[420px] text-xs leading-5 text-zinc-600" title={tool.description}>{tool.description}</span> },
        { key: "tool_class", header: t(locale, "col.class"), sortable: true, render: (tool) => <Badge variant="secondary">{tool.tool_class}</Badge> },
        {
          key: "timeout_ms", header: t(locale, "col.timeout"), sortable: true,
          render: (tool) => <span className="whitespace-nowrap tabular-nums text-xs">{tool.timeout_ms != null ? `${Math.round(tool.timeout_ms / 1000)}s` : "—"}</span>,
        },
        {
          key: "idempotency", header: t(locale, "col.idempotent"), render: (tool) => (
            <span className="text-xs">{tool.idempotency ? t(locale, "mcp.yes") : "—"}</span>
          ),
        },
        {
          key: "__tpl", header: "", render: (tool) => (
            <button
              type="button"
              onClick={() => copyTemplate(tool)}
              title={tpl("mcp.copyTitle", tool.name)}
              aria-label={tpl("mcp.copyAria", tool.name)}
              className="inline-flex items-center gap-1 rounded-lg border border-zinc-200 px-2 py-1 text-xs text-zinc-600 hover:bg-zinc-50"
            >
              {copied === tool.name ? <Check className="size-3.5" aria-hidden /> : <Copy className="size-3.5" aria-hidden />}
              {copied === tool.name ? t(locale, "copy.copied") : t(locale, "mcp.template")}
            </button>
          ),
        },
      ]}
    />
  );
}
