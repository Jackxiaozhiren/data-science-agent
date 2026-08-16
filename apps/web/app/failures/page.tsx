export default function FailuresPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Failure Analysis</h1>
      <p className="text-sm text-zinc-600">Taxonomy F01–F15 · Failure log · Recovery rate · Agent/tool with most errors · Average retries · Unsupported claim rate.</p>
      <div className="rounded border bg-white p-4 text-sm">See <code>packages/evidence/src/dsa_evidence/failure_taxonomy.py</code></div>
    </div>
  );
}
