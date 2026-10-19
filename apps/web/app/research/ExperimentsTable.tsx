"use client";

import { DataTable } from "@/app/components/data/DataTable";
import { useLocale } from "@/app/lib/LocaleProvider";
import { t } from "@/lib/locale";

// Client wrapper: column render functions cannot cross the server→client
// boundary, so they are defined here next to the client DataTable.
export function ExperimentsTable({ files }: { files: string[] }) {
  const locale = useLocale();
  return (
    <DataTable<{ name: string } & Record<string, unknown>>
      caption={t(locale, "rs.recentCaption")}
      keyOf={(r) => r.name}
      rows={files.map((name) => ({ name }))}
      columns={[{ key: "name", header: t(locale, "col.file"), render: (r) => <code className="font-mono text-xs">{r.name}</code> }]}
    />
  );
}
