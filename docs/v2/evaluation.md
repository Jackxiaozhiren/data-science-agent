# Evaluation Framework — W2

- Spec: V2 §9–13 · Code: `packages/evaluation/src/dsa_evaluation/{metrics.py,evaluation_framework.py}`

Replaces single `50/50` with 10-dim `EvaluationResultV2`:

- `task_success`, `statistical_correctness`, `tool_correctness`, `evidence_coverage`, `unsupported_claim_rate`, `code_execution_rate`, `sql_correctness`, `reproducibility_score`, `safety_score` + `latency_ms` / `planning_latency_ms` / `tool_latency_ms` / `input_tokens/output_tokens/total_tokens` + `level_scores{tool_execution,numerical,sql,evidence}` · Adapted from `evaluate_task` → `from_metrics`.
- `aggregate_v2` adds `by_category` + `by_difficulty{easy,medium,hard,expert}` breakdowns.

Evidence coverage: `supported_claims/total_claims`; Unsupported claim rate: `unsupported/total_claims` (guarded by causal regex). Statistical correctness checks `correct_method/assumptions/statistic/p/effect_size/interpretation` where `expected_value+tolerance` present (future: exact `gold_method` per task from `benchmarks/v2` catalog).

Tests: `tests/evals/test_evaluation_framework.py` (2 passed, live).
