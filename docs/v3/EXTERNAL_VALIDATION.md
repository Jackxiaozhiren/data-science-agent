# External User Validation — V3 Phase H (W8 §39–42)

> **Real external usability without developer-only paths, private datasets, or private credentials (§39). One-command demo (§40/47) + fresh-machine + installation metrics (§42).**

---

## 1. Clean Install (§39)

Goal:

```
git clone → install → run
```

Constraints (must NOT require):

- Developer-only paths, private datasets, private credentials, internal environment.

Current compliance:

- `git clone https://...` → `uv sync --dev` (lock `uv.lock` 114 packages, `pyproject` `^3.12`) → `uv run dsa demo` / `uv run dsa --catalog benchmarks/v2/catalog.json --datasets benchmarks/v2/datasets --limit 100`
- No private path: demo dataset is `demo/datasets/sales.csv` (copied from `benchmarks/v2/datasets/sales.csv`, synthetic seed 42, 500 rows).
- No credential: local-first (§34) `stub/small` LLM + `DuckDB + Polars` + `data/ + artifacts/` storage. `Cloud API Cost = $0` only for electricity/hardware; do not quote as "free" service (§75 note).

Verified: `uv run dsa demo` → `task_success true` (`4 tool_calls`, `1 insight`, `4 evidence`, `has_report true`, `~1.8s`), artifacts `demo/runs/demo/{report.md, state.json, manifest.json}`.

---

## 2. One-Command Demo (§40/47)

```bash
uv run dsa demo
# also: dsa demo (via [project.scripts] entry point)
```

Pipeline:

```
Demo Dataset (demo/datasets/sales.csv)
  ↓
Analysis (dsa_agent.graph.run_analysis + dsa_tools bootstrap → correlation + profile + charts)
  ↓
Evidence (4 evidence nodes, evidence_ids per insight)
  ↓
Report (report.md with ![chart] embeds, Limitations, Validation)
```

Artifacts: `demo/runs/demo/report.md` (the report), `state.json` (evidence graph + tool trace), `manifest.json` (`dataset/question/elapsed_ms/workdir`). Evidence package `demo/evidence/state.json` mirrors the trace for inspection.

Failure policy: `dsa demo` exits non-zero (`1`) only if `task_success false`; error payload includes `error` string. No private env assumed.

---

## 3. Fresh Machine Testing (§41)

| OS | Status | Note |
|----|--------|------|
| Linux | Tested (local stub) | `uv` + stub LLM + DuckDB path used in CI-reproducible flows (`dsa --limit 100` `100/100`) |
| macOS | Tested | Darwin `26.6 arm64` in this repo (`demo_pass true`, `external-validation` pass, `npm build 13/13`, `docker compose valid`) |
| Windows | Not supported must be explicit | Not tested; PowerShell `curl -F`, path separators, and `uv` shim may differ — documented here as limitation |

No silent Windows claim. If Windows support is needed, add it as a V3.1 `ROADMAP.md` item rather than claiming it now.

---

## 4. Installation Metrics (§42)

Record:

```
Cold Install Time   — time uv sync --dev on a fresh clone
First Launch Time   — import + tool bootstrap (dsa_tools bootstrap)
Demo Execution Time — wall time of dsa demo (question: "Analyze correlation between price and revenue")
Benchmark Setup Time — catalog load + task enumeration (100 tasks)
```

Harness:

```bash
uv run dsa external-validation
# → InstallationMetrics JSON: python_version, node_version, platform, install_present, demo_pass, demo_result, first_launch_time_ms, demo_execution_time_ms, benchmark_setup_time_ms, details.root/question/notes
```

Code: `packages/evaluation/src/dsa_evaluation/external_validation.py` (`run_demo`, `collect_installation_metrics`, `fresh_machine_checklist`).

Captured (this repo, macOS `26.6 arm64`, `Python 3.12.13`, `Node v24.15.0`):

| Metric | Value |
|--------|-------|
| Cold Install | not timed here — run `time uv sync --dev` on a fresh clone |
| First Launch | `~25–90ms` (tool bootstrap) |
| Demo Execution | `1.7–1.9s` (`4 tool_calls`, report `true`) |
| Benchmark Setup | `~2–5ms` (`100 tasks` `11 categories`) |

Tests: `tests/evals/test_external_validation.py` (3: `demo_pass true` local-first, `install_present + timings`, `fresh_machine_checklist` does not claim Windows).

---

## 5. Files

- `packages/evaluation/src/dsa_evaluation/external_validation.py` — `run_demo` / `collect_installation_metrics` / `fresh_machine_checklist`
- `packages/evaluation/src/dsa_evaluation/cli.py` — `dsa demo` + `dsa external-validation` subcommands (§47)
- `demo/{datasets,sales.csv, questions/demo-question.md, runs/demo/*, reports/demo-report.md, evidence/state.json, README.md}` — §46 demo package
- `tests/evals/test_external_validation.py` — 3 gates for W8
