export default function MCPPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">MCP 2026-07-28</h1>
      <p className="text-sm text-zinc-600">Stateless core · 17 tools (SAFE_READ/ANALYSIS/COMPUTE/WRITE_ARTIFACT) · No Mcp-Session-Id · cacheHints via cache_hint · Explicit handles: run_id / dataset_id.</p>
      <div className="rounded border bg-white p-4 text-sm">Endpoints: <code>GET /mcp/tools</code> · <code>POST /mcp/call</code> · <code>POST /mcp</code> (tools/list, tools/call)</div>
    </div>
  );
}
