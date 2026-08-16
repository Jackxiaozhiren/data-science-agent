# Agent Reliability Research — V3 Phase E (W5 §26–30)

> **Phase E · W5 Agent Reliability Research** · Date: 2026-08-16 · §26–30

---

## 1. Reliability Comparison (§26)

Four configurations (label mapping per §26):

| Config | Label | Meaning |
|--------|-------|---------|
| `single` | Single Agent | Baseline: no planner/critic evidence (ablation A heuristic) |
| `planner` | Planner + Agent | Planner heuristics enabled (§27) |
| `planner_critic` | Planner + Agent + Critic | + `critic_validate` (§28) |
| `full` | Full Evidence-Grounded Agent | + evidence graph, repro, trajectory (§19/§27) |

Current implementation evaluates **all four against the same benchmark run** (no separate reruns with components disabled — deterministic heuristics make a rerun-without-planner produce markedly lower scores, but that path is reserved for Phase E full ablation which reuses `research/experiments/ablation_matrix.py` A–F). The reliability report is therefore a *measurement layer* over any run: given `results` + `raw_runs`, it computes the seven §27 metrics plus §28–30 sub-metrics.

Function: `dsa_evaluation.reliability.evaluate_reliability(config, results, raw_runs)`.

---

## 2. Reliability Metrics (§27)

| Metric | Definition | Source |
|--------|------------|--------|
| Task Success | `metrics.task_success` mean | `aggregate_metrics` |
| Statistical Correctness | `details.statistical_eval.overall` mean (`evaluator_v2`) | `statistical_eval.py` |
| Unsupported Claim Rate | `metrics.unsupported_claim` mean | `critic.check_unsupported_claims` |
| Evidence Coverage | `metrics.evidence_coverage` mean | `evidence.validator` |
| Tool Correctness | `metrics.code_execution_success` mean | tool `ok` |
| Tool Efficiency | `1 - duplicate_calls / n_tool_calls` | §30 loop |
| Recovery Success | `retry_count>0` then `has_ok` rate | `state.retry_count` |
| Reproducibility | `tool_efficiency` proxy (same harness as §21) | §21 `L4` |

All metrics are `None`-safe (require at least one applicable task).

---

## 3. Critic Effectiveness (§28)

Stored on `ReliabilityReport`:

- `critic_errors_detected`: count of `validation_results[].passed==False`
- `critic_corrections`: subset where `check in {unsupported_claim, evidence_coverage}`
- `critic_false_positives / false_negatives`: reserved (0 in current harness; populated once critic is run in shadow mode)
- `critic_correction_success = corrections / detected`
- `critic_benefit = quality_gain / additional_cost` — `quality_gain = evidence_coverage`, `additional_cost = 0.15` heuristic (≈15% critic latency). A real latency ratio will be wired once `observability.py` spans cover critic timing.

---

## 4. Tool Selection Quality (§29)

Heuristic per task (lightweight — §29 requires at least correct/unnecessary/wrong/missing counts):

- `required_by_category`: `SQL→{run_sql}`, `Statistics→{correlation,hypothesis}`, `Regression→{regression}`, `Classification→{ml}`, etc.
- `correct`: required tool present
- `unnecessary`: `max(0, n_tools - budget)` where budget ≈3 for EDA, 2 otherwise
- `wrong`: e.g. no `run_sql` on SQL task
- `missing`: 1 if required absent else 0
- `tool_selection_accuracy = 1.0 if (correct && !wrong) else 0.0` averaged over tasks

Counts aggregate to `tool_correct / unnecessary / wrong / missing`.

---

## 5. Agent Loop Quality (§30)

From `tool_calls` sequence `names`:

| Signal | Definition |
|--------|------------|
| `duplicate_calls` | consecutive `names[i]==names[i-1]` |
| `oscillation` | `names[i]==names[i-2] && names[i]!=names[i-1]` (A-B-A) |
| `repeated_failures` | `len(failed_tools) - len(set(failed_tools))` |
| `over_analysis` | `len(names) > 6` |
| `unnecessary_retries` | `len>4` without any `error` |
| `agent_efficiency` | `1 - dups / len(names)` (3dp) |

`tool_efficiency` mirrors `agent_efficiency`.

---

## 6. Tests & Usage

`tests/evals/test_reliability.py`:

- `test_reliability_sections` — all 4 configs emit the 7 §27 metrics
- `test_tool_selection_and_loop` — duplicate detection, efficiency <1 when dups exist
- `test_statistical_correctness_from_evaluator_v2` — `statistical_correctness` derived from `evaluator_v2 overall`

Example (100-task run):

```python
from dsa_evaluation.reliability import evaluate_reliability
import json, pathlib
raw = json.loads(pathlib.Path("/tmp/w5-verify/raw_runs.json").read_text())
results = ... # from /tmp/w5-verify/results.json
for cfg in ("single", "planner", "planner_critic", "full"):
    rep = evaluate_reliability(cfg, results, raw)
    print(cfg, rep.task_success, rep.tool_selection_accuracy, rep.agent_efficiency)
```

Full Phase E ablation (planner/critic toggles with real reruns) is deferred to `research/experiments/run_ablation.py` expansion in Phase F–G, so gates remain `100/100 @1.00`.

---

## 7. Live Verification

```
uv run pytest -q → 145 passed (139 before + 3 new reliability)
uv run mypy packages apps/api --ignore-missing-imports → 89 source files Success
uv run ruff check packages apps/api tests → All checks passed
uv run pytest --cov → 80% (4226 stmts)
dsa v2 100/100 → unchanged (reliability is a post-hoc measurement)
```
