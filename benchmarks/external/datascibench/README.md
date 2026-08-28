# DataSciBench Adapter (V4.3 Phase C, W3)

Bridge between Data Science Agent and the **original** DataSciBench benchmark
([arXiv:2502.13897](https://arxiv.org/abs/2502.13897), [THUDM/DataSciBench](https://github.com/THUDM/DataSciBench)),
pinned at upstream commit `84ef3d4d94d7362a5149cf14a73dc168fc4f2f33` (2026-01-21).

## Files

| File | Purpose |
|------|---------|
| `adapter.py` | implements the Phase B `ExternalBenchmarkAdapter` protocol (§17) |
| `manifest.json` | §18 provenance manifest (pinned commit, task counts, integrity notes) |
| `LICENSE_NOTES.md` | license findings and redistribution constraints (§23) |
| `results/` | raw evaluator output lands here (§48: raw → analysis → artifact) |
| `logs/` | adapter run logs |
| `.workspace/` | git-ignored clone of upstream + gated GT (never committed) |

## Usage

```bash
export DSC_WORKSPACE=/path/for/upstream-clone   # optional override
# optional, for gated ground truth (never commit it):
export HF_TOKEN=...                             # from your HF account after accepting dataset conditions

uv run python - <<'PY'
from benchmarks_external.datascibench_adapter import load_adapter
PY
```

The adapter is loaded via `tests/evals/test_datascibench_adapter.py` and the
Phase B protocol — see `adapter.py` docstrings for the per-method contract.

## Task categories (222 total at pinned commit)

| Prefix | Count | Adapter v1 |
|--------|-------|------------|
| `human_*` | 25 | supported end-to-end |
| `csv_excel_*` | 20 | supported end-to-end |
| `dl_*` | 10 | **unsupported** — no GPU training surface (reported with reason, §26) |
| `bcb*` | 167 | **pending** — `evaluate_tmc.py` TMC path not yet implemented (reported with reason) |

## Integrity (V4.3 §16/§19/§21/§23)

- Original evaluator only — the adapter converts DSA output into the
  `data/{task_id}/{model}_{run_id}/logs.txt` plan-marker layout consumed by
  upstream `experiments/evaluate.py`; the evaluator is never modified.
- Gold isolation — GT never enters `AgentTaskView`; `assert_gold_isolation`
  runs before every agent dispatch.
- No redistribution — upstream has no LICENSE; nothing from the benchmark is
  committed into this repository. See `LICENSE_NOTES.md`.
