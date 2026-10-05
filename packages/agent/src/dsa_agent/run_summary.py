"""The run-level contract shared by every interface (audit §111, Phase 4 target 3).

``dsa_agent.state.AnalysisState`` is the source. §108 measured that the SDK, the REST report and the MCP
``analyze`` result each re-listed its run-level fields by hand, and that the copies had already diverged:
MCP published no ``validation`` at all and emitted ``tool_calls`` without declaring it. Hand-listing is
the mechanism, a lost field is the symptom, so this module holds the list and the one normalization rule.

Names here are canonical (``validation_results``). A surface that publishes an alias applies it at its own
boundary, explicitly -- REST's ``markdown``, MCP's ``analysis_id`` -- so the alias is visible where it is
introduced instead of being three spellings of one idea.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

#: The run-level fields every interface publishes, under these names.
RUN_SUMMARY_FIELDS: tuple[str, ...] = (
    "run_id",
    "status",
    "report_markdown",
    "evidence",
    "insights",
    "artifacts",
    "tool_calls",
    "validation_results",
    "error",
)

#: Of those, the ones that arrive as model instances and leave as plain dicts.
COLLECTION_FIELDS = frozenset(
    {"evidence", "insights", "artifacts", "tool_calls", "validation_results"}
)


def normalize_records(items: Iterable[Any] | None) -> list[dict[str, Any]]:
    """Turn run records into plain dicts, accepting all three shapes the codebase produces.

    A state member may be a pydantic model, a dataclass instance, or already a dict depending on whether
    the run was just executed or rehydrated from a checkpoint; each of the four hand-rolled copies of
    this rule handled the same cases slightly differently.
    """
    out: list[dict[str, Any]] = []
    for item in items or []:
        if hasattr(item, "model_dump"):
            out.append(item.model_dump(mode="json"))
        elif isinstance(item, dict):
            out.append(dict(item))
        elif hasattr(item, "__dict__"):
            out.append(dict(item.__dict__))
        else:
            out.append(dict(item))
    return out


def run_summary(state: Any) -> dict[str, Any]:
    """The canonical run-level payload for one analysis, from a model or its serialized dict."""
    source: dict[str, Any] = state if isinstance(state, dict) else state.model_dump(mode="json")
    return {
        key: normalize_records(source.get(key)) if key in COLLECTION_FIELDS else source.get(key)
        for key in RUN_SUMMARY_FIELDS
    }
