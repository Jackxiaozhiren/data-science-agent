# CS08 ML Classification — Machine Learning

> **Flagship workflow:** train and evaluate a classification model while keeping model evidence, feature-importance output, provenance, and non-model tool failures in one auditable trace.

| Verified status | Runtime | Evidence | Tool calls | Artifacts |
|---|---:|---:|---:|---:|
| `COMPLETED` | 0.113s | 5 | 7 | 5 |

**Question →** Can DSA train a useful classifier on an imbalanced dataset, evaluate it, and explain the model with traceable evidence?  
**Why this case matters →** It demonstrates that model output is not treated as a free-floating answer: training/evaluation artifacts and feature importance live inside the same evidence and reproduction model as the rest of the analysis.

## Problem (§31)

Classification: predict an imbalanced label, evaluate holdout/CV performance, and report feature importance.

## Dataset (§29)

| Field | Value |
|-------|-------|
| **File** | `benchmarks/v2/datasets/imbalanced.csv` (verified run) |
| **Source** | Synthetic via `scripts/generate_benchmark_v2.py` seed 42 (public, CC0/MIT) |
| **License** | MIT / CC0 (synthetic, no copyright) |
| **Citation** | `benchmarks/v2/catalog.json` `0.3.0` + `DATA_SCIENCE_AGENT_V4_2.md` |
| **Download** | `benchmarks/v2/datasets/imbalanced.csv` (included in the repository) |
| **Version / Hash** | `v2 0.3.0` / `sha256:e47fd0fd12cdc56523da6377d4b311a6c40c3b022d587f58299cf319578fe1ef` |

## Question (§31)

> **"Train classification for imbalanced.csv, evaluate holdout, and report feature importance."**

## Analysis Plan (§31)

1. Profile the dataset and target balance.
2. Train a baseline classification model with cross-validation.
3. Evaluate predictive performance.
4. Produce feature-importance output and visualization.
5. Capture evidence and generate the reproducible report bundle.

## Agent Trajectory (§31)

**Run:** `run-e569d4141d` — **COMPLETED** in 0.113s with **5 evidence items, 7 tool calls, and 5 artifacts** (2026-08-25 live).

The classification path itself completed. Two automatically attempted `causal_check` calls failed with duplicate-projection errors and remain in the recorded trajectory as explicit limitations rather than being removed from the demo.

**Full trajectory:** `outputs/tool_calls.json`  
**Verified run summary:** `outputs/summary.json`  
**Evidence:** `outputs/evidence.json`

## Tools (§31)

`profile_dataset`, `train_model`, `evaluate_model`, `feature_importance`, `create_visualization`, plus evidence/report tooling selected by the agent.

## Statistics / Model (§31)

- **Model:** baseline classification workflow with logistic / tree-based model support depending on the tool path.
- **Evaluation:** cross-validation and/or holdout metrics recorded by the model tools.
- **Explainability:** feature-importance output is persisted with the analytical artifacts rather than summarized without provenance.

## Evidence (§31)

The verified run generated **5 real evidence items**, stored in `outputs/evidence.json` and linked to the corresponding tool calls and dataset provenance.

Evidence follows the project contract:

`Insight → Evidence → ToolCall → Dataset`

## Visualization (§31)

The verified workflow produced visualization artifacts associated with the model/evaluation path. They remain part of the generated analytical bundle.

## Report (§31)

The live execution produced `outputs/report.md` and the associated reproduction artifacts. The case-study audit records a 3,470-character report with a valid reproduction package.

## Limitations (§31)

- The dataset is synthetic and intentionally imbalanced; production calibration and domain shift are outside this case.
- The case demonstrates a baseline model path rather than exhaustive hyperparameter optimization.
- A single verified run is not external validation.
- **Observed tool failures remain visible:** two `causal_check` calls hit duplicate-projection errors. Classification training/evaluation and feature-importance generation still succeeded; see `outputs/tool_calls.json`.

## Reproduction (§31)

```bash
uv run python -c "
from data_science_agent import Agent
r = Agent().analyze_sync(
    'benchmarks/v2/datasets/imbalanced.csv',
    'Train classification for imbalanced.csv, evaluate holdout, and report feature importance.'
)
print(r.status, len(r.evidence))
"
```

Expected reference run: `run-e569d4141d`, `COMPLETED`, 5 evidence items. Compare a new run against `outputs/summary.json`, `outputs/evidence.json`, and the generated report bundle.

**Quality Gate (§33):** ✅ **Verified** — model workflow completed, evidence/reproduction artifacts were generated, and non-model tool failures remain visible. No mock / no hard-coded success result.

*Verified: 2026-08-25 — Phase D execution*
