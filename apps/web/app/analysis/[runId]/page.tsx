import { apiUrl } from "@/lib/api";

type RunDetail = {
  id: string;
  status: string;
  user_query: string;
  state: {
    objective: string;
    plan: { id: string; name: string; tool: string; description: string }[];
    tool_calls: { call_id: string; tool: string; status: string; duration_ms: number; error?: string | null; input: Record<string, unknown>; output?: unknown }[];
    evidence: { id: string; claim: string; source_type: string; source_id: string; confidence: number; result: Record<string, unknown> }[];
    insights: { id: string; finding: string; evidence_ids: string[]; limitation?: string }[];
    validation_results: { check: string; passed: boolean; message: string }[];
    report_markdown: string | null;
    artifacts: { id: string; type: string; path: string; metadata: Record<string, unknown> }[];
  } | null;
};

async function fetchRun(id: string): Promise<RunDetail | null> {
  const res = await fetch(apiUrl(`/api/v1/analysis/${id}`), { cache: "no-store" });
  if (!res.ok) return null;
  return (await res.json()) as RunDetail;
}

function StatusDot({ status }: { status: string }) {
  const ok = status === "COMPLETED";
  const fail = status === "FAILED";
  return (
    <span className={`inline-block rounded px-2 py-1 text-xs ${ok ? "bg-green-100 text-green-700" : fail ? "bg-red-100 text-red-700" : "bg-zinc-100"}`}>
      {status}
    </span>
  );
}

export default async function TracePage({ params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;
  const run = await fetchRun(runId);
  if (!run) return <p className="text-sm text-red-600">Run not found or the DSA API is unavailable.</p>;

  const st = run.state;
  const reportUrl = apiUrl(`/api/v1/analysis/${runId}/report?format=markdown`);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-zinc-500">Step 3 · Inspect the evidence</p>
          <h1 className="text-lg font-semibold">Analysis {runId.slice(0, 12)} <StatusDot status={run.status} /></h1>
        </div>
        {st?.report_markdown && (
          <a href={reportUrl} className="rounded border bg-white px-3 py-2 text-sm font-medium" target="_blank" rel="noreferrer">
            Download report ↗
          </a>
        )}
      </div>
      <p className="text-sm text-zinc-600">Objective: {st?.objective || run.user_query}</p>

      <div className="rounded border bg-white p-4">
        <h2 className="font-medium">Plan</h2>
        <ol className="mt-2 list-decimal pl-5 text-sm">
          {(st?.plan || []).map((s) => (
            <li key={s.id}>
              <span className="font-mono text-xs">{s.tool}</span> — {s.name}
              <span className="text-zinc-500"> · {s.description}</span>
            </li>
          ))}
        </ol>
      </div>

      <div className="rounded border bg-white p-4">
        <h2 className="font-medium">Agent trace</h2>
        <table className="mt-2 w-full text-sm">
          <thead className="text-left text-zinc-500"><tr><th>Tool</th><th>Status</th><th>Duration</th><th>Call</th></tr></thead>
          <tbody>
            {(st?.tool_calls || []).map((tc) => (
              <tr key={tc.call_id} className="border-t">
                <td className="py-1 font-mono text-xs">{tc.tool}</td>
                <td><span className={`rounded px-1 text-xs ${tc.status === "ok" ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"}`}>{tc.status}</span></td>
                <td>{tc.duration_ms}ms</td>
                <td className="font-mono text-xs">{tc.call_id}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="rounded border bg-white p-4">
        <div className="flex items-center justify-between">
          <h2 className="font-medium">Evidence</h2>
          <span className="text-xs text-zinc-500">Claim → computation → dataset</span>
        </div>
        <ul className="mt-2 space-y-2 text-sm">
          {(st?.evidence || []).map((ev) => (
            <li key={ev.id} className="rounded border p-2">
              <div className="font-mono text-xs">{ev.id} · {ev.source_type} → {ev.source_id} · conf {ev.confidence.toFixed(2)}</div>
              <div className="mt-1 font-medium">{ev.claim}</div>
              <div className="mt-1 text-xs text-zinc-500">{JSON.stringify(ev.result).slice(0, 300)}</div>
            </li>
          ))}
          {(st?.evidence || []).length === 0 && <li className="text-zinc-500">No evidence.</li>}
        </ul>
      </div>

      <div className="rounded border bg-white p-4">
        <h2 className="font-medium">Insights</h2>
        <ul className="mt-2 space-y-2 text-sm">
          {(st?.insights || []).map((ins) => (
            <li key={ins.id} className="rounded border p-2">
              <div>{ins.finding}</div>
              <div className="text-xs text-zinc-500">Evidence: {ins.evidence_ids.join(", ") || "—"} {ins.limitation ? `· ${ins.limitation}` : ""}</div>
            </li>
          ))}
        </ul>
      </div>

      <div className="rounded border bg-white p-4">
        <h2 className="font-medium">Validation</h2>
        <ul className="mt-2 text-sm">
          {(st?.validation_results || []).map((v, i) => (
            <li key={i} className={v.passed ? "text-green-700" : "text-red-600"}>{v.passed ? "✓" : "✗"} {v.check}: {v.message}</li>
          ))}
        </ul>
      </div>

      <div className="rounded border bg-white p-4">
        <h2 className="font-medium">Artifacts</h2>
        <ul className="mt-2 text-sm">
          {(st?.artifacts || []).map((a) => <li key={a.id} className="font-mono text-xs">{a.type} — {a.path}</li>)}
        </ul>
      </div>

      {st?.report_markdown && (
        <div className="rounded border bg-white p-4">
          <h2 className="font-medium">Report preview</h2>
          <pre className="mt-2 whitespace-pre-wrap text-sm">{st.report_markdown.slice(0, 6000)}</pre>
          <a href={reportUrl} className="mt-3 inline-block text-sm font-medium underline" target="_blank" rel="noreferrer">
            Open full Markdown report ↗
          </a>
        </div>
      )}
    </div>
  );
}
