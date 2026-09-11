"use client";

import { Badge } from "@/app/components/ui/badge";
import { DataTable } from "@/app/components/data/DataTable";

export type SchemaColumn = {
  name: string;
  dtype: string;
  kind: string;
  null_count: number;
  unique_count: number | null;
};

// Client wrapper: column render functions cannot cross the server→client
// boundary, so they are defined here next to the client DataTable.
export function SchemaTable({ columns, filename }: { columns: SchemaColumn[]; filename: string }) {
  return (
    <DataTable<SchemaColumn & Record<string, unknown>>
      caption={`Schema of ${filename}`}
      keyOf={(c) => c.name}
      rows={columns as (SchemaColumn & Record<string, unknown>)[]}
      columns={[
        { key: "name", header: "Column", sortable: true, render: (c) => <code className="font-mono text-xs">{c.name}</code> },
        { key: "dtype", header: "Dtype", sortable: true, render: (c) => <span className="font-mono text-xs">{c.dtype}</span> },
        { key: "kind", header: "Kind", sortable: true, render: (c) => <Badge variant="outline">{c.kind}</Badge> },
        { key: "null_count", header: "Nulls", sortable: true, render: (c) => <span className="tabular-nums">{c.null_count}</span> },
        { key: "unique_count", header: "Uniques", sortable: true, render: (c) => <span className="tabular-nums">{c.unique_count ?? "—"}</span> },
      ]}
    />
  );
}
