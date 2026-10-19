# Getting Started

Three steps: install → run your first analysis → use the SDK, API, or dashboard.

## Prerequisites

- **Python ≥ 3.12** — the floor `pyproject.toml` declares (`requires-python = ">=3.12"`), and the only
  version CI runs (`python-version: "3.12"`). No older interpreter is tested anywhere.
- **uv** — recommended for contributors and repository development
- **Node 20 or newer** — only needed for the web dashboard. The version everything is aligned on is the
  one CI proves: it installs and builds the dashboard on Node **26**, and `docker/Dockerfile.web` runs
  `node:26-alpine` for both its builder and its runtime stage. That pairing is checked, not remembered —
  `tests/test_runtime_version_claims.py` compares the image's base major against `ci.yml` and fails if they
  diverge. (Until §137 the image shipped `node:20-alpine` while CI proved only 22, and the page's job was
  to state the gap rather than close it.)

## 1. Install

### macOS / Linux

Install `uv`, then sync the repository if you are contributing:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync --dev
```

Or install only the published Python package:

```bash
pip install jack-data-science-agent
```

### Windows PowerShell

Install `uv` with Astral's official PowerShell installer:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
uv --version
```

If `uv` is not found immediately after installation, close and reopen PowerShell so the updated user `PATH` is reloaded. The standalone installer normally places the executable under `$HOME\.local\bin`; you can verify it directly with:

```powershell
& "$HOME\.local\bin\uv.exe" --version
```

For a contributor checkout of this repository:

```powershell
uv sync --dev
uv run dsa demo
```

For only the published package, Python's launcher keeps the interpreter version explicit:

```powershell
py -3.12 -m pip install jack-data-science-agent
dsa demo
```

If `dsa` is not recognized after a successful `pip install`, reopen PowerShell and confirm the package is installed with `py -3.12 -m pip show jack-data-science-agent`. Then ensure the Scripts directory for that Python installation is on your user `PATH`.

## 2. First analysis

### macOS / Linux

```bash
# One-command demo: demo dataset → analysis → evidence → report
uv run dsa demo

# Or run it on your own CSV:
uv run dsa analyze examples/datasets/sales.csv --task "Does price predict revenue?"
```

### Windows PowerShell

From a repository checkout:

```powershell
uv run dsa demo
uv run dsa analyze ".\examples\datasets\sales.csv" --task "Does price predict revenue?"
```

With the published package installed via `pip`, use the same command without `uv run` and quote Windows paths that contain spaces:

```powershell
dsa analyze "C:\Users\me\Documents\sales data.csv" --task "Does price predict revenue?"
```

Every result is evidence-grounded: each claim is linked to a specific tool call and
the `sha256` of the dataset it ran on. Output also includes a reproducibility bundle
(`reproduce.sh`, `analysis.ipynb`, `experiment.json`).

## 3. Use it as a library

```python
import asyncio
from data_science_agent import Agent

result = asyncio.run(
    Agent().analyze(
        "examples/datasets/sales.csv",
        "What drives revenue by region?",
    )
)
print(result.report_markdown)  # prose + charts, every claim cited
print(result.evidence)  # Insight → Evidence → ToolCall → Dataset(hash)
```

## Run the whole thing with one command

```bash
dsa ui                              # API on :8000, dashboard on :3000, data in ~/.dsa/ui
dsa ui --data-dir ./my-analysis     # same, with the database and artifacts somewhere you choose
dsa ui --json                       # preflight only: what would stop a start, then exit
```

One process supervises both, binds loopback, prints the single URL to open, and stops both on one `Ctrl-C`
(or a `SIGTERM`) — the ports are free again afterwards, with nothing left listening. Your data never leaves the
machine: DSA makes no outbound request except the model endpoint you configure, and with `DSA_LLM_MODE` unset
the run is answered by the deterministic planner, so nothing is billed. Checked on the locally served pages
(`/`, `/datasets`, `/analysis`): none of them loads a third-party script, style or font — the only
non-loopback reference in the markup is the repository link in the header, which is a link, not a fetch.

