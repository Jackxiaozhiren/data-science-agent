"use client";

import Link from "next/link";
import { DataTable } from "@/app/components/data/DataTable";
import { StatusBadge } from "@/app/components/data/StatusBadge";

export type ReportRow = { id: string; status: string; user_query: string; created_at: string | null };

// Client wrapper: column render functions cannot cross the server→client
// boundary, so they are defined here next to the client DataTable.
export function ReportsTable({ runs }: { runs: ReportRow[] }) {
  return (
    <DataTable<ReportRow & Record<string, unknown>>
      caption="Reports"
      keyOf={(r) => r.id}
      rows={runs as (ReportRow & Record<string, unknown>)[]}
      columns={[
        { key: "id", header: "Run", render: (r) => <Link href={`/analysis/${r.id}`} className="font-mono text-xs underline">{r.id.slice(0, 14)}</Link> },
        { key: "status", header: "Status", sortable: true, render: (r) => <StatusBadge status={r.status} /> },
        { key: "user_query", header: "Query", render: (r) => <span className="block max-w-[360px] truncate" title={r.user_query}>{r.user_query}</span> },
        { key: "created_at", header: "Created", sortable: true, render: (r) => <span className="whitespace-nowrap text-xs text-zinc-500">{r.created_at?.slice(0, 19).replace("T", " ") || "—"}</span> },
      ]}
    />
  );
}
