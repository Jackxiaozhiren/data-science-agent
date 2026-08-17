from __future__ import annotations

import statistics
from typing import Any


def p50(vals: list[float]) -> float:
    return float(statistics.median(vals)) if vals else 0.0


def p95(vals: list[float]) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    idx = int(0.95 * len(s))
    return float(s[min(idx, len(s) - 1)])


def p99(vals: list[float]) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    idx = int(0.99 * len(s))
    return float(s[min(idx, len(s) - 1)])


def concurrency_matrix(levels: list[int] | None = None) -> dict[str, Any]:
    levels = levels or [1, 5, 10, 25, 50]
    # Stub: run dsa benchmark at each level and record latency
    # For now return structure without actual runs (caller fills)
    return {str(n): {"concurrency": n, "p50_ms": 0, "p95_ms": 0, "throughput": 0} for n in levels}


def measure_latencies(runs: list[float]) -> dict[str, float]:
    return {"p50": p50(runs), "p95": p95(runs), "p99": p99(runs), "mean": float(statistics.mean(runs)) if runs else 0.0}
