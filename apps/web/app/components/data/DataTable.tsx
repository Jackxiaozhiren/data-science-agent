"use client";

import * as React from "react";
import { ArrowUpDown } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow, TableWrapper } from "@/app/components/ui/table";
import { EmptyState } from "@/app/components/data/States";

export type DataTableColumn<T> = {
  key: string;
  header: string;
  sortable?: boolean;
  className?: string;
  render?: (row: T) => React.ReactNode;
};

// Unified DataTable: sorting + empty state + horizontal scroll for 390px.
export function DataTable<T extends Record<string, unknown>>({
  columns,
  rows,
  keyOf,
  empty,
  caption,
}: {
  columns: DataTableColumn<T>[];
  rows: T[];
  keyOf: (row: T, index: number) => string;
  empty?: React.ReactNode;
  caption?: string;
}) {
  const [sortKey, setSortKey] = React.useState<string | null>(null);
  const [sortDir, setSortDir] = React.useState<"asc" | "desc">("asc");

  const sorted = React.useMemo(() => {
    if (!sortKey) return rows;
    const copy = [...rows];
    copy.sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      const cmp = String(av).localeCompare(String(bv), undefined, { numeric: true });
      return sortDir === "asc" ? cmp : -cmp;
    });
    return copy;
  }, [rows, sortKey, sortDir]);

  if (rows.length === 0) {
    return <>{empty ?? <EmptyState title="Nothing here yet" description="No rows to display." />}</>;
  }

  return (
    <TableWrapper>
      <Table>
        {caption && <caption className="sr-only">{caption}</caption>}
        <TableHeader>
          <TableRow>
            {columns.map((c) => (
              <TableHead key={c.key} className={c.className}>
                {c.sortable ? (
                  <button
                    type="button"
                    onClick={() => {
                      if (sortKey === c.key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
                      else {
                        setSortKey(c.key);
                        setSortDir("asc");
                      }
                    }}
                    aria-label={`Sort by ${c.header}`}
                    className="inline-flex items-center gap-1 hover:text-zinc-900"
                  >
                    {c.header}
                    <ArrowUpDown className="size-3" aria-hidden />
                  </button>
                ) : (
                  c.header
                )}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.map((row, i) => (
            <TableRow key={keyOf(row, i)}>
              {columns.map((c) => (
                <TableCell key={c.key} className={c.className}>
                  {c.render ? c.render(row) : String(row[c.key] ?? "—")}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableWrapper>
  );
}
