# Cross-Model Evaluation — V3 Phase F (W6 §31–34)

> **Phase F · W6 Cross-Model Evaluation** · Date: 2026-08-16 · §31–34 · `dsa_evaluation.cross_model`

---

## 1. Categories (§31)

| Class | Meaning | Provider probing |
|-------|---------|------------------|
| `local_small` | Local Small Model | `ollama/small` if `OLLAMA_HOST/MODEL` else `stub/small` — **always available** (§34) |
| `local_medium` | Local Medium Model | `ollama/medium` if `OLLAMA_HOST` else `stub/medium` — always available |
| `open_api` | Open API Model | `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GOOGLE_API_KEY` present → available |
| `frontier` | Frontier Model | `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` → available |

**Policy (§31): Do not fabricate.** When a required key is absent, the record is `available: false, reason: "NOT RUN — no API key configured"` and all metrics are `None`. No synthetic `task_success 0.92` is invented.

---

## 2. Matrix (§32)

`CrossModelMatrix {records: list[ModelRecord], frontier_*, cost_model, details}`

`ModelRecord` (one per class):

| Field | Type | §32 mapping |
|-------|------|-------------|
| `model_class` | `local_small \| local_medium \| open_api \| frontier` | — |
| `model_id` | `str` | e.g. `local_small:stub`, `open_api:not_run` |
| `provider` | `str` | `stub/small`, `ollama/medium`, `openai`, … |
| `available` | `bool` | key/probe gated |
| `task_success` | `float \| None` | from `aggregate.task_success_rate` |
| `statistical_accuracy` | `...` | `aggregate.statistical_accuracy` |
| `evidence_coverage` | `...` | `evidence_coverage` |
| `unsupported_claim_rate` | `...` | `unsupported_claim_rate` |
| `tool_selection_accuracy` | `...` | caller-supplied if available |
| `latency_ms` | `float \| None` | `aggregate.mean_latency_ms` |
| `token_input/output/total` | `int \| None` | caller-supplied `token_estimates` |
| `cost_usd` | `float \| None` | stub heuristic (see §3) |
| `failure_rate` | `float \| None` | `1 - task_success` |

Builder:

```python
from dsa_evaluation.cross_model import build_cross_model_matrix
from pathlib import Path
import json

# From a real benchmark run's aggregate
agg = json.loads(Path("reproduction/v2/results.json").read_text())["first"]  # any aggregate
m = build_cross_model_matrix(
    {"local_small": agg, "local_medium": agg},  # open/frontier omitted → NOT RUN
    token_estimates={"local_small": (1200, 800)},
)
```

If `results_by_class` omits a local class, it is still emitted as `NOT RUN — run with local stub to populate (§34)`.

---

## 3. Frontier (§33) — Do not claim “Model X is best”

Three frontiers are emitted without a verdict:

- `frontier_quality_cost: list[{cost_usd, quality, model, class}]`
- `frontier_quality_latency`
- `frontier_quality_tokens`

Construction: sort available records with numeric `task_success` + numeric key (`cost_usd` / `latency_ms` / `token_total`) by the key ascending; keep the **Pareto frontier** (keep points whose `quality` is maximal so far). This surfaces the trade-off — e.g. local stub `quality 1.0` at `cost 0` dominates small-cost open models until a frontier model lifts `quality`.

`cost_model`:

```
stub heuristic: local 0, open_api 0.002/1k, frontier 0.01/1k — placeholder to demonstrate
trade-off (§33); real costs require provider billing
```

`cost_usd` is therefore a **ranking placeholder**, not billing. The frontier still demonstrates the intended shape, and any real billing must replace this heuristic.

---

## 4. Local-First Validation (§34)

At least one full benchmark must run **without paid cloud**:

- `Local LLM` → `StubLLMProvider` (deterministic, no key)
- `Local Data Engine` → `DuckDB + Polars` (no external DB)
- `Local Storage` → `data/ + artifacts/ + reproduction/` (no S3)

This is satisfied today: `uv run dsa --catalog benchmarks/v2/catalog.json --datasets benchmarks/v2/datasets --limit 100` uses **no cloud credential** and achieves `100/100 @1.00` on both `local_small` and `local_medium` stubs.

`Cloud API Cost = $0` for local runs — local `cost_usd` is `0.0` in the matrix.

---

## 5. Tests

`tests/evals/test_cross_model.py`:

- `test_matrix_no_fabrication` — open/frontier are `NOT RUN` without keys; local is available
- `test_matrix_with_real_agg_and_frontier` — real agg populates `task_success 1.0` and frontier list
- `test_local_first_is_stub_runnable` — both locals are `stub/*`

Full suite: `148 passed`.

---

## 6. Live Verification

```
uv run pytest -q → 148 passed
uv run mypy packages apps/api --ignore-missing-imports → 90 source files Success
uv run ruff check packages apps/api tests → All checks passed
dsa 100/100 — local_small stub 1.0 stable (no API key required)
```
