async function fetchOne(id: string) {
  const res = await fetch(`http://localhost:8000/api/v1/datasets/${id}`, { cache: "no-store" });
  if (!res.ok) return null;
  return (await res.json()) as { id: string; filename: string; format: string; rows: number; cols: number; profile: { rows: number; columns: number; column_profiles: { name: string; dtype: string; kind: string; null_count: number; unique_count: number | null; mean?: number }[]; duplicate_rows: number; missing_ratio: number } | null };
}

export default async function DatasetDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const ds = await fetchOne(id);
  if (!ds) return <p className="text-sm text-red-600">Dataset not found.</p>;
  const prof = ds.profile;
  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold">{ds.filename}</h1>
      <p className="text-sm text-zinc-600">Format {ds.format} · {ds.rows} rows × {ds.cols} cols</p>
      {!prof ? <p className="text-sm">No profile.</p> : (
        <>
          <div className="rounded border bg-white p-4 text-sm">Duplicates: {prof.duplicate_rows} · Missing ratio: {(prof.missing_ratio * 100).toFixed(1)}%</div>
          <div className="rounded border bg-white p-4">
            <h2 className="font-medium">Schema</h2>
            <table className="mt-2 w-full text-sm">
              <thead className="text-left text-zinc-500"><tr><th>Column</th><th>Dtype</th><th>Kind</th><th>Nulls</th><th>Uniques</th></tr></thead>
              <tbody>
                {prof.column_profiles.map((c) => (
                  <tr key={c.name} className="border-t"><td>{c.name}</td><td>{c.dtype}</td><td>{c.kind}</td><td>{c.null_count}</td><td>{c.unique_count ?? "-"}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      <a href={`/analysis?dataset=${ds.id}`} className="inline-block rounded bg-zinc-900 px-3 py-2 text-sm text-white">Analyze this dataset</a>
    </div>
  );
}
