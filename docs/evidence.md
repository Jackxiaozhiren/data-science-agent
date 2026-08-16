# Evidence

## Model
`packages/evidence/src/dsa_evidence/models.py`: `EvidenceGraph` — `Insight → Evidence → ToolCall → Dataset` with `dataset_sha256` and edge kinds `supports / derives_from`.

## Validation
`packages/evidence/src/dsa_evidence/validator.py` — 4 checks:
- `insight_evidence` (every insight has ≥1 evidence),
- `evidence_traceability` (evidence → tool_call → dataset),
- `unsupported_claim` (causal guard),
- `dataset_hash` (artifact can rehash to source).

## Reproducibility Bundle
`packages/evidence/src/dsa_evidence/repro.py` — per-run artifacts under `artifacts/reports/<run_id>/`:
- `report.md`, `experiment.json`, `reproduce.sh`, `analysis.ipynb`, `evidence_graph.json`.

Validator is called post-`write_report_artifacts` inside `dsa_agent.graph.run_analysis` when the graph is executed.
