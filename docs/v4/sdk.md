# SDK — V4 W2 (§14–20) — Distribution Hardening 2026-08-21

Stable facade `src/data_science_agent` (§14-15) — audited in `docs/v4_1/SDK_PUBLIC_API_AUDIT.md`:

```python
from data_science_agent import Agent, Dataset, Analysis, Evidence, Artifact, Benchmark, Reproduction

agent = Agent()  # Stable since 4.0.0
result = await agent.analyze(Dataset.from_path("sales.csv"), "Analyze revenue decline")
# or sync: agent.analyze_sync("sales.csv", "Analyze revenue")
profile = agent.profile("sales.csv")  # {"rows": 500, "columns": [...]}
bench = Benchmark().run(limit=1)  # BenchmarkResult(n_tasks=1, aggregate={...})
repro = Reproduction().run()  # ReproductionResult(overall=..., execution=..., by_level={...})
```

Public surface (§14):

| Export | Stability | Doc §16 |
|--------|-----------|---------|
| `Agent` (`analyze`, `analyze_sync`, `profile`, `version`) | **Stable** | Description/Params/Return/Errors/Example/Version in `sdk.py` |
| `Dataset` (`from_path`) | **Stable** | ✅ |
| `Analysis` | **Stable** | ✅ |
| `Evidence` / `Artifact` / `Insight` / `Report` | **Stable** | ✅ |
| `Benchmark` / `BenchmarkResult` | **Stable** | ✅ |
| `Reproduction` / `ReproductionResult` | **Stable** | ✅ |

Stability map: `API_STABILITY` in `src/data_science_agent/sdk.py:67` (all Stable). Internal `dsa_agent`, `dsa_tools`, `dsa_evaluation` etc. are `Internal` — public code must not import `_internal` (enforced by `tests/sdk/test_sdk_contract.py::test_sdk_no_internal_dependency_text`).

Contract tests (§17): `tests/sdk/test_sdk_contract.py` (18 tests: input/output/error/compat/serialization/async) + `tests/api/compatibility/test_sdk_compat.py` (2 tests). Gates: input schema, output schema, error schema, backward compat, serialization, async.

Package metadata (§18): `pyproject.toml` now includes `authors, maintainers, keywords, classifiers, urls, optional-dependencies (jupyter/time-series)`; `readme = "README.md"`; `tool.hatch.build`.

Installation (§19): `uv sync --dev` → `uv run python -c "from data_science_agent import Agent"` PASS; `pip install .` wheel via hatch.

CLI (§20): see `docs/v4_1/SDK_PUBLIC_API_AUDIT.md` table — all 11 subcommands now have `--help` + `--json` + correct exit codes (doctor/init/plugin/mcp/demo --json fixed 2026-08-21).

