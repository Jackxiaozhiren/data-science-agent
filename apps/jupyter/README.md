# Jupyter Integration — V4 W4 Real Integration (§28–32)

**Maturity: Experimental → Stable (W4)** — Real `%dsa` magic + rich display (not stub). Stub is forbidden per §28.

## Installation (§32)

```bash
# From workspace (clean env verification)
pip install "jack-data-science-agent[jupyter]"  # pulls dsa-jupyter + ipython + nest-asyncio
# or
pip install dsa-jupyter  # standalone
# or local
pip install -e "apps/jupyter"
# + verify
python -c "import dsa_jupyter; print(dsa_jupyter.__version__)"
ipython -c "import dsa_jupyter; print('ok')"
```

`pyproject.toml` optional-dependencies: `jupyter = ["dsa-jupyter","ipython>=8.0","ipykernel>=6.0","nest-asyncio>=1.5"]` verified via `uv sync --dev` + `uv run python -c "import dsa_jupyter"`.

## MVP (§28)

```python
%dsa --help
%dsa profile sales.csv
%dsa analyze sales.csv --task "Analyze revenue"  # via magic

# SDK (rich)
from data_science_agent import Agent
agent = Agent()
result = await agent.analyze("benchmarks/v2/datasets/sales.csv", "Analyze revenue")
result  # auto HTML (via _repr_html_ patched by load_ext)

# also sync (outside Jupyter)
result = Agent().analyze_sync("sales.csv", "Analyze revenue")
```

Magic is `dsa_jupyter.magic.DSAMagic` (`%dsa` line + `%%dsa` cell). Load via `%load_ext dsa_jupyter` (auto on `import dsa_jupyter` patch).

## Notebook UX (§29) — 6-step closed loop

```
Ask Question
↓
Run Analysis (Agent Planner→Scientist→Critic→Report)
↓
Show Progress (tool_calls, status)
↓
Show Chart (artifact PNG + base64)
↓
Show Evidence (table Evidence→ToolCall)
↓
Show Result (report markdown + insights)
```

Tested in `tests/jupyter/test_jupyter_integration.py::test_jupyter_analyze_via_magic_6step` (<2s, 4 evidence).

Cell magic:

```python
%%dsa analyze benchmarks/v2/datasets/sales.csv
Analyze revenue trend over time and create a chart
```

## Artifact Integration (§30)

Directly embedded in Notebook (via `dsa_jupyter.display.display_analysis`):

- **Chart**: `artifacts/charts/*_forecast.png` rendered as `IPython.display.Image` (file + base64 fallback)
- **Table**: `df.head()` shown as Polars HTML
- **Evidence**: HTML table `id | claim | source | confidence` (10 rows max)
- **Report**: `Markdown(report_markdown[:3000])`
- **Artifact**: list `type: path`

Formatter registered in `display.register_formatter` for `Analysis` — so bare `result` shows HTML automatically.

## Reproducibility (§31)

Notebook metadata collected by `dsa_jupyter.metadata.collect_notebook_metadata`:

```python
from dsa_jupyter.metadata import collect_notebook_metadata
meta = collect_notebook_metadata("sales.csv", "Analyze revenue", run_id)
# {
#   "dataset_hash": "96fabf8340c8f6e1",  # sha256 of file (size+mtime+content)
#   "agent_version": "0.1.0",
#   "sdk_version": "4.0.0",
#   "prompt_version": "53a1f8e2399b",  # sha(task)
#   "tool_version": "0.1.0",
#   "experiment_id": "run-XXXX"
# }
```

Header in every `format_analysis_html` shows `dataset_hash/prompt/tool_version/experiment_id` — suitable for `notebook.metadata` or `analysis.ipynb` bundle.

## Example Notebook

See `tests/jupyter/test_jupyter_integration.py` for programmatic usage; a minimal notebook is:

```json
{
 "cells": [
  {"cell_type": "code", "source": ["%load_ext dsa_jupyter"]},
  {"cell_type": "code", "source": ["%dsa profile benchmarks/v2/datasets/sales.csv"]},
  {"cell_type": "code", "source": ["%dsa analyze benchmarks/v2/datasets/sales.csv --task \"Analyze revenue\""]},
  {"cell_type": "code", "source": ["from data_science_agent import Agent\nagent = Agent()\nr = await agent.analyze(\"benchmarks/v2/datasets/sales.csv\", \"Forecast next 30 days\")\nr"]}
 ]
}
```

## Tests (§26-style)

```bash
uv run pytest tests/jupyter -v  # 10 tests
# - help/profile/analyze (line+cell)
# - await Agent display + metadata
# - artifact (chart/table/evidence/report)
# - reproducibility all fields
# - auto _repr_html_
# - pip install + error handling
```
