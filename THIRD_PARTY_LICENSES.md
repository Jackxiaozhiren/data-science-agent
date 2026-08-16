# Third Party Licenses

## Runtime Dependencies (Python)

| Package | License | Notes |
|---|---|---|
| FastAPI | MIT | https://github.com/fastapi/fastapi |
| Pydantic | MIT | https://github.com/pydantic/pydantic |
| SQLAlchemy | MIT | https://github.com/sqlalchemy/sqlalchemy |
| DuckDB | MIT | https://github.com/duckdb/duckdb |
| Polars | MIT | https://github.com/pola-rs/polars |
| PyArrow | Apache-2.0 | https://github.com/apache/arrow |
| NumPy | BSD-3-Clause | https://github.com/numpy/numpy |
| SciPy | BSD-3-Clause | https://github.com/scipy/scipy |
| scikit-learn | BSD-3-Clause | https://github.com/scikit-learn/scikit-learn |
| Matplotlib | PSF + BSD | https://github.com/matplotlib/matplotlib |
| LangGraph / LangChain Core / LangSmith | MIT | https://github.com/langchain-ai/langgraph |
| Uvicorn | BSD-3-Clause | https://github.com/encode/uvicorn |
| HTTPX | BSD-3-Clause | https://github.com/encode/httpx |

## Frontend

| Package | License |
|---|---|
| Next.js | MIT |
| React / React-DOM | MIT |
| Tailwind CSS / PostCSS / Autoprefixer | MIT |
| TypeScript | Apache-2.0 |

## Tooling

Ruff (MIT), MyPy (MIT), Pytest (MIT), uv (MIT/Apache-2.0)

## Datasets

All benchmark datasets under `benchmarks/ds-agent-benchmark/datasets/` (20), `benchmarks/v2/datasets` (30, 20 v1 verbatim + 10 new), and `examples/datasets/` are **synthetic, deterministic (seed 42), public domain (CC0)** — no third-party dataset licenses required. When real public datasets are added (e.g., Titanic), record source/license/citation here per spec §69.

## Dependency Policy (V2 §69)

No new dependency may be added without documenting Purpose / License / Size / Security / Maintenance / Alternative / Why-needed, and updating this file. V2 added none beyond the frozen stack above.
