export default async function ReplayPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Replay — {id}</h1>
      <p className="text-sm text-zinc-600">Select checkpoint, Replay or Fork. Persists via LangGraph MemorySaver (pause/resume/replay/fork/inspect).</p>
    </div>
  );
}
