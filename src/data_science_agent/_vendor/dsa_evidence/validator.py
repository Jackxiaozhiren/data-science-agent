from __future__ import annotations

import re
from typing import Any

from dsa_evidence.models import EvidenceGraph

_CAUSAL_PAT = re.compile(
    r"\b(cause[sd]?|caused by|impact|effect of|leads to|results in|due to)\b", re.IGNORECASE
)


def validate_evidence_graph(graph: EvidenceGraph) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    # 1. Every insight must have evidence
    for ins in graph.insights:
        if not ins.evidence_ids:
            results.append(
                {
                    "check": "insight_evidence",
                    "passed": False,
                    "message": f"Insight {ins.id} has no evidence",
                    "insight_id": ins.id,
                }
            )
        else:
            missing = [eid for eid in ins.evidence_ids if eid not in {n.id for n in graph.nodes}]
            if missing:
                results.append(
                    {
                        "check": "insight_evidence",
                        "passed": False,
                        "message": f"Insight {ins.id} references missing evidence {missing}",
                        "insight_id": ins.id,
                    }
                )
            else:
                results.append(
                    {"check": "insight_evidence", "passed": True, "message": f"Insight {ins.id} ok"}
                )

    # 2. Every evidence must trace to a tool call
    call_ids = {c.get("call_id") for c in graph.tool_calls}
    for ev in graph.nodes:
        if ev.source_id not in call_ids:
            results.append(
                {
                    "check": "evidence_traceability",
                    "passed": False,
                    "message": f"Evidence {ev.id} source_id {ev.source_id} not in tool_calls",
                }
            )
        else:
            results.append(
                {
                    "check": "evidence_traceability",
                    "passed": True,
                    "message": f"Evidence {ev.id} traceable",
                }
            )

    # 3. Unsupported causal claim guard
    for ins in graph.insights:
        if _CAUSAL_PAT.search(ins.finding):
            # check if any supporting evidence is causal — none in V0.1, so fail
            results.append(
                {
                    "check": "unsupported_claim",
                    "passed": False,
                    "message": f"Insight {ins.id} uses causal language without causal evidence",
                    "finding": ins.finding,
                }
            )
        else:
            results.append(
                {
                    "check": "unsupported_claim",
                    "passed": True,
                    "message": f"Insight {ins.id} no causal claim",
                }
            )

    # 4. Dataset hash present
    if graph.dataset_sha256:
        results.append({"check": "dataset_hash", "passed": True, "message": "Dataset hash present"})
    else:
        results.append(
            {"check": "dataset_hash", "passed": False, "message": "Dataset hash missing"}
        )

    return results
