"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { DataTable } from "@/app/components/data/DataTable";
import { StatusBadge } from "@/app/components/data/StatusBadge";
import { Input, Select } from "@/app/components/ui/input";
import { Button } from "@/app/components/ui/button";

export type RunRow = { id: string; status: string; user_query: string; created_at: string | null };

// Client wrapper: column render functions cannot cross the server→client
// boundary, so they are defined here next to the client DataTable.
// Includes search + status filter + newest-first default + compare-select.
export function RunsTable({ runs }: { runs: RunRow[] }) {
  const router = useRouter();
  const [q, setQ] = React.useState("");
  const [status, setStatus] = React.useState("all");
  const [selected, setSelected] = React.useState<string[]>([]);

  const filtered = React.useMemo(() => {
    const ql = q.trim().toLowerCase();
    return [...runs]
      .sort((a, b) => String(b.created_at ?? "").localeCompare(String(a.created_at ?? "")))
      .filter((r) => {
        if (status !== "all" && r.status.trim().toUpperCase() !== status) return false;
        if (ql && !`${r.id} ${r.user_query}`.toLowerCase().includes(ql)) return false;
        return true;
      });
  }, [runs, q, status]);

  // Drop selections that vanished from the filtered list.
  React.useEffect(() => {
    setSelected((sel) => sel.filter((id) => filtered.some((r) => r.id === id)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, status]);

  function toggle(id: string) {
    setSelected((sel) => (sel.includes(id) ? sel.filter((s) => s !== id) : sel.length >= 2 ? sel : [...sel, id]));
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <label htmlFor="runs-search" className="sr-only">Search runs</label>
        <Input
          id="runs-search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search query or run id…"
          className="h-8 w-52"
        />
        <label htmlFor="runs-status" className="sr-only">Filter by status</label>
        <Select id="runs-status" value={status} onChange={(e) => setStatus(e.target.value)} className="h-8 w-40" aria-label="Filter by status">
          <option value="all">All statuses</option>
          <option value="COMPLETED">Completed</option>
          <option value="FAILED">Failed</option>
          <option value="RUNNING">Running</option>
        </Select>
        <span className="text-xs text-zinc-400" aria-live="polite">{filtered.length} of {runs.length} runs</span>
        <span className="flex-1" />
        <Button
          variant="secondary"
          size="sm"
          disabled={selected.length !== 2}
          onClick={() => router.push(`/runs/compare?a=${selected[0]}&b=${selected[1]}`)}
          title={selected.length !== 2 ? "Select exactly two runs to compare" : "Compare selected runs"}
        >
          Compare ({selected.length}/2)
        </Button>
      </div>
      {filtered.length === 0 ? (
        <p className="rounded-xl border border-dashed border-zinc-200 bg-zinc-50/60 px-4 py-6 text-center text-sm text-zinc-500">
          No runs match — adjust the search or status filter.
        </p>
      ) : (
        <DataTable<RunRow & Record<string, unknown>>
          caption="Analysis runs"
          keyOf={(r) => r.id}
          rows={filtered as (RunRow & Record<string, unknown>)[]}
          columns={[
            {
              key: "__sel", header: "", render: (r) => (
                <input
                  type="checkbox"
                  checked={selected.includes(r.id)}
                  disabled={!selected.includes(r.id) && selected.length >= 2}
                  onChange={() => toggle(r.id)}
                  aria-label={`Select run ${r.id.slice(0, 12)} for comparison`}
                  className="size-4 accent-zinc-900"
                />
              ),
            },
            { key: "id", header: "Run", render: (r) => <Link href={`/analysis/${r.id}`} className="font-mono text-xs underline">{r.id.slice(0, 14)}</Link> },
            { key: "status", header: "Status", sortable: true, render: (r) => <StatusBadge status={r.status} /> },
            { key: "user_query", header: "Query", render: (r) => <span className="block max-w-[280px] truncate" title={r.user_query}>{r.user_query}</span> },
            { key: "created_at", header: "Created", sortable: true, render: (r) => <span className="whitespace-nowrap text-xs text-zinc-500">{r.created_at?.slice(0, 19).replace("T", " ") || "—"}</span> },
            { key: "__open", header: "", render: (r) => <Link href={`/analysis/${r.id}`} className="whitespace-nowrap text-xs font-semibold underline">Inspect →</Link> },
          ]}
        />
      )}
    </div>
  );
}
