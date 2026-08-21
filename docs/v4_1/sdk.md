# SDK — V4.1 §14-20 (Stable)

**Public surface (§14):**

```python
from data_science_agent import Agent, Dataset, Analysis, Evidence, Artifact, Benchmark, Reproduction
# + Insight, Report, BenchmarkResult, ReproductionResult
from data_science_agent.sdk import API_STABILITY  # all Stable
```

**Audit (§15):** `SDK_PUBLIC_API_AUDIT.md` — Stable/Experimental/Internal/Deprecated, no `public → _internal`, `API_STABILITY` all `Stable`.

**Docs (§16):** Each Stable has Description/Params/Return/Errors/Example/Version in `src/data_science_agent/sdk.py` (658 lines, e.g. `Agent.analyze`).

**Contracts (§17):** `tests/sdk/test_sdk_contract.py` 18 (input/output/error/compat/serialization/async) + `tests/api/compatibility/test_sdk_compat.py` 2.

**Metadata (§18):** `pyproject.toml` `4.1.0` with `authors/maintainers/keywords/classifiers/urls` + `optional-dependencies` (jupyter, time-series).

**Install (§19):** `pip install .` via `uv build` `data_science_agent-4.1.0-py3-none-any.whl` (192 SBOM), `uv run python -c "from data_science_agent import Agent"` PASS.

**CLI (§20):** 11 subcommands `dsa --help/doctor/init/analyze/profile/benchmark/demo/verify-release` all `--help` + `--json` + exit `0/1/2` + structured errors (fixed `doctor --json` §20).
