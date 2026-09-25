"use client";

import { DataTable } from "@/app/components/data/DataTable";

type Tracked = {
  id: string;
  name: string;
  run_id: string;
  created_at: string | null;
};

// Client wrapper: column render functions cannot cross the server→client
// boundary, so they are defined here next to the client DataTable.
export function TrackedExperimentsTable({ rows }: { rows: Tracked[] }) {
  return (
    <DataTable<Tracked>
      caption="API-tracked experiments"
      keyOf={(r) => r.id}
      rows={rows}
      columns={[
        { key: "name", header: "Name", render: (r) => <span className="font-medium">{r.name}</span> },
        { key: "id", header: "ID", render: (r) => <code className="font-mono text-xs">{r.id}</code> },
        { key: "run_id", header: "Run", render: (r) => <code className="font-mono text-xs">{r.run_id}</code> },
      ]}
    />
  );
}
