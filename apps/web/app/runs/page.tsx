export default function RunsPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Runs</h1>
      <p className="text-sm text-zinc-600">Analysis inspector: Overview, Timeline, Agent Graph, Tool Calls, Evidence, Artifacts, Checkpoints, Failures, Validation, Reproduction.</p>
      <div className="rounded border bg-white p-4 text-sm">Trace from <code>GET /api/v1/analysis/{"{id}"}</code> · SSE: <code>/events</code> · Evidence graph at <code>/evidence/{"{evidence_id}"}</code></div>
    </div>
  );
}
