"use client";

import { useEffect, useState } from "react";
import { API_BASE_URL, apiUrl } from "@/lib/api";

type Dataset = {
  id: string;
  filename: string;
  format: string;
  rows: number | null;
  cols: number | null;
  created_at: string | null;
};

export default function DatasetsPage() {
  const [items, setItems] = useState<Dataset[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setErr(null);
    try {
      const res = await fetch(apiUrl("/api/v1/datasets/"));
      if (!res.ok) {
        setErr(await res.text());
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

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;

    setUploading(true);
    setErr(null);
    const fd = new FormData();
    fd.append("file", f);

    try {
      const res = await fetch(apiUrl("/api/v1/datasets/"), {
        method: "POST",
        body: fd,
      });
      if (!res.ok) {
        setErr(await res.text());
        return;
      }
      await load();
    } catch (e) {
      setErr(`Upload failed because the DSA API at ${API_BASE_URL} is unavailable. ${String(e)}`);
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <p className="text-xs font-medium uppercase tracking-[0.18em] text-zinc-500">Step 1</p>
        <h1 className="text-lg font-semibold">Bring a dataset</h1>
        <p className="mt-1 text-sm text-zinc-600">Upload a file, then ask DSA a real question about it.</p>
      </div>

      <div className="rounded border bg-white p-4">
        <label className="text-sm font-medium">Upload CSV, Parquet, JSON, or Excel (≤100MB)</label>
        <input
          type="file"
          accept=".csv,.parquet,.json,.xlsx,.xls"
          onChange={onUpload}
          className="mt-2 block text-sm"
        />
        {uploading && <p className="mt-2 text-sm text-zinc-600">Uploading…</p>}
        {err && <p className="mt-2 text-sm text-red-600">{err}</p>}
      </div>

      <div className="rounded border bg-white p-4">
        {loading ? (
          <p className="text-sm text-zinc-500">Loading datasets…</p>
        ) : items.length === 0 ? (
          <div className="space-y-2">
            <p className="text-sm text-zinc-500">No datasets yet. Upload one above to begin the demo flow.</p>
            <p className="text-xs text-zinc-400">
              API diagnostics: {" "}
              <a href={apiUrl("/health")} className="underline" target="_blank" rel="noreferrer">/health</a>
              {" · "}
              <a href={apiUrl("/metrics")} className="underline" target="_blank" rel="noreferrer">/metrics</a>
              {" · "}
              <a href={apiUrl("/version")} className="underline" target="_blank" rel="noreferrer">/version</a>
            </p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-left text-zinc-500">
              <tr><th>File</th><th>Format</th><th>Rows</th><th>Cols</th><th></th></tr>
            </thead>
            <tbody>
              {items.map((d) => (
                <tr key={d.id} className="border-t">
                  <td className="py-2">{d.filename}</td>
                  <td>{d.format}</td>
                  <td>{d.rows ?? "-"}</td>
                  <td>{d.cols ?? "-"}</td>
                  <td>
                    <a href={`/datasets/${d.id}`} className="underline">View</a>
                    {" · "}
                    <a href={`/analysis?dataset=${d.id}`} className="font-medium underline">Analyze →</a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
