export default function EvaluationsPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Evaluations</h1>
      <p className="text-sm text-zinc-600">V2 evaluation framework (EvaluationResultV2: 10 dims + 6-level breakdown). See <code>docs/evaluation.md</code>.</p>
      <div className="rounded border bg-white p-4 text-sm">Levels: Tool Execution → Numerical → Statistical Method → Interpretation → Evidence → Final Report</div>
    </div>
  );
}
