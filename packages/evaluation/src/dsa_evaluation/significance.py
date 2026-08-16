from __future__ import annotations

import math
import random
from typing import Any


def bootstrap_ci(
    values: list[float], n_boot: int = 2000, alpha: float = 0.05, seed: int = 42
) -> tuple[float, float, float]:
    """Bootstrap CI for mean; returns (mean, lower, upper). Deterministic with seed 42 per V2 §98."""
    if not values:
        return (0.0, 0.0, 0.0)
    r = random.Random(seed)
    n = len(values)
    mean = sum(values) / n
    boots = []
    for _ in range(n_boot):
        sample = [values[r.randrange(n)] for _ in range(n)]
        boots.append(sum(sample) / n)
    boots.sort()
    lo = boots[int((alpha / 2) * n_boot)]
    hi = boots[int((1 - alpha / 2) * n_boot) - 1]
    return (mean, lo, hi)


def paired_bootstrap_diff(
    a: list[float], b: list[float], n_boot: int = 2000, seed: int = 42
) -> tuple[float, float, float]:
    """Paired bootstrap for difference of means; handles non-iid via pairing."""
    if len(a) != len(b) or not a:
        return (0.0, 0.0, 0.0)
    diffs = [ai - bi for ai, bi in zip(a, b)]
    return bootstrap_ci(diffs, n_boot=n_boot, seed=seed)


def mcnemar(b01: int, b10: int) -> dict[str, Any]:
    """McNemar for paired binary outcomes; b01 = A fail B pass, b10 = A pass B fail."""
    n = b01 + b10
    if n == 0:
        return {"statistic": 0.0, "p_value": 1.0, "note": "no discordant pairs"}
    stat = (abs(b01 - b10) - 1) ** 2 / n  # continuity correction
    # chi2(1) tail approx
    # use math.erfc for p-value
    p = math.erfc(math.sqrt(stat / 2))
    return {"statistic": stat, "p_value": p, "b01": b01, "b10": b10}
