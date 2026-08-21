type RunItem = { id: string; dataset_id: string; status: string; user_query: string; created_at: string | null };

async function fetchRuns(): Promise<RunItem[]> {
  try {
    const res = await fetch("http://localhost:8000/api/v1/analysis/", { cache: "no-store" });
    if (!res.ok) return [];
    const d = (await res.json()) as { analyses: RunItem[] };
    return d.analyses;
  } catch { return []; }
}

export default async function ReportsPage() {
  const runs = await fetchRuns();
  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold">Reports</h1>
      <div className="rounded border bg-white p-4">
        <table className="w-full text-sm">
          <thead className="text-left text-zinc-500"><tr><th>Run</th><th>Status</th><th>Query</th><th>Created</th></tr></thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.id} className="border-t">
                <td className="font-mono text-xs"><a href={`/analysis/${r.id}`} className="underline">{r.id.slice(0, 14)}</a></td>
                <td><span className={`rounded px-1 text-xs ${r.status === "COMPLETED" ? "bg-green-50" : "bg-zinc-100"}`}>{r.status}</span></td>
                <td className="max-w-[360px] truncate">{r.user_query}</td>
                <td className="text-xs text-zinc-500">{r.created_at?.slice(0, 19) || "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {runs.length === 0 && <p className="mt-2 text-sm text-zinc-500">No runs.</p>}
      </div>
    </div>
  );
}
