# Benchmark Showcase — V3 §71 (10 Canonical Tasks for README/Documentation)

> Selected from `benchmarks/v2/catalog.json 0.3.0` (30/100/11, seed 42) — shows `Task / System / Score / Evidence / Failure|Success`.

| # | Task (id / category) | System | Score (live 100/100 @1.00) | Evidence | Failure/Success |
|---|----------------------|--------|----------------------------|----------|-----------------|
| 1 | `eda-08` EDA — `Describe distribution x,y,z` | `profile_dataset + correlation` | `task_success 1.00, evidence_coverage 1.00` | `E-profile + E-corr r` | Success |
| 2 | `sql-05` SQL — `Top categories by revenue` | `run_sql SELECT ... GROUP BY ORDER BY LIMIT` | `sql_accuracy 1.00` | `E-sql 3 rows` | Success |
| 3 | `stats-10` Statistics — `hypothesis test price vs units` | `hypothesis_test (t-test)` | `statistical 1.00 (evaluator_v2)` | `E-hyp p=0.205` | Success |
| 4 | `reg-08` Regression — `regression y~x` | `regression` | `statistical 1.00` | `E-reg r2 0.42` | Success |
| 5 | `clf-04` Classification — `hr_promotion` | `train_model` | `task_success 1.00` | `E-clf accuracy` | Success |
| 6 | `ts-06` Time Series — `forecast 30d` | `forecast` | `task_success 1.00, uncertainty CI` | `E-fc 30-day interval` | Success |
| 7 | `viz-03` Visualization — `histogram sales` | `create_chart` | `task_success 1.00` | `E-viz PNG artifact` | Success |
| 8 | `dq-06` Data Quality — `missing_heavy` | `profile + validate` | `task_success 1.00` | `E-dq missing report` | Success (recoverable) |
| 9 | `clus-04` Clustering — `wide_table PCA+cluster` | `run_python PCA + train kmeans` | `task_success 1.00` | `E-clus sil 0.42` | Success |
| 10 | `ev-01` Evidence Validation — `validate insight` | `get_evidence + validator` | `evidence_coverage 1.00, unsupported 0.00` | `E→TC→Dataset trace` | Success (S09 guard exercised) |

- Live aggregate: `uv run dsa --catalog benchmarks/v2/catalog.json --datasets benchmarks/v2/datasets --limit 100` → `100/100 @1.00, 11 cats @1.00`.
- Full 100: `benchmarks/v2/catalog.json` + `benchmarks/v2/README.md` (§50) + `docs/v3/BENCHMARK_AUDIT.md` (§12 Q1–Q10).
- Failure patterns: see `research/failure-case-study.md` (§67).
