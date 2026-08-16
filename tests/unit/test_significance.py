from __future__ import annotations


def test_significance_helpers() -> None:
    from dsa_evaluation.significance import bootstrap_ci, mcnemar, paired_bootstrap_diff

    m, lo, hi = bootstrap_ci([1.0, 0.0, 1.0, 1.0], n_boot=200, seed=42)
    assert 0 <= lo <= m <= hi <= 1
    md, lo2, hi2 = paired_bootstrap_diff([1, 0, 1], [1, 1, 0], n_boot=200)
    assert isinstance(md, float)
    r = mcnemar(5, 2)
    assert "p_value" in r
    assert 0 <= r["p_value"] <= 1
