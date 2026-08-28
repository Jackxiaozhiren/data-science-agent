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
| `.workspace/` | git-ignored pinned tarball extraction + gated GT (never committed) |

## Usage

**Step 1 — operator setup** (network + license acceptance stay operator-side;
the adapter itself contains no network or credential code):

```bash
export DSC_WORKSPACE="$PWD/benchmarks/external/datascibench/.workspace"
mkdir -p "$DSC_WORKSPACE"
curl -L "https://codeload.github.com/THUDM/DataSciBench/tar.gz/84ef3d4d94d7362a5149cf14a73dc168fc4f2f33" \
  | tar xz --strip-components=1 -C "$DSC_WORKSPACE"
printf '%s\n' "84ef3d4d94d7362a5149cf14a73dc168fc4f2f33" > "$DSC_WORKSPACE/.upstream_commit"

# optional — gated distribution (never commit it):
#   accept conditions at https://huggingface.co/datasets/zd21/DataSciBench
#   then place, per the download's layout:
#     - input datasets referenced by the prompts (e.g. campaign_data.csv)
#     - ground truth into "$DSC_WORKSPACE/gt/"
# NOTE: input datasets are NOT in the public GitHub repo — only prompt.json
# per task. Without the gated download, runs complete mechanically but analyze
# no data (honest failed outcome, adapter reports this rather than scoring).
```

**Step 2 — run through the Phase B protocol** (`adapter.py` docstrings carry
the per-method contract; `tests/evals/test_datascibench_adapter.py` shows the
end-to-end flow):

```python
from pathlib import Path
import importlib.util
spec = importlib.util.spec_from_file_location(
    "datascibench_adapter",
    Path("benchmarks/external/datascibench/adapter.py"),
)
```

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
