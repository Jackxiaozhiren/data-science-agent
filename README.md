# Data Science Agent

> **An Evidence-Grounded Autonomous Data Science System.**
> Turn natural-language questions into reproducible statistical analysis, machine learning experiments, visualizations, and research reports.

## Architecture Freeze

See [ARCHITECTURE_FREEZE_V0.1.md](./ARCHITECTURE_FREEZE_V0.1.md) — Phase 0 frozen. No business code until approval.

## Quick Start (Phase 1 Scaffold)

```bash
uv sync --dev
uv run pytest -q
uv run ruff check .
uv run mypy .

# API
uv run uvicorn dsa_api.main:app --reload --port 8000

# Web
cd apps/web && npm install && npm run dev
```

## Stack

Next.js 15 + TypeScript + Tailwind + shadcn/ui + Plotly | FastAPI + Pydantic v2 + SQLAlchemy | LangGraph | DuckDB + Polars + PyArrow | SQLite | LLM Abstraction (OpenAI/Anthropic/Google/OpenRouter/Ollama)
