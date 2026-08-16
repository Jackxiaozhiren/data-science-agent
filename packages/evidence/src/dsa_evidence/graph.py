from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from dsa_datasets.hash_utils import sha256_file
from dsa_evidence.models import EvidenceEdge, EvidenceGraph, EvidenceNode, InsightNode


def build_evidence_graph(
    run_id: str,
    dataset_id: str,
    dataset_path: str | None,
    evidence: list[Any],
    insights: list[Any],
    tool_calls: list[Any],
) -> EvidenceGraph:
    sha = None
    if dataset_path:
        p = Path(dataset_path)
        if p.exists():
            try:
                sha = sha256_file(p)
            except Exception:
                sha = None

    nodes = []
    for ev in evidence:
        # ev may be dsa_agent.state.Evidence or dsa_evidence model
        nodes.append(
            EvidenceNode(
                id=getattr(ev, "id", str(uuid.uuid4())),
                claim=getattr(ev, "claim", str(ev)),
                source_type=getattr(ev, "source_type", "python"),
                source_id=getattr(ev, "source_id", ""),
                result=getattr(ev, "result", {}) if hasattr(ev, "result") else (ev.get("result", {}) if isinstance(ev, dict) else {}),
                confidence=float(getattr(ev, "confidence", 0.0)),
                validation_status=getattr(ev, "validation_status", "pending"),
            )
        )

    ins_nodes = []
    for ins in insights:
        ins_nodes.append(
            InsightNode(
                id=getattr(ins, "id", str(uuid.uuid4())),
                finding=getattr(ins, "finding", str(ins)),
                evidence_ids=list(getattr(ins, "evidence_ids", [])),
                magnitude=getattr(ins, "magnitude", None),
                significance=getattr(ins, "significance", None),
                limitation=getattr(ins, "limitation", None),
            )
        )

    # edges: Insight -> Evidence, Evidence -> ToolCall
    edges: list[EvidenceEdge] = []
    for ins in ins_nodes:
        for eid in ins.evidence_ids:
            edges.append(EvidenceEdge(from_id=ins.id, to_id=eid, kind="supports"))
    for ev in nodes:
        edges.append(EvidenceEdge(from_id=ev.id, to_id=ev.source_id, kind="derives_from"))

    # normalize tool_calls to dict list
    tc_list: list[dict[str, Any]] = []
    for tc in tool_calls:
        if hasattr(tc, "model_dump"):
            tc_list.append(tc.model_dump(mode="json"))
        elif isinstance(tc, dict):
            tc_list.append(tc)
        else:
            tc_list.append({"call_id": str(getattr(tc, "call_id", "")), "tool": str(getattr(tc, "tool", ""))})

    return EvidenceGraph(
        run_id=run_id,
        dataset_id=dataset_id,
        dataset_path=dataset_path,
        dataset_sha256=sha,
        nodes=nodes,
        insights=ins_nodes,
        edges=edges,
        tool_calls=tc_list,
    )
