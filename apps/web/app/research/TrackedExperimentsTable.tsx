"use client";

import { DataTable } from "@/app/components/data/DataTable";
import { useLocale } from "@/app/lib/LocaleProvider";
import { t } from "@/lib/locale";

type Tracked = {
  id: string;
  name: string;
  run_id: string;
  created_at: string | null;
};

// Client wrapper: column render functions cannot cross the server→client
// boundary, so they are defined here next to the client DataTable.
export function TrackedExperimentsTable({ rows }: { rows: Tracked[] }) {
  const locale = useLocale();
  return (
    <DataTable<Tracked>
      caption={t(locale, "rs.trackedCaption")}
      keyOf={(r) => r.id}
      rows={rows}
      columns={[
        { key: "name", header: t(locale, "col.name"), render: (r) => <span className="font-medium">{r.name}</span> },
        { key: "id", header: t(locale, "col.id"), render: (r) => <code className="font-mono text-xs">{r.id}</code> },
        { key: "run_id", header: t(locale, "col.run"), render: (r) => <code className="font-mono text-xs">{r.run_id}</code> },
      ]}
    />
  );
}
