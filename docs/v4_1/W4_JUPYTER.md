# W4 Jupyter Real Integration — Completion Report 2026-08-21

> Workstream W4 (§28-32) — Stub → Real MVP (§28).

## Summary

W4 replaces `apps/jupyter` stub with **real MVP**: `%dsa` magic + `Agent` rich display + 6-step UX + artifact embedding + reproducibility metadata + clean-env install.

Forbidden to treat stub as done (§28) — now verified via `tests/jupyter` 10/10.

## Changes

| File | Change |
|------|--------|
| `apps/jupyter/pyproject.toml:1` | New `dsa-jupyter 0.1.0` (hatch, `src/dsa_jupyter`, deps `ipython/nest-asyncio/polars`) — workspace member |
| `apps/jupyter/src/dsa_jupyter/__init__.py:1` | Expose `DSAMagic`, `display_analysis`, `load_ipython_extension` |
| `apps/jupyter/src/dsa_jupyter/magic.py:1` | `DSAMagic` (`%dsa`/`%%dsa`) — line+cell magic, handles `profile/analyze/benchmark/doctor/plugin`, `_run_sync` with `nest_asyncio` + thread fallback for Jupyter loop (§29), progress HTML |
| `apps/jupyter/src/dsa_jupyter/display.py:1` | `format_analysis_html`/`display_analysis`/`register_formatter` — HTML header with meta, report Markdown, tool_calls progress, evidence table, insights, artifacts (chart Image via file/base64) (§29-30) |
| `apps/jupyter/src/dsa_jupyter/metadata.py:1` | `collect_notebook_metadata`/`dataset_hash` — §31 6 fields (dataset_hash 16hex, agent_version, sdk_version, prompt_version 12hex, tool_version, experiment_id) |
| `apps/jupyter/README.md:1` | Rewrite stub → real (install, MVP, UX, artifacts, reproducibility, tests) |
| `docs/v4/jupyter.md:1` | Rewrite W6 stub → W4 real (magic, UX flow, artifacts, reproducibility, install, tests) |
| `pyproject.toml:78` | Add `apps/jupyter` to `tool.uv.workspace.members`, `dsa-jupyter` to `tool.uv.sources`, `jupyter` extra adds `dsa-jupyter+ipython+nest-asyncio`, dev includes `dsa-jupyter` |
| `pyproject.toml:114` | Add `apps/jupyter/**/*` ruff per-file ignores |
| `tests/jupyter/test_jupyter_integration.py:1` | 10 tests §28-32 (magic help/profile/analyze/cell, await display, artifacts, metadata, formatter, pip install, error handling) |

## Verification (§28-32)

```bash
# §28 MVP
uv run python -c "import dsa_jupyter; print(dsa_jupyter.__version__)"  # 0.1.0
uv run ipython -c "import dsa_jupyter; print('ok')"  # ok
python -c "from IPython.testing.globalipapp import get_ipython; ip=get_ipython(); ip.run_line_magic('load_ext','dsa_jupyter'); ip.run_line_magic('dsa','--help')"  # Markdown help

# SDK
uv run python -c "
from data_science_agent import Agent
import asyncio
async def f():
    r = await Agent().analyze('benchmarks/v2/datasets/sales.csv','Analyze revenue')
    from dsa_jupyter.display import format_analysis_html
    print(format_analysis_html(r)[:200])
asyncio.run(f())
"

# Magic 6-step (§29)
# In IPython:
# %load_ext dsa_jupyter
# %dsa profile benchmarks/v2/datasets/sales.csv
# %dsa analyze benchmarks/v2/datasets/sales.csv --task "Analyze revenue"
# → Analysis(run-..., COMPLETED, 4 evidence) with HTML header/report/progress/evidence/insights/artifacts

# Artifacts (§30) — chart/table/evidence/report/artifact all embedded
# display_analysis shows Image for chart, df.head() for table, evidence table, Markdown report

# Reproducibility (§31)
uv run python -c "from dsa_jupyter.metadata import collect_notebook_metadata; print(collect_notebook_metadata('benchmarks/v2/datasets/sales.csv','Analyze revenue','run-123'))"
# {'dataset_hash':'96fabf8340c8f6e1','agent_version':'0.1.0','sdk_version':'4.0.0','prompt_version':'53a1f8...','tool_version':'0.1.0','experiment_id':'run-123'}

# Installation (§32)
pip install "data-science-agent[jupyter]"  # via optional-dependencies jupyter = [dsa-jupyter,ipython,ipykernel,nest-asyncio]
uv sync --dev && uv run python -c "import dsa_jupyter; print('clean env ok')"
uv build --package dsa-jupyter  # wheel dsa_jupyter-0.1.0-py3-none-any.whl

# Tests
uv run pytest tests/jupyter -v  # 10 passed
uv run ruff check apps/jupyter
# All checks passed!
uv run mypy apps/jupyter --ignore-missing-imports  # (per-file ignores, IPython stubs)
```

## Maturity Update

| Capability | Before | After W4 | Evidence |
|------------|--------|----------|----------|
| Jupyter Integration | Stub | **Experimental (Real MVP)** → Stable after W8 | `%dsa` + `Agent` rich + 10 tests, `uv run pytest tests/jupyter` 10/10, `pip install` verified |

`Stub` forbidden — now `STATUS PASS` per §28. Full `Stable` after external validation (W8).

## Risks / Next

- No `jupyter lab` extension (only IPython magic + display) — sufficient for MVP, matches §28 minimal.
- No `notebook.metadata` auto-injection (display header only) — W4 stores meta in HTML, full `.ipynb` metadata injection is W8/W10.
- `nest-asyncio` is required for `asyncio.run` inside Jupyter — documented in deps.

## Stop Condition (§72)

W4 implements `Inspect→Plan→Implement→Test→Security→Benchmark→Document→Commit→STOP`. Do not auto-enter W5.
