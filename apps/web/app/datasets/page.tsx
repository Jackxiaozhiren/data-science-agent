"use client";

import * as React from "react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { FileUp, Database } from "lucide-react";
import { API_BASE_URL, apiUrl } from "@/lib/api";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/app/components/ui/card";
import { Progress } from "@/app/components/ui/feedback";
import { PageHeader } from "@/app/components/data/PageHeader";
import { DataTable } from "@/app/components/data/DataTable";
import { EmptyState, ErrorState, TableSkeleton } from "@/app/components/data/States";

type Dataset = {
  id: string;
  filename: string;
  format: string;
  rows: number | null;
  cols: number | null;
  created_at: string | null;
};

async function errorMessage(res: Response): Promise<string> {
  // Never dump raw response bodies: a misconfigured API URL returns a full
  // HTML error page, which is unreadable and leaks internals. One human line.
  let hint = "";
  try {
    const body = await res.text();
    const clean = body.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
    if (clean) hint = `: ${clean.slice(0, 160)}`;
  } catch {
    hint = "";
  }
  return `Request failed (HTTP ${res.status})${hint}. Check API diagnostics below.`;
}

export default function DatasetsPage() {
  const [items, setItems] = useState<Dataset[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [uploading, setUploading] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [dragging, setDragging] = useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);

  async function load() {
    setLoading(true);
    setErr(null);
    try {
      const res = await fetch(apiUrl("/api/v1/datasets/"));
      if (!res.ok) {
        setErr(await errorMessage(res));
        return;
      }
      const data = (await res.json()) as { datasets: Dataset[] };
      setItems(data.datasets);
    } catch (e) {
      setErr(`Could not reach the DSA API at ${API_BASE_URL}. ${String(e)}`);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function uploadFile(f: File) {
    setUploading(f.name);
    setErr(null);
    const fd = new FormData();
    fd.append("file", f);
    try {
      const res = await fetch(apiUrl("/api/v1/datasets/"), { method: "POST", body: fd });
      if (!res.ok) {
        setErr(await errorMessage(res));
        return;
      }
      await load();
    } catch (e) {
      setErr(`Upload failed because the DSA API at ${API_BASE_URL} is unavailable. ${String(e)}`);
    } finally {
      setUploading(null);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    await uploadFile(f);
  }

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Step 1 · Bring your data"
        title="Bring a dataset"
        description="Upload a file, then ask DSA a real question about it."
        actions={
          <Link href="/analysis">
            <Button variant="secondary" size="sm">Skip to Step 2 · Ask →</Button>
          </Link>
        }
      />

      {/* Drag-and-drop upload card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Upload CSV, Parquet, JSON, or Excel (≤100MB)</CardTitle>
          <CardDescription className="text-xs">Drag a file onto the drop zone or browse. Accepted: .csv .parquet .json .xlsx .xls</CardDescription>
        </CardHeader>
        <CardContent>
          <div
            role="button"
            tabIndex={0}
            aria-label="Upload dataset: drag a file here or press Enter to browse"
            onClick={() => inputRef.current?.click()}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
            }}
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              const f = e.dataTransfer.files?.[0];
              if (f) void uploadFile(f);
            }}
            className={`flex flex-col items-center rounded-xl border border-dashed px-6 py-8 text-center transition-colors ${dragging ? "border-emerald-400 bg-emerald-50/60" : "border-zinc-300 bg-zinc-50/60 hover:bg-zinc-50"}`}
          >
            <span className="flex size-10 items-center justify-center rounded-full bg-white shadow-sm" aria-hidden>
              <FileUp className="size-5 text-zinc-500" />
            </span>
            <p className="mt-3 text-sm font-medium">{dragging ? "Drop the file to upload" : "Drag & drop a file here, or browse"}</p>
            <p className="mt-1 text-xs text-zinc-500">Your file is sent to the DSA API for profiling — nothing is stored in the browser.</p>
            <Button variant="secondary" size="sm" className="mt-3" onClick={(e) => { e.stopPropagation(); inputRef.current?.click(); }}>
              Browse files
            </Button>
            <input ref={inputRef} type="file" accept=".csv,.parquet,.json,.xlsx,.xls" onChange={onUpload} className="sr-only" aria-label="Dataset file" />
          </div>
          {uploading && (
            <div className="mt-3 space-y-1.5" role="status" aria-label={`Uploading ${uploading}`}>
              <p className="truncate text-sm text-zinc-600">Uploading {uploading}…</p>
              <Progress value={60} />
            </div>
          )}
          {err && <div className="mt-3"><ErrorState message={err} retry={() => void load()} /></div>}
        </CardContent>
      </Card>

      {/* Table card */}
      <Card>
        <CardContent className="p-3 pt-3 sm:p-4 sm:pt-4">
          {loading ? (
            <TableSkeleton rows={5} />
          ) : items.length === 0 && !err ? (
            <EmptyState
              icon={<Database className="size-5 text-zinc-400" aria-hidden />}
              title="No datasets yet"
              description="Upload one above to begin the demo flow: Bring → Ask → Inspect."
              action={
                <Button size="sm" onClick={() => inputRef.current?.click()}>Upload your first dataset</Button>
              }
            />
          ) : items.length > 0 ? (
            <DataTable<Dataset & Record<string, unknown>>
              caption="Datasets"
              keyOf={(d) => d.id}
              rows={items as (Dataset & Record<string, unknown>)[]}
              columns={[
                { key: "filename", header: "File", sortable: true, render: (d) => <span className="block max-w-[220px] truncate font-medium" title={d.filename}>{d.filename}</span> },
                { key: "format", header: "Format", sortable: true, render: (d) => <code className="rounded bg-zinc-100 px-1.5 py-0.5 font-mono text-xs">{d.format || "—"}</code> },
                { key: "rows", header: "Rows", sortable: true, render: (d) => <span className="tabular-nums">{d.rows ?? "—"}</span> },
                { key: "cols", header: "Cols", sortable: true, render: (d) => <span className="tabular-nums">{d.cols ?? "—"}</span> },
                { key: "created_at", header: "Created", sortable: true, className: "hidden sm:table-cell", render: (d) => <span className="whitespace-nowrap text-xs text-zinc-500">{d.created_at?.slice(0, 19).replace("T", " ") || "—"}</span> },
                {
                  key: "__actions", header: "", render: (d) => (
                    <span className="flex shrink-0 items-center gap-3 whitespace-nowrap">
                      <Link href={`/datasets/${d.id}`} className="text-xs font-medium text-zinc-600 underline hover:text-zinc-900">View</Link>
                      <Link href={`/analysis?dataset=${d.id}`} className="text-xs font-semibold text-zinc-900 underline">Analyze →</Link>
                    </span>
                  ),
                },
              ]}
            />
          ) : null}
        </CardContent>
      </Card>

      {/* API diagnostics */}
      <details className="rounded-xl border bg-white px-4 py-3 text-sm shadow-sm">
        <summary className="cursor-pointer text-xs font-medium text-zinc-500">API diagnostics</summary>
        <p className="mt-2 text-xs leading-5 text-zinc-500">
          Base URL: <code className="font-mono">{API_BASE_URL}</code>
          {" · "}
          <a href={apiUrl("/health")} className="underline" target="_blank" rel="noreferrer">/health</a>
          {" · "}
          <a href={apiUrl("/metrics")} className="underline" target="_blank" rel="noreferrer">/metrics</a>
          {" · "}
          <a href={apiUrl("/version")} className="underline" target="_blank" rel="noreferrer">/version</a>
        </p>
      </details>
    </div>
  );
}
