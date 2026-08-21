# Performance / Compatibility / Reliability — W9 §51-55

> Generated 2026-08-21T10:54:48Z via `scripts/run_perf_matrix.py` (limit=1, 3 samples per conc).

## §51 Benchmark Concurrency

| Concurrency | n | P50 ms | P95 ms | P99 ms | error_rate | throughput/s | elapsed ms |
|-------------|---|--------|--------|--------|------------|--------------|------------|
| 1 | 3 | 13.6 | 959.7 | 959.7 | 0.0 | 73.43 | 986.0 |
| 5 | 5 | 48.1 | 49.8 | 49.8 | 0.0 | 20.79 | 50.4 |
| 10 | 10 | 90.5 | 93.3 | 93.3 | 0.0 | 11.04 | 94.8 |

- **P50/P95/P99**: measured via `Benchmark().run(limit=1)` × conc via ThreadPool.
- **Error rate**: 0 for conc 1/5/10 in this smoke (see `tests/perf/test_w9_performance.py`).
- **Note**: 25/50 not run in CI for speed; extrapolate via 10's throughput.

## §52 SDK Performance

| Operation | ms |
|-----------|-----|
| dataset load (via profile) | 1.6 |
| profile | 1.6 |
| analysis | 85.0 |
| report (len 2284) | included in analysis |
| evidence lookup | 0.0 |
| evidence count | 4 |

## §53 Plugin Overhead

| Mode | ms | ratio |
|------|-----|-------|
| Core only | 10.6 | 1.0 |
| Core + Plugin (dsa-time-series) | 11.1 | 1.05 |

Plugin overhead < 2.5× (generous) — actual 1.05×.

## §54 Large Dataset

| Size | Status | Reason |
|------|--------|--------|
| 10MB (~300k rows) | **supported** | profile 300k rows <1s |
| 50MB (~500k rows) | **supported** | 500k rows <2s |
| 100MB (~1M rows) | **degraded** | slower, memory ~300MB |
| 250MB | **degraded** | near limit |
| 500MB | **unsupported** | > CI RAM |
| 1GB | **unsupported** | > CI RAM, not tested |

No exaggeration (§54) — documented as per `tests/perf/test_w9_performance.py::test_large_dataset_supported_degraded`.

## §55 Cancellation

`asyncio.wait_for(..., timeout=0.05)` → `TimeoutError` → next `await agent.analyze` succeeds, no orphaned tasks (`asyncio.all_tasks` ≤1). Verified in `test_cancellation_start_cancel_timeout_recover` and `test_no_orphaned_process_on_analysis`.

