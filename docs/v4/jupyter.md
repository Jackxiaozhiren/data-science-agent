# Jupyter — V4 W4 Real Integration (§28–32)

**Maturity: Experimental (Real MVP)** — replaces stub (§28). `Stub is forbidden`.

## Entry Points

- **Magic**: `%dsa` (line) / `%%dsa` (cell) via `dsa_jupyter.magic.DSAMagic` — `apps/jupyter/src/dsa_jupyter/magic.py:1`
- **SDK**: `from data_science_agent import Agent; await agent.analyze(...)` → rich HTML via `dsa_jupyter.display` (§28)
- **Load**: `%load_ext dsa_jupyter` registers magics + `Analysis` formatter (`load_ipython_extension` in `magic.py:280`)

## UX Flow (§29)

`Ask → Run → Progress → Chart → Evidence → Result` — all in `display_analysis` (`display.py:1`):

- Progress: `tool_calls` list (10 max)
- Chart: `artifacts` + `tool_calls[].result.base64_png` rendered as `IPython.display.Image`
- Evidence: HTML table (`id | claim | source | confidence`)
- Report: `Markdown(report_markdown[:3000])`
- Result: `Analysis` dataclass with `run_id/status/evidence/insights/artifacts`

## Artifacts (§30)

- `Chart` (`artifacts/charts/*.png`, base64 fallback)
- `Table` (`pl.DataFrame.head()` HTML)
- `Evidence`/`Report`/`Artifact` all embedded; `format_analysis_html` includes them.

## Reproducibility (§31)

`dsa_jupyter.metadata.collect_notebook_metadata` returns `dataset_hash/agent_version/sdk_version/prompt_version/tool_version/experiment_id` — displayed in header of every analysis, suitable for `notebook.metadata` or `analysis.ipynb` bundle.

## Installation (§32)

```bash
pip install "jack-data-science-agent[jupyter]"  # or pip install dsa-jupyter
```

Verified: `uv sync --dev` + `uv run python -c "import dsa_jupyter"` + `ipython -c "import dsa_jupyter"` (§32 clean-env via `uv build`).

## Tests

`tests/jupyter/test_jupyter_integration.py` — 10 tests covering magic, profile/analyze, cell magic, await display, artifacts, metadata, formatter, pip install, error handling.

See `apps/jupyter/README.md` for full usage and `docs/v4_1/W4_JUPYTER.md` for hardening report.
