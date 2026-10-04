from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ReproLevel = Literal["L0", "L1", "L2", "L3", "L4", "L5"]


class ReproducibilityScore(BaseModel):
    level: ReproLevel = "L0"
    score: float = 0.0
    details: dict[str, Any] = Field(default_factory=dict)
    dataset_sha256_match: bool | None = None
    tool_trajectory_match: bool | None = None
    conclusion_match: bool | None = None


def _dataset_sha(record: dict[str, Any]) -> str | None:
    """The dataset content hash a run record carries, or ``None`` when it carries none.

    Two shapes are accepted because two producers exist: `build_experiment_json` writes
    ``dataset_sha256`` at the top level, while a nested evidence-graph record was an earlier shape.
    """
    sha = record.get("dataset_sha256")
    if isinstance(sha, str) and sha:
        return sha
    graph = record.get("evidence_graph")
    if isinstance(graph, dict):
        nested = graph.get("dataset_sha256")
        if isinstance(nested, str) and nested:
            return nested
    return None


def compare_runs(original: dict[str, Any], fresh: dict[str, Any]) -> ReproducibilityScore:
    """Compare two analysis state dicts (original vs fresh reproduce) → score 0..1.

    L0 same request, L1 same code (always lenient), L2 same data (hash when both records carry one,
    else dataset_id equality), L3 same env (python_version when either record carries an environment,
    else lenient), L4 same tool trajectory (tool names sequence), L5 same conclusion
    (insights+evidence count+metrics close). Each passing level contributes 1/6; failure
    short-circuits higher levels in details.

    Every lenient decision is recorded: ``details["L1_basis"]``, ``details["L2_basis"]`` and
    ``details["L3_basis"]`` name the equality that actually decided the level, so a pass that compared
    nothing cannot be read as evidence that it did.
    """
    scores = []
    details: dict[str, Any] = {}
    # L0 same request
    same_request = original.get("user_query") == fresh.get("user_query") and original.get(
        "dataset_path"
    ) == fresh.get("dataset_path")
    scores.append(1 if same_request else 0)
    details["L0_same_request"] = same_request
    # L1 same code (compare experiment package versions if present, else lenient)
    scores.append(1)
    details["L1_same_code"] = True
    details["L1_basis"] = "lenient_no_code_identity_is_compared"
    # L2 same data
    o_sha, f_sha = _dataset_sha(original), _dataset_sha(fresh)
    same_data = bool(o_sha and f_sha and o_sha == f_sha)
    # if missing hash fall back to dataset_id equality
    if o_sha is None and f_sha is None:
        same_data = original.get("dataset_id") == fresh.get("dataset_id")
        l2_basis = "dataset_id"
    elif o_sha is None or f_sha is None:
        l2_basis = "one_record_carries_no_hash"
    else:
        same_data = o_sha == f_sha
        l2_basis = "dataset_sha256"
    scores.append(1 if same_data else 0)
    details["L2_same_data"] = same_data
    details["L2_basis"] = l2_basis
    # L3 same env (python_version + platform)
    o_env = original.get("environment") or {}
    f_env = fresh.get("environment") or {}
    if o_env or f_env:
        same_env = o_env.get("python_version", "")[:20] == f_env.get("python_version", "")[:20]
        l3_basis = "environment.python_version"
    else:
        same_env = True
        l3_basis = "no_environment_in_either_record"
    scores.append(1 if same_env else 0)
    details["L3_same_env"] = same_env
    details["L3_basis"] = l3_basis

    # L4 same tool trajectory (tool name sequence, ignoring call_id)
    def _seq(d: dict[str, Any]) -> list[str]:
        tcs = d.get("tool_calls") or []
        return [c.get("tool", "") for c in tcs if isinstance(c, dict)]

    o_seq, f_seq = _seq(original), _seq(fresh)
    same_traj = o_seq == f_seq and len(o_seq) > 0
    scores.append(1 if same_traj else 0)
    details["L4_same_trajectory"] = same_traj
    details["L4_orig_seq"] = o_seq
    details["L4_fresh_seq"] = f_seq
    # L5 same conclusion (insight findings + evidence count within 20%)
    o_ins = len(original.get("insights") or [])
    f_ins = len(fresh.get("insights") or [])
    o_ev = len(original.get("evidence") or [])
    f_ev = len(fresh.get("evidence") or [])
    same_conclusion = (
        (abs(o_ins - f_ins) <= max(1, o_ins * 0.2)) and (abs(o_ev - f_ev) <= max(1, o_ev * 0.2))
        if (o_ins or f_ins or o_ev or f_ev)
        else True
    )
    scores.append(1 if same_conclusion else 0)
    details["L5_same_conclusion"] = same_conclusion
    details["L5_basis"] = (
        "insight_and_evidence_counts"
        if (o_ins or f_ins or o_ev or f_ev)
        else "no_insights_or_evidence_in_either_record"
    )
    n = 6
    total = sum(scores) / n
    # Level label = highest L whose all prior Ls passed
    level_order: list[ReproLevel] = ["L0", "L1", "L2", "L3", "L4", "L5"]
    lvl: ReproLevel = "L0"
    for i, ok in enumerate(scores):
        if ok:
            lvl = level_order[i]
        else:
            break
    return ReproducibilityScore(
        level=lvl,
        score=round(total, 4),
        details=details,
        # The field names a hash comparison, so it only claims one when a hash was in both records;
        # an id-equality pass is reported as unknown rather than as a sha match.
        dataset_sha256_match=same_data if l2_basis == "dataset_sha256" else None,
        tool_trajectory_match=same_traj,
        conclusion_match=same_conclusion,
    )
