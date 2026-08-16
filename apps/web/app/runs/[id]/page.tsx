export default async function RunDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Run {id}</h1>
      <p className="text-sm text-zinc-600">Replay / Fork: checkpoint #12 → Replay or Fork (Run #124 → Run #124-Fork-A). API: <code>GET /api/v1/analysis/{id}</code></p>
    </div>
  );
}
