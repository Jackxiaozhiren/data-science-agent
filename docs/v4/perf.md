# Performance — V4 W9 (§53–57)

Targets (§54): `P50/P95/P99` for `API latency / Tool latency / Agent latency / Report latency / Dataset loading`.

Concurrency (§55): test `1/5/10/25/50 runs` — record `throughput / failure / memory / latency`.

Harness: `packages/evaluation/src/dsa_evaluation/perf_harness.py` — `p50/p95/p99/measure_latencies/concurrency_matrix`.

Resource mgmt (§57): `Job Queue / Execution Limits / Cancellation / Backpressure` — local-first, no K8s yet.
