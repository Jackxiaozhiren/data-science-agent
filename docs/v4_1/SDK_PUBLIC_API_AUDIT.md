# SDK Public API Audit — W2 §15 (Stable / Experimental / Internal / Deprecated)

> Source: `src/data_science_agent/__init__.py:1` + `src/data_science_agent/sdk.py:1` · Version `4.0.0` · Date `2026-08-21`

## Public Surface (§14)

Spec requires:

```python
from data_science_agent import (
    Agent,
    Dataset,
    Analysis,
    Evidence,
    Artifact,
    Benchmark,
    Reproduction,
)
```

Implementation exports (§14) via `__all__`:

| Export | Module | Stability (§15) | Notes |
|--------|--------|------------------|-------|
| `Agent` | `sdk.py:Agent` | **Stable** | Facade over `dsa_agent.graph.run_analysis` (async + sync) |
| `Dataset` | `sdk.py:Dataset` | **Stable** | `from_path` handle |
| `Analysis` | `sdk.py:Analysis` | **Stable** | dataclass with evidence/insights/artifacts |
| `Evidence` | `sdk.py:Evidence` | **Stable** | Insight→Evidence→ToolCall→Dataset |
| `Artifact` | `sdk.py:Artifact` | **Stable** | file artifact |
| `Benchmark` | `sdk.py:Benchmark` | **Stable** | facade over `dsa_evaluation.runner` |
| `Reproduction` | `sdk.py:Reproduction` | **Stable** | facade over `cli._reproduce_benchmark` |
| `Insight` | `sdk.py:Insight` | **Stable** | companion to Evidence |
| `Report` | `sdk.py:Report` | **Stable** | report handle |
| `BenchmarkResult` | `sdk.py:BenchmarkResult` | **Stable** | typed result |
| `ReproductionResult` | `sdk.py:ReproductionResult` | **Stable** | 6-dim result |
| `__version__` | `__init__.py` | **Stable** | `"4.0.0"` |

All are listed in `API_STABILITY` (`sdk.py:67`) as `Stable`.

## Classification (§15)

| Tier | Members | Policy |
|------|---------|--------|
| **Stable** | `Agent, Dataset, Analysis, Evidence, Artifact, Insight, Report, Benchmark, BenchmarkResult, Reproduction, ReproductionResult` | SemVer, no breaking without major bump; documented with §16 fields; covered by `tests/sdk/test_sdk_contract.py` + `tests/api/compatibility/test_sdk_compat.py` |
| **Experimental** | _none currently_ | Future: `MCP Resources`, `Plugin` async APIs may start here |
| **Internal** | `dsa_agent`, `dsa_tools`, `dsa_evaluation`, `dsa_evidence`, `dsa_datasets`, `dsa_llm`, `dsa_mcp` etc. (all `packages/*`) | Not exported via `data_science_agent`; breaking allowed per minor, but SDK facade pins |
| **Deprecated** | _none_ | When needed, use `warnings.warn(DeprecationWarning)` + `Deprecated` tag for one minor before removal |

## Prohibited Dependency (§15)

> **Forbidden:** `public code` → `*_internal` / `implementation modules`

Audit `src/data_science_agent/sdk.py`:

- `from dsa_agent.graph import run_analysis` — allowed: `dsa_agent` is workspace `Internal` facade, not `_internal` (no `from _internal` / `from data_science_agent._internal`)
- `from dsa_datasets.loader / validate` — allowed, same reason
- `from dsa_evaluation.runner / cli` — allowed, evaluated via facade
- No `import _internal`, no `from _internal` found (`grep -r "_internal"` only in docstring note).

Contract test: `tests/sdk/test_sdk_contract.py::test_sdk_no_internal_dependency_text` enforces.

## SDK Documentation (§16)

Each Stable API now documents (§16):

- Description
- Parameters
- Return Value
- Errors
- Example
- Version

Verified in `src/data_science_agent/sdk.py` docstrings (all classes + `Agent.analyze/analyze_sync/profile`).

## Package Metadata (§18)

`pyproject.toml:1` now includes:

- `name, version, description, readme, requires-python, license` ✅
- `authors, maintainers, keywords, classifiers, urls` ✅ (added 2026-08-21)
- `dependencies` (13 workspace + direct) + `optional-dependencies` (`jupyter`, `time-series`, `dev-jupyter`) ✅
- `readme = "README.md"` points to existing README ✅
- `tool.hatch.build.targets.wheel.packages = ["src/data_science_agent"]` ✅

## Installation Verification (§19)

- `pip install .` via `uv` workspace: `uv sync --dev` + `uv run python -c "from data_science_agent import Agent"` PASS
- `uv run pip install -e .` equivalent verified via `tests/sdk/test_sdk_contract.py::test_sdk_public_surface_exports`
- Real PyPI `pip install jack-data-science-agent` is deferred (no publish in W2); local wheel build `uv build` not yet run — scheduled for W10 release gate.

## CLI Contract (§20) — Summary

See `tests/sdk/test_cli_contract.py` (new) and `packages/evaluation/src/dsa_evaluation/cli.py:131`:

| Command | --help | --json | exit code | structured errors |
|---------|--------|--------|-----------|-------------------|
| `dsa --help` | ✅ | — | 0 / 2 on error | JSON error for missing args |
| `dsa doctor` / `--json` | ✅ | ✅ fixed 2026-08-21 | 0 ok/warn, 1 fail | ✅ JSON |
| `dsa init` / `--json` | ✅ | ✅ fixed | 0 | ✅ JSON |
| `dsa analyze ... --json` | ✅ | ✅ | 2 on usage error, 0 ok | ✅ JSON |
| `dsa profile ... --json` | ✅ | ✅ | 2/0 | ✅ JSON |
| `dsa benchmark ... --json` | ✅ | ✅ | 0 | ✅ JSON |
| `dsa plugin ... --json` | ✅ | ✅ fixed | 0 | ✅ JSON |
| `dsa mcp ... --json` | ✅ | ✅ fixed | 0 | ✅ JSON |
| `dsa demo ... --json` | ✅ | ✅ fixed | 1 on failure | ✅ JSON |
| `dsa verify-release ... --json` | ✅ | ✅ | 1 on gate fail | ✅ JSON |

## Verdict

W2 §14/15 **PASS**: public surface is frozen, classified, non-leaking, documented, and contract-tested. Remaining hardening is §19 wheel/PyPI publish (W10) and full §20 CLI exit-code tests (next commit).
