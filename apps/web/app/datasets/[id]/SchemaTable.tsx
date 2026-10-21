"use client";

import { Badge } from "@/app/components/ui/badge";
import { DataTable } from "@/app/components/data/DataTable";
import { useLocale } from "@/app/lib/LocaleProvider";
import { t } from "@/lib/locale";

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
  const locale = useLocale();
  return (
    <DataTable<SchemaColumn & Record<string, unknown>>
      caption={t(locale, "dsd.schemaCaption").replace("{name}", filename)}
      keyOf={(c) => c.name}
      rows={columns as (SchemaColumn & Record<string, unknown>)[]}
      columns={[
        { key: "name", header: t(locale, "col.column"), sortable: true, render: (c) => <code className="font-mono text-xs">{c.name}</code> },
        { key: "dtype", header: t(locale, "col.dtype"), sortable: true, render: (c) => <span className="font-mono text-xs">{c.dtype}</span> },
        { key: "kind", header: t(locale, "col.kind"), sortable: true, render: (c) => <Badge variant="outline">{c.kind}</Badge> },
        { key: "null_count", header: t(locale, "col.nulls"), sortable: true, render: (c) => <span className="tabular-nums">{c.null_count}</span> },
        { key: "unique_count", header: t(locale, "col.uniques"), sortable: true, render: (c) => <span className="tabular-nums">{c.unique_count ?? "—"}</span> },
      ]}
    />
  );
}
