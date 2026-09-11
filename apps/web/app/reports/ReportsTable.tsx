"use client";

import * as React from "react";
import Link from "next/link";
import { DataTable } from "@/app/components/data/DataTable";
import { StatusBadge } from "@/app/components/data/StatusBadge";
import { Input, Select } from "@/app/components/ui/input";

export type ReportRow = { id: string; status: string; user_query: string; created_at: string | null };

// Client wrapper: column render functions cannot cross the server→client
// boundary, so they are defined here next to the client DataTable.
// Includes search + status filter + newest-first default.
export function ReportsTable({ runs }: { runs: ReportRow[] }) {
  const [q, setQ] = React.useState("");
  const [status, setStatus] = React.useState("all");

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

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <label htmlFor="reports-search" className="sr-only">Search reports</label>
        <Input
          id="reports-search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search query or run id…"
          className="h-8 w-52"
        />
        <label htmlFor="reports-status" className="sr-only">Filter by status</label>
        <Select id="reports-status" value={status} onChange={(e) => setStatus(e.target.value)} className="h-8 w-40" aria-label="Filter by status">
          <option value="all">All statuses</option>
          <option value="COMPLETED">Completed</option>
          <option value="FAILED">Failed</option>
          <option value="RUNNING">Running</option>
        </Select>
        <span className="text-xs text-zinc-400" aria-live="polite">{filtered.length} of {runs.length} reports</span>
      </div>
      {filtered.length === 0 ? (
        <p className="rounded-xl border border-dashed border-zinc-200 bg-zinc-50/60 px-4 py-6 text-center text-sm text-zinc-500">
          No reports match — adjust the search or status filter.
        </p>
      ) : (
        <DataTable<ReportRow & Record<string, unknown>>
          caption="Reports"
          keyOf={(r) => r.id}
          rows={filtered as (ReportRow & Record<string, unknown>)[]}
          columns={[
            { key: "id", header: "Run", render: (r) => <Link href={`/analysis/${r.id}`} className="font-mono text-xs underline">{r.id.slice(0, 14)}</Link> },
            { key: "status", header: "Status", sortable: true, render: (r) => <StatusBadge status={r.status} /> },
            { key: "user_query", header: "Query", render: (r) => <span className="block max-w-[360px] truncate" title={r.user_query}>{r.user_query}</span> },
            { key: "created_at", header: "Created", sortable: true, render: (r) => <span className="whitespace-nowrap text-xs text-zinc-500">{r.created_at?.slice(0, 19).replace("T", " ") || "—"}</span> },
          ]}
        />
      )}
    </div>
  );
}
