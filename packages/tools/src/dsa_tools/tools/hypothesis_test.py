from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import numpy as np
import polars as pl
from pydantic import BaseModel, Field
from scipy import stats

from dsa_datasets.loader import load_dataframe
from dsa_datasets.validate import detect_format
from dsa_tools.base import BaseTool
from dsa_tools.errors import ToolExecutionError


class HypothesisTestInput(BaseModel):
    dataset_path: str
    test: Literal["t_test", "welch_t_test", "mann_whitney", "anova", "kruskal", "chi2", "fisher"] = "t_test"
    group_col: str | None = None
    value_col: str | None = None
    group_a: str | None = None
    group_b: str | None = None


class HypothesisTestOutput(BaseModel):
    test: str
    statistic: float
    p_value: float
    effect_size: float | None = None
    ci_low: float | None = None
    ci_high: float | None = None
    assumptions: list[str] = Field(default_factory=list)
    interpretation: str
    limitations: str = "Check assumptions; association does not imply causation."
    n_a: int | None = None
    n_b: int | None = None


def _cohen_d(a: np.ndarray, b: np.ndarray) -> float:
    mean_a, mean_b = float(np.mean(a)), float(np.mean(b))
    n_a, n_b = len(a), len(b)
    var_a, var_b = float(np.var(a, ddof=1)), float(np.var(b, ddof=1))
    pooled = ((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2) if (n_a + n_b - 2) > 0 else 0
    if pooled <= 0:
        return 0.0
    return (mean_a - mean_b) / float(np.sqrt(pooled))


class HypothesisTestTool(BaseTool[HypothesisTestInput, HypothesisTestOutput]):
    name = "hypothesis_test"
    description = "Run hypothesis tests: t_test/welch/mann_whitney/anova/kruskal/chi2"
    input_model = HypothesisTestInput
    output_model = HypothesisTestOutput

    async def execute(self, inp: HypothesisTestInput) -> HypothesisTestOutput:
        p = Path(inp.dataset_path)
        if not p.exists():
            raise ToolExecutionError(f"dataset_path not found: {inp.dataset_path}")
        fmt = detect_format(p.name)
        df = load_dataframe(p, fmt)

        test = inp.test

        if test in ("t_test", "welch_t_test", "mann_whitney"):
            if not inp.group_col or not inp.value_col:
                raise ToolExecutionError("group_col and value_col required for t_test/welch/mann_whitney")
            if inp.group_col not in df.columns or inp.value_col not in df.columns:
                raise ToolExecutionError(f"Columns not found: {df.columns}")
            groups = df[inp.group_col].unique().to_list()
            # filter nulls
            sub = df.select([inp.group_col, inp.value_col]).drop_nulls()
            if inp.group_a and inp.group_b:
                a_vals = sub.filter(pl.col(inp.group_col) == inp.group_a)[inp.value_col].to_numpy().astype(float)
                b_vals = sub.filter(pl.col(inp.group_col) == inp.group_b)[inp.value_col].to_numpy().astype(float)
            else:
                if len(groups) < 2:
                    raise ToolExecutionError("Need at least 2 groups")
                g0, g1 = groups[0], groups[1]
                a_vals = sub.filter(pl.col(inp.group_col) == g0)[inp.value_col].to_numpy().astype(float)
                b_vals = sub.filter(pl.col(inp.group_col) == g1)[inp.value_col].to_numpy().astype(float)
            if len(a_vals) < 2 or len(b_vals) < 2:
                raise ToolExecutionError("Each group needs >=2 observations")

            if test == "t_test":
                stat, pval = stats.ttest_ind(a_vals, b_vals, equal_var=True)
                eff = _cohen_d(a_vals, b_vals)
                assumptions = ["independence", "normality (approx)", "equal variances"]
            elif test == "welch_t_test":
                stat, pval = stats.ttest_ind(a_vals, b_vals, equal_var=False)
                eff = _cohen_d(a_vals, b_vals)
                assumptions = ["independence", "normality (approx)", "unequal variances allowed"]
            else:
                stat, pval = stats.mannwhitneyu(a_vals, b_vals, alternative="two-sided")
                eff = None
                assumptions = ["independence", "ordinal/continuous"]

            sig = "reject H0" if float(pval) < 0.05 else "fail to reject H0"
            interp = f"{test}: statistic={float(stat):.4f}, p={float(pval):.4g} -> {sig} at alpha=0.05."
            return HypothesisTestOutput(
                test=test,
                statistic=float(stat),
                p_value=float(pval),
                effect_size=eff,
                assumptions=assumptions,
                interpretation=interp,
                n_a=len(a_vals),
                n_b=len(b_vals),
            )

        if test in ("anova", "kruskal"):
            if not inp.group_col or not inp.value_col:
                raise ToolExecutionError("group_col and value_col required for anova/kruskal")
            sub = df.select([inp.group_col, inp.value_col]).drop_nulls()
            groups = [sub.filter(pl.col(inp.group_col) == g)[inp.value_col].to_numpy().astype(float) for g in sub[inp.group_col].unique().to_list()]
            if len(groups) < 2:
                raise ToolExecutionError("Need >=2 groups")
            if test == "anova":
                stat, pval = stats.f_oneway(*groups)
                assumptions = ["independence", "normality", "homogeneity of variances"]
            else:
                stat, pval = stats.kruskal(*groups)
                assumptions = ["independence", "ordinal"]
            sig = "reject H0" if float(pval) < 0.05 else "fail to reject H0"
            interp = f"{test}: statistic={float(stat):.4f}, p={float(pval):.4g} -> {sig}."
            return HypothesisTestOutput(test=test, statistic=float(stat), p_value=float(pval), assumptions=assumptions, interpretation=interp)

        if test == "chi2":
            if not inp.group_col or not inp.value_col:
                raise ToolExecutionError("group_col and value_col required for chi2")
            # build contingency table
            sub = df.select([inp.group_col, inp.value_col]).drop_nulls()
            # pivot counts
            ct = sub.group_by([inp.group_col, inp.value_col]).len()
            # Build matrix via polars pivot
            try:
                pivoted = ct.pivot(values="len", index=inp.group_col, on=inp.value_col)
                mat = pivoted.select(pl.exclude(inp.group_col)).to_numpy().astype(float)
                # fill nan as 0
                mat = np.nan_to_num(mat, nan=0.0)
            except Exception as e:
                raise ToolExecutionError(f"Failed to build contingency table: {e}") from e
            stat, pval, dof, expected = stats.chi2_contingency(mat)
            interp = f"chi2: statistic={float(stat):.4f}, p={float(pval):.4g} -> {'reject H0' if float(pval) < 0.05 else 'fail to reject H0'}."
            return HypothesisTestOutput(test=test, statistic=float(stat), p_value=float(pval), assumptions=["independence", "expected counts >=5"], interpretation=interp)

        raise ToolExecutionError(f"Unsupported test: {test}")
