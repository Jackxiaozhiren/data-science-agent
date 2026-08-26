<div align="center">

# Data Science Agent

**From natural language to reproducible data science.**

Turns a question about your data into a completed analysis — with every claim traced
back to an executable tool call, the underlying computation, and the dataset it was run on.

[Documentation](docs/getting-started.md) ·
[SDK reference](docs/api.md) ·
[CLI](docs/benchmark.md) ·
[Changelog](CHANGELOG.md) ·
[Citation](CITATION.cff)

[![CI](https://img.shields.io/github/actions/workflow/status/Jackxiaozhiren/data-science-agent/ci.yml?label=CI&logo=github&logoColor=white)](https://github.com/Jackxiaozhiren/data-science-agent/actions)
[![PyPI version](https://img.shields.io/pypi/v/jack-data-science-agent)](https://pypi.org/project/jack-data-science-agent/)
[![Python ≥ 3.12](https://img.shields.io/pypi/pyversions/jack-data-science-agent)](https://pypi.org/project/jack-data-science-agent/)
[![License: MIT](https://img.shields.io/github/license/Jackxiaozhiren/data-science-agent)](LICENSE)

</div>

## What is it?

**Data Science Agent is an evidence-grounded autonomous data science platform.** You ask
a question in natural language — *"Does price predict revenue?"* — and it profiles your
data, runs the analysis (SQL, statistics, forecasting, ML, visualization), and produces a
report in which **every claim is linked to an evidence record**: a specific tool call, its
result, and the `sha256` hash of the dataset it ran on. No anonymous numbers, no fabricated
results.

```python
import asyncio
from data_science_agent import Agent

result = asyncio.run(Agent().analyze(
    "sales.csv",
    "Does price predict revenue, and is the effect statistically significant?",
))
print(result.report_markdown)   # prose + charts, every claim evidence-cited
print(result.evidence)          # Insight → Evidence → ToolCall → Dataset (hash)
```

## The key features are

- **Evidence-grounded output** — each insight traces the chain
  `Insight → Evidence → ToolCall → Dataset(sha256)`, so results can be audited, not trusted on faith.
- **Reproducible by default** — every run writes a bundle: `report.md`, `experiment.json`, `reproduce.sh`, `analysis.ipynb`, `evidence_graph.json`. Re-run it, get the same result.
- **Local-first, no cloud required** — runs fully on your machine (DuckDB, Polars, Python). A stub LLM means even heavy features degrade gracefully offline.
- **Benchmark-driven** — evaluated on two frozen internal benchmarks plus 8 real-world-style case studies, with results and limitations published.
- **One SDK, many surfaces** — `dsa` CLI, Python SDK, FastAPI server with an **MCP** endpoint, Jupyter magic, VS Code extension, and a plugin runtime for custom tools.

## Quickstart

```bash
# Install (Python ≥ 3.12)
uv sync --dev            # or: pip install jack-data-science-agent

# One-command smoke run: demo dataset → analysis → evidence → report
uv run dsa demo

# Your data, your question
uv run dsa analyze sales.csv --task "Does price predict revenue?"
```

`uv run dsa --help` exposes `profile`, `benchmark`, `init`, `reproduce`, `plugin`, and `mcp`.
Prefer the SDK? `from data_science_agent import Agent` works in any script or notebook.

## Using the SDK

### Create it
```python
import asyncio
from data_science_agent import Agent

result = asyncio.run(Agent().analyze(
    "sales.csv",
    "Which region drives the most revenue, and is the trend significant?",
))
```

### Run it
```bash
uv run dsa analyze benchmarks/v2/datasets/sales.csv \
  --task "Which region drives the most revenue?"
```

### Check it
```python
print(result.status)               # "COMPLETED" | "FAILED"
print(len(result.evidence))        # each evidence is traceable
for e in result.evidence:
    print(e.claim, "->", e.source_id, "->", e.result)
```

## How it works

```
your question ──▶ LangGraph agent ──▶ planner ──▶ data scientist ──▶ critic ──▶ reporter
                        │                 ◀──────── tools (18) ────────
                        ▼
              DuckDB · Polars · SQL/Stats · ML · Visualization · Evidence
                        │
                        ▼
      report.md + evidence graph + reproduce.sh + analysis.ipynb
```

The runtime is a **LangGraph** orchestrator running over a typed tool layer: dataset
profiling, read-only SQL on DuckDB, Python, statistical tests, forecasting, regression and
classification, feature importance, and visualization. Every tool call may emit an
`Evidence` record bound to the dataset hash, and a **critic** step rejects claims that
outrun their evidence (e.g. causal language without a causal check). The API layer
(see `apps/api`) wraps the same graph behind REST + **SSE streaming** + an MCP endpoint.

## Integrations

| Surface | Entry point |
|---|---|
| CLI | `uv run dsa <command>` — analyze, benchmark, reproduce, plugin, mcp |
| Python SDK | `from data_science_agent import Agent` |
| REST API | `apps/api` — FastAPI + Pydantic v2 + SQLAlchemy/SQLite, `/api/v1/analysis/...` |
| MCP | stateless MCP server mounted at `/mcp` over the same tool layer |
| Jupyter | `%load_ext dsa_jupyter` magic (see `apps/jupyter`) |
| VS Code | extension w/ dataset explorer + analysis replay (see `apps/vscode`) |
| Plugins | `dsa plugin install` — custom tool packages validated via `PluginManifest` |

## Evaluation

Numbers are what we measured on frozen benchmarks, with the version and commit recorded.

- **Benchmark v1** (`benchmarks/ds-agent-benchmark`, frozen): **50 / 50 tasks** at
  `task_success_rate = 1.0`, `1.0` statistical & SQL accuracy, `0.06` unsupported-claim rate.
- **Benchmark v2** (`benchmarks/v2`, catalog `0.3.0`, seed 42): **100 tasks · 30 datasets · 11 categories**.
- **8 case studies** (`case-studies/`) executed end-to-end; real tool failures are *kept* and
  documented as limitations rather than hidden.
- **Reproduction** harness: 6-dim `ReproductionScore` across execution / numerical / statistical
  / evidence / semantic dimensions.

A full, honest gap analysis (which failure modes the benchmarks *don't* cover) lives in
[`docs/research.md`](docs/research.md) — see also [`docs/benchmark.md`](docs/benchmark.md)
and [`docs/evaluation.md`](docs/evaluation.md).

## Why evidence-grounded?

Data-science outputs are only as trustworthy as the path from question to number. This
project treats that path as a first-class artifact:

- claims cite the exact computation and dataset (hash), not vibes;
- every run is reproducible from a bundle, so "works on my machine" becomes verifiable;
- the critic and evidence gates make the agent refuse claims it cannot back.

## Resources

- [Documentation](docs/getting-started.md) — get started, architecture, tools, statistics, security
- [SDK & API reference](docs/api.md)
- [MCP design](docs/mcp.md)
- [Contributing guide](CONTRIBUTING.md) · [Security](SECURITY.md) · [Changelog](CHANGELOG.md)
- [Cite this project](CITATION.cff)

## Contributing

Contributions are welcome — bug reports, docs, plugins, and benchmark tasks alike. Open an
issue or PR; CI gates on tests, mypy, ruff, the docs build, and `dsa verify-release`. See
[CONTRIBUTING.md](CONTRIBUTING.md) and our [Code of Conduct](CODE_OF_CONDUCT.md).

## License

[MIT](LICENSE)