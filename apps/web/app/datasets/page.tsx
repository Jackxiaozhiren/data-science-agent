"use client";
import { useEffect, useState } from "react";

type Dataset = { id: string; filename: string; format: string; rows: number | null; cols: number | null; created_at: string | null };

export default function DatasetsPage() {
  const [items, setItems] = useState<Dataset[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/api/v1/datasets/");
      if (!res.ok) { setErr(await res.text()); return; }
      const data = (await res.json()) as { datasets: Dataset[] };
      setItems(data.datasets);
    } catch (e) { setErr(String(e)); } finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    setUploading(true); setErr(null);
    const fd = new FormData();
    fd.append("file", f);
    const res = await fetch("http://localhost:8000/api/v1/datasets/", { method: "POST", body: fd });
    setUploading(false);
    if (!res.ok) { setErr(await res.text()); return; }
    await load();
  }

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold">Datasets</h1>
      <div className="rounded border bg-white p-4">
        <label className="text-sm">Upload (CSV / Parquet / JSON / Excel, ≤100MB)</label>
        <input type="file" accept=".csv,.parquet,.json,.xlsx,.xls" onChange={onUpload} className="mt-2 block text-sm" />
        {uploading && <p className="mt-2 text-sm text-zinc-600">Uploading…</p>}
        {err && <p className="mt-2 text-sm text-red-600">{err}</p>}
      </div>
      <div className="rounded border bg-white p-4">
        {loading ? (
          <p className="text-sm text-zinc-500">Loading datasets…</p>
        ) : items.length === 0 ? (
          <p className="text-sm text-zinc-500">No datasets yet. Upload a CSV/Parquet/JSON/Excel above to begin.</p>
        ) : (
        <table className="w-full text-sm">
          <thead className="text-left text-zinc-500"><tr><th>File</th><th>Format</th><th>Rows</th><th>Cols</th><th></th></tr></thead>
          <tbody>
            {items.map((d) => (
              <tr key={d.id} className="border-t">
                <td className="py-2">{d.filename}</td>
                <td>{d.format}</td>
                <td>{d.rows ?? "-"}</td>
                <td>{d.cols ?? "-"}</td>
                <td><a href={`/datasets/${d.id}`} className="underline">View</a> · <a href={`/analysis?dataset=${d.id}`} className="underline">Analyze</a></td>
              </tr>
            ))}
          </tbody>
        </table> )}
      </div>
    </div>
  );
}
