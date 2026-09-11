"use client";

import { DataTable } from "@/app/components/data/DataTable";

// Client wrapper: column render functions cannot cross the server→client
// boundary, so they are defined here next to the client DataTable.
export function ExperimentsTable({ files }: { files: string[] }) {
  return (
    <DataTable<{ name: string } & Record<string, unknown>>
      caption="Recent ablation experiments"
      keyOf={(r) => r.name}
      rows={files.map((name) => ({ name }))}
      columns={[{ key: "name", header: "File", render: (r) => <code className="font-mono text-xs">{r.name}</code> }]}
    />
  );
}
