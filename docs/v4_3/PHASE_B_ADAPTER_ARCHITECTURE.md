# Phase B — External Benchmark Adapter Architecture (V4.3 W2, §15-21)

> **Phase:** B — External Benchmark Architecture
> **Date:** 2026-08-28 · **Base:** `c8903d4` (`v4.2.10-1`) + Phase A freeze commit
> **Scope:** adapter *layer* only. No specific benchmark is integrated (DataSciBench = Phase C, DSAgentBench = Phase D), per §99 phase discipline.
> **Architecture Freeze (§7):** additive module + tests + docs only; no change to LangGraph runtime, evaluation framework internals, or any protected surface.

---

## 1. What was inspected (Inspect → Plan)

Phase A readiness audit (`V4_2_FINAL_TRUTH.md` §15) found: no `ExternalBenchmarkAdapter`, no gold isolation boundary, no UNSUPPORTED outcome, no external manifest. The internal runner passes the whole `task` object (gold included) around in a single process. Phase B adds the missing architecture **without touching** the internal benchmark path.

## 2. Design (Plan → Implement)

New module: `packages/evaluation/src/dsa_evaluation/external_benchmark.py`

| Spec | Deliverable | Implementation |
|------|-------------|----------------|
| §17 Adapter Interface | `ExternalBenchmarkAdapter` Protocol (`runtime_checkable`) | `name/version/prepare/list_tasks/run_task/evaluate/export_results` |
| §18 Manifest | `ExternalBenchmarkManifest` (pydantic) | all 15 required fields + `write()` for versioned JSON emission |
| §19 Gold firewall | `AgentTaskView` + `assert_gold_isolation()` | agent runtime receives *only* the view; `extra="forbid"` makes smuggling gold fields a construction error; runtime tripwire rejects serialized payloads carrying `gold/ground_truth/rubric/...` keys |
| §16 Original evaluator | `evaluate(run)` signature | takes **only** the run; gold is applied inside the adapter, behind the boundary — the harness never mediates agent output ↔ gold |
| §20 Isolation | module separation + lazy agent import | evaluation-facing code imports no agent runtime; `AgentBackedRunner` imports DSA lazily so evaluator-only processes stay agent-free. Full process isolation is a Phase C+ hardening (subprocess runner seam already isolated by this split) |
| §26 Outcome taxonomy | `TaskOutcome` + `classify_outcome()` | `passed / failed / unsupported / execution_error`; unsupported tasks carry a mandatory reason and are reported, never filtered; completed-but-unevaluated is **not** a pass |
| §21 Integrity | `INTEGRITY_RULES` + guard placement | constraints encoded at the firewall (`assert_gold_isolation` runs before every agent dispatch) and documented for review/ADR enforcement |
| §41 Run isolation | `RunConfig` | model/provider/seed/temperature/prompt_version captured per run |

Reference runner: `AgentBackedRunner` — maps `ExternalTask → agent_view() → Agent().analyze_sync → ExternalRun`, skipping unsupported tasks without invoking the agent.

## 3. Verification (Execute → Test → Evaluate)

```text
pytest tests/evals/test_external_benchmark.py   → 10/10 passed
mypy packages apps/api src                      → Success: no issues in 105 files (+1 module)
ruff check + ruff format                        → clean
full pytest suite                               → 263 passed (253 + 10 new), no regressions
```

Test coverage map: protocol conformance, gold dropped from view, structural `extra="forbid"` block, runtime tripwire, unsupported reported with reason, unevaluated ≠ passed, execution error classification, manifest field completeness + JSON emission, `export_results` path contract, `prepare` idempotence, dataset hashing.

## 4. What Phase C/D must build on this

- **Phase C (DataSciBench):** implement `ExternalBenchmarkAdapter` in `benchmarks/external/datascibench/` using the benchmark's original tasks/evaluator/licenses (§22-23); map unsupported tasks to `UNSUPPORTED` + reason (§26); emit `ExternalBenchmarkManifest` + `research/external/datascibench_results.json`.
- **Phase D (DSAgentBench):** feasibility audit first (§29); reuse `AgentBackedRunner` or a subprocess runner for the §30 real-computer boundary — do not replace benchmark environments with internal APIs unless rules allow.
- **Hardening candidates (non-blocking):** subprocess-level agent/evaluator separation on top of the existing module seam; per-run prompt/tool version pinning beyond `RunConfig`.

## 5. Honest limitations

- This phase proves the *architecture*, not any external score. No benchmark numbers exist yet — none may be claimed until Phase C/D run real evaluations (§108).
- `assert_gold_isolation` is a tripwire over known gold key names; adapters must extend it if their benchmarks use exotic vocabularies. It complements, not replaces, the structural guarantee (`extra="forbid"` + view-only construction).
- Process isolation is module-level only at this point (§20 minimum), as recorded in Phase A §15.
