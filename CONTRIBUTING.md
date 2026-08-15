# Contributing

See `ARCHITECTURE_FREEZE_V0.1.md` — follow phased, gate-controlled delivery.

Before PR:

```bash
uv sync --dev
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run pytest -q
```