Two things are checked before anything starts, because both fail confusingly otherwise:

- **The dashboard bundle.** It is built by Node, not by this package: `dsa ui` refuses and names
  `npm --prefix apps/web run build` when `.next` is missing **or older than the sources**, rather than serving
  you the previous product.
- **The API port.** `NEXT_PUBLIC_API_URL` is compiled into the client, so a bundle built for `:8000` cannot be
  pointed at `:9000` from the command line. `--api-port` is refused until you rebuild with that variable set.

```bash
dsa ui --port 3100 --api-port 8100 --web-dir apps/web --no-browser   # non-default ports, scripted
```

Choosing `--port`/`--api-port` is fine when you also rebuild; `--host` to something other than loopback needs
`--allow-public` as well, and `DSA_AUTH_TOKEN` should be set before you do that.

### Choose what produces the plan

`dsa ui` starts in `heuristic` mode: the deterministic planner answers, nothing leaves the machine, and no
provider is contacted. To run a model instead, open **Model settings** in the sidebar (or
`http://127.0.0.1:3000/settings`) and save the provider there -- no shell variables, no restart.

- The suggested first option is **Ollama**: free, local, and it keeps your data on the machine. Start it with
  `ollama serve`, pull a model (`ollama pull qwen3:8b`), then set the mode to `real` and the endpoint to
  `http://localhost:11434/v1`.
- Any OpenAI-compatible endpoint works the same way (endpoint, model name, credential). A hosted endpoint means
  your question and your data go to it; the mode selector on that page says which of the two you are choosing.
- The credential is stored in `provider.json` **inside the `--data-dir` you chose, with mode 0600**, and is
  never sent back to the browser: the page cannot display it, so leaving the field blank means "keep the stored
  one" and the checkbox next to it means "remove it". Deleting the data directory deletes the key.
- Saving does not contact the provider. A test call would spend your credit or send your data out without being
  asked, so the page says the configuration was checked for shape only, and the first run is the real test.
- The mode that produced a finished run is recorded on the run (`reasoning`, with `source: stored` when the
  settings answered), so a plan from a model and a plan from the deterministic planner can be told apart after
  the fact rather than by memory.
- The hosted demo refuses this feature and says why on the same page: an instance with nowhere to keep a secret
  between visits should not accept one.

## Run the API server

```bash
uv run uvicorn dsa_api.main:app --app-dir apps/api/src --port 8000

# upload a dataset, then create an analysis run
curl -F "file=@examples/datasets/sales.csv;type=text/csv" http://localhost:8000/api/v1/datasets/
curl -X POST http://localhost:8000/api/v1/analysis/ \
  -H 'Content-Type: application/json' \
  -d '{"dataset_id":"<DATASET_ID>","user_query":"Analyze revenue trends"}'
curl "http://localhost:8000/api/v1/analysis/<RUN_ID>/report?format=markdown"
curl -H "Accept: text/event-stream" "http://localhost:8000/api/v1/analysis/<RUN_ID>/events"
```

## Web dashboard

```bash
cd apps/web && npm ci --legacy-peer-deps && npm run dev   # :3000
```

## Docker

```bash
docker compose up                  # api :8000, web :3000
docker compose logs -f api
```

## Health

```bash
curl http://localhost:8000/health    # {status, details:{db,duckdb,polars,llm}, version}
curl http://localhost:8000/ready
curl http://localhost:8000/version
```

## Where to go next

- [Architecture](architecture.md) — agent graph, tool layer, storage, security boundary
- [Tools](tools.md) — the 18 typed tools
- [Statistics](statistics.md) — statistical methods and guardrails
- [Evidence](evidence.md) — how claims are traced to data
- [API](api.md) — REST endpoints
- [MCP](mcp.md) — MCP server over the same tool layer
- [Benchmark](benchmark.md) / [Evaluation](evaluation.md) — how the system is measured
- [Reproducibility](reproducibility.md) — reproduce any run
- [Research](research.md) — published results and gap analysis
- [Security](security.md) · [Contributing](contributing.md)
