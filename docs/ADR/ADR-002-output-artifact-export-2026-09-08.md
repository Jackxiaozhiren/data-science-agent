# ADR-002 — Agent Output-Artifact Export (file-producing tasks)

- Status: Proposed · Date: 2026-09-08 · Applies to: `packages/tools`, planner, `benchmarks/external/datascibench/adapter.py`
- Related: DataSciBench GT lane (`research/external/DATASCIBENCH_REPORT.md` §9.5), Benchmark V3 proposal C4, V4.3 §51 (no benchmark-specific core hacks)

## Problem

After adapter v2 (file mapping, 5/44 passed, mean CR 0.088), the dominant
remaining failure class is **wrong-content measured 0s**: the agent analyzes
data in memory but never writes the output files metric code reads
(`predictions.csv` with a `Predictions` column, `evaluation_metrics.csv` with
`Accuracy`, normalized/cleaned CSVs with exact schemas). The adapter can only
relocate genuine artifacts — it cannot invent schema-conformant content, and
must not (§16, §51). The capability gap is on the agent side: tool results
stay in memory; only charts persist as files today.

## Evidence

- `benchmarks/external/datascibench/results/raw_runs.json` (v2 run, 2026-09-05):
  39/44 failed on content; per-task CSVs in `.workspace/evaluation_results/`
  show `Error`→measured transitions but near-zero content matches.
- Example (`csv_excel_8` metric code): `pd.read_csv("predictions.csv")['Predictions']`
  → `accuracy_score(ground_truth, predictions)`. Our run produced tabular SQL
  output in memory; nothing named `predictions.csv` with that column existed.
- Example (`human_20`, passed 0.6): structural boolean checks passed once files
  existed — proving the pipeline from file-existence to measured score works.
- Internal benchmarks (150/150) need no files (exact-match tasks); case studies
  are `COMPLETED` without file outputs. So this gap is invisible internally —
  a genuine generalization finding, not a regression.

## Impact

- **New general capability** (not benchmark-specific): an `export_artifact`
  tool that persists an in-memory tool result to a named file (CSV/XLSX/PNG)
  inside the run workspace, with content hash recorded in evidence. Useful for
  real users (downloadable results), case studies, and any file-scored
  evaluation — this generality is what makes it §51-compliant.
- Components touched: `packages/tools` (new tool, additive), planner prompt
  (guidance to export key results, additive), adapter v2 preference order
  (run-workspace files first, largest-tabular fallback stays).
- No public API removal; no benchmark, evaluator, or metric change.

## Alternatives

1. **Adapter-side synthesis** (generate schema-conformant files from GT shapes
   or guesses) → REJECTED: fabrication boundary (§16, §130). The adapter must
   never author content.
2. **`export_artifact` tool (chosen):** general, testable, benefits non-benchmark
   users; adapter mapping stays a pure relocation layer.
3. **Prompt-only fix** (tell the planner to use `run_python` for file outputs) →
   fragile and model-dependent; no contract, no evidence hash. Rejected as the
   primary fix (may complement later).
4. **Do nothing** (accept 5/44) → valid fallback; keeps the honest baseline but
   leaves the largest measured failure class unaddressed.

## Recommendation

- Add `export_artifact` tool: inputs = source (tool `call_id` or inline table),
  filename (constrained to run workspace, no `..`/absolute), format (csv/xlsx/png);
  output = path + sha256, recorded as evidence. Writes bytes identical to the
  source result (relocation, not synthesis).
- Planner: export terminal results (predictions, metrics tables, cleaned frames)
  under task-natural names derived from the *user question*, never from
  metric definitions (gold isolation holds: the agent never sees metric.yaml).
- Adapter: prefer run-workspace files by name match first; keep largest-tabular
  fallback. `dsa_file_map.json` records provenance per file.
- Tests required before merge: unit round-trip (csv/xlsx/png + hash); integration
  (≥2 GT tasks move Error→measured, none regress to Error); regression
  (internal 150/150 unchanged, 8/8 case studies still COMPLETED, full suite green).

## Migration Plan

- Additive only: new tool registration, planner prompt appendix, adapter
  preference reorder. No migration needed for existing users; `export_artifact`
  appears in tool lists (SDK/MCP surfaces gain one entry — minor version bump).
- Docs: tool reference + evidence-graph story updated in the same PR.

## Rollback Plan

- Unregister the tool and revert the adapter preference line (largest-tabular
  fallback remains); delete run-workspace export dirs. All changes are additive,
  so rollback restores v2 behavior exactly. If GT scores regress vs the v2
  baseline (5/44, mean 0.088), the PR does not merge.

## Appendix (2026-09-08): internal v2 scare — root-caused to a CLI default bug, FIXED

- `dsa --catalog benchmarks/v2/catalog.json --limit 100` (no `--datasets`)
  measured **0.57**. A/B attribution via stash: identical 0.57 with this
  track's changes stashed → not export-track fallout.
- Root cause (deeper, same day): the `--datasets` default stayed at the v1
  dir even when `--catalog` pointed at v2 (present since 2026-08-17), so all
  v2-only datasets failed with "Dataset not found". With explicit
  `--datasets benchmarks/v2/datasets`: **100/100 @1.00** on the merged tree
  (all 11 categories green), export track active.
- Fix (this track, general not benchmark-specific): `_resolve_datasets_dir`
  derives the sibling `datasets/` dir when the catalog is overridden
  (`packages/evaluation/src/dsa_evaluation/cli.py` + regression test in
  `tests/unit/test_benchmark.py`). Verified: catalog-only v2 invocation now
  measures **100/100**. Lesson recorded: the `dsa` console resolves
  `dsa_evaluation` to the **vendored** copy — source edits take effect only
  after `sync_vendor.py` (this trap cost one full 100-task run).
- Release-truth consequence: no stale-claim issue — manifests' "100/100 (v2)"
  re-verified live on the merged tree. The GT generalization-gap math stands.
