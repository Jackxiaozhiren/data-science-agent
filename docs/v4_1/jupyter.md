# Jupyter — V4.1 §28-32 (Experimental Real MVP)

**MVP (§28):** `%dsa`/`%%dsa` magic + `from data_science_agent import Agent; await agent.analyze()` rich HTML. `Stub is forbidden`.

**Magic:** `dsa_jupyter.magic.DSAMagic` (`%dsa profile|analyze|benchmark|doctor|plugin`, cell `%%dsa analyze ...\nquestion`) with `_run_sync` (`nest-asyncio` + thread fallback) for Jupyter loop.

**UX (§29):** `Ask → Run → Progress (Planner→Scientist→Critic→Report) → Chart → Evidence → Result` via `display_analysis`/`format_analysis_html` (header with meta, report Markdown, `tool_calls` progress, evidence table, insights, artifacts).

**Artifacts (§30):** `Chart` (`artifacts/charts/*.png` + base64), `Table` (`Polars head`), `Evidence`, `Report`, `Artifact` all embedded; `register_formatter` for `Analysis`.

**Reproducibility (§31):** `collect_notebook_metadata` → `dataset_hash` (16hex, `sha256` of file), `agent_version`, `sdk_version`, `prompt_version` (12hex of task), `tool_version`, `experiment_id` (`run-*`) — shown in header, for `notebook.metadata` / `analysis.ipynb`.

**Install (§32):** `pip install "jack-data-science-agent[jupyter]"` (`dsa-jupyter 0.1.0` workspace, `ipython>=8.0`, `nest-asyncio`), `uv sync --dev` + `uv build --package dsa-jupyter` verified.

**Tests:** `tests/jupyter` 10 (magic, profile/analyze, cell, await display, artifacts, metadata, formatter, pip install, error).

See `apps/jupyter/README.md` + `W4_JUPYTER.md`.
