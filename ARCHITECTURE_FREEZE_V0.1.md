# Data Science Agent — Phase 0 Architecture Freeze (V0.1)

> Status: FROZEN for V0.1 implementation | Date: 2026-08-15
> Principle: Evidence Before Claim | Code Before Claim | Statistical Rigor Before Fluency

---

## 1. System Architecture (Layered)

```
┌─────────────────────────────────────────────────────┐
│ Frontend  Next.js 15 + TypeScript + Tailwind +      │
│           shadcn/ui + Plotly (SSE client)           │
└──────────────────────┬──────────────────────────────┘
                       │ HTTPS / SSE
┌──────────────────────▼──────────────────────────────┐
│ API Layer  FastAPI + Pydantic v2 + SQLAlchemy        │
│  /api/v1/datasets  /analysis  /artifacts  /reports  │
│  Auth (future) · Validation · Rate Limit · Logging  │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│ Agent Runtime  LangGraph Stateful Graph              │
│  Planner → DataScientist → Critic → Report          │
│  State: AnalysisState · Checkpoints · Retry(3)      │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│ Tool Layer  Typed Tool Contract (async execute)      │
│  Data | SQL | Python | Stats | ML | Viz | Evidence │
└──────┬──────────┬───────────┬───────────┬───────────┘
       │          │           │           │
   DuckDB    Python Sandbox  Stats/ML   Viz Engine
   + Polars  (restricted)   (scipy/    (Plotly/
   + PyArrow  AST+seccomp    sklearn)   Matplotlib)
       │          │           │           │
       └──────────┴───────────┴───────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│ Evidence & Reproducibility Layer                    │
│  Evidence Graph · Artifact Store · experiment.json  │
│  + reproduce.sh + analysis.ipynb                    │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│ Storage  SQLite (MVP) / Postgres · Local FS         │
│  projects/datasets/analysis_runs/tool_calls/        │
│  artifacts/evidence/insights/reports                 │
└─────────────────────────────────────────────────────┘
 LLM Abstraction: LLMProvider → OpenAI/Anthropic/Google/OpenRouter/Ollama
 Cache: Local File Cache (DatasetProfile/SQL/Python/LLM)  OTel: optional
```

**Why layered:** Separation of Concerns, Dependency Injection (API → Agent → Tool → Engine), testability, MCP adapter can wrap Tool Layer without leaking into domain.

---

## 2. Component Diagram

```
apps/api          → FastAPI app, routers, SSE, DI container
apps/web          → Next.js app router, Dashboard/Projects/Datasets/Analysis/Reports

packages/agent    → LangGraph graph, 4 agents, state, prompts, guardrails
packages/tools    → Tool registry, base Tool class, 20+ tools
packages/execution→ Python Sandbox (AST validator + subprocess jail), SQL validator
packages/statistics → descriptive/correlation/hypo/regression engine + assumption checker
packages/ml       → leakage detector, model selector, trainer, evaluator
packages/visualization → chart recommender + Plotly/Matplotlib generators
packages/evidence → Evidence / Insight / validation, graph builder
packages/reports  → Markdown/HTML/PDF/Notebook builder
packages/datasets → upload, registry, profiling, DuckDB/Polars adapters, hash
packages/mcp      → MCP adapter (stateless, 2026-07-28 spec) wraps Tool Layer

Shared: packages/llm (LLMProvider), packages/cache, packages/observability, packages/security
```

---

## 3. Repository Tree (Monorepo, frozen)

```
data-science-agent/
├── apps/
│   ├── api/                 # FastAPI
│   │   ├── src/dsa_api/{routers,services,models,core}
│   │   └── tests/
│   └── web/                 # Next.js 15
│       ├── app/(dashboard|projects|datasets|analysis|reports|settings)/
│       ├── components/ui/   # shadcn
│       └── lib/
├── packages/
│   ├── agent/               # LangGraph
│   │   ├── prompts/{planner,data_scientist,critic,report}/v1.yaml
│   │   ├── state.py         # AnalysisState
│   │   ├── graph.py         # StateGraph
│   │   └── agents/{planner,scientist,critic,report}.py
│   ├── tools/               # Tool contracts + implementations
│   ├── execution/           # python sandbox + sql validator
│   ├── statistics/          # stats engine
│   ├── ml/                  # ml + leakage
│   ├── visualization/       # viz engine
│   ├── evidence/            # evidence graph
│   ├── reports/             # report generators
│   ├── datasets/            # dataset layer
│   ├── llm/                 # LLMProvider abstraction
│   └── mcp/                 # MCP server (adapter)
├── tests/{unit,integration,e2e,security}/
├── benchmarks/ds-agent-benchmark/  # 20 datasets, 50 tasks
├── examples/{datasets,analyses}/
├── docs/                    # MkDocs
├── scripts/
├── docker/{Dockerfile,compose.yml}
├── .github/workflows/ci.yml
├── pyproject.toml (uv)  package.json  README.md  LICENSE (MIT)
├── CONTRIBUTING.md  SECURITY.md  CODE_OF_CONDUCT.md  THIRD_PARTY_LICENSES.md
└── .commandcode/
```

Tooling: `uv` (dep), `Ruff` (lint/fmt), `MyPy` (strict), `Pytest+coverage`, `pre-commit`, `Docker`

---

## 4. Agent State Machine (LangGraph StateGraph, explicit)

```
START
  ↓
UNDERSTANDING  (Supervisor/Planner parses user_query + dataset profile)
  ↓
PLANNING       (produce AnalysisPlan: objective, assumptions, steps, tools, outputs)
  ↓
DATA_PROFILING (profile_dataset, schema, missing, duplicates, outliers)
  ↓
ANALYSIS       (EDA, correlation, hypothesis_test — Data Scientist)
  ↓
MODELING       (feature eng, train_model, leakage check — optional by task)
  ↓
VALIDATION     (Critic: stats validity, leakage, calc correctness, evidence completeness)
  ├─ FAIL → CorrectionRequest → back to ANALYSIS/MODELING (max 3 retries)
  └─ PASS → SYNTHESIS
  ↓
SYNTHESIS      (Insight engine: Finding+Evidence+Magnitude+Limitation)
  ↓
REPORTING      (Report Agent: Markdown/HTML/PDF + Notebook + experiment.json + reproduce.sh)
  ↓
COMPLETED

ERROR → RECOVERY → RETRY (≤3) → else HUMAN_REVIEW (WAITING_FOR_APPROVAL)
Cost guard: max_tokens / max_steps / max_tool_calls / max_time → STOP
```

V0.1 agents: `Planner`, `Data Scientist`, `Critic`, `Report` (4). Supervisor responsibilities merged into Planner for V0.1; expand to 8 agents in V0.2+.

---

## 5. Database ERD (SQLite MVP)

```
projects (id PK, name, description, created_at)
  1──n datasets (id PK, project_id FK, filename, path, hash, format, rows, cols, metadata JSON, created_at)
  1──n analysis_runs (id PK, project_id FK, dataset_id FK, user_query, objective, status ENUM, plan JSON, current_step, report_id FK, error, budget JSON, created_at)
        1──n agent_steps (id PK, run_id FK, agent, state, input JSON, output JSON, duration_ms, status)
        1──n tool_calls (id PK, run_id FK, step_id FK, tool_name, input JSON, output JSON, status, duration_ms, error)
        1──n artifacts (id PK, run_id FK, type ENUM[dataset,code,sql,table,chart,model,notebook,report,evidence], path, metadata JSON, created_by, created_at)
        1──n evidence (id PK, run_id FK, claim, source_type ENUM[sql,python,statistical_test,model,visualization], source_id FK→tool_calls/artifacts, result JSON, confidence, validation_status)
        1──n insights (id PK, run_id FK, finding, evidence_ids JSON, magnitude, significance, limitation, created_at)
        1──1 reports (id PK, run_id FK, markdown_path, html_path, pdf_path, notebook_path, experiment_json_path, created_at)
  users (future, id PK, email) — not in V0.1 MVP
```

Indexes: `analysis_runs(status)`, `tool_calls(run_id, tool_name)`, `evidence(run_id)`.

---

## 6. Core Domain Models (Pydantic, typed)

```python
class AnalysisStatus(str, Enum): UNDERSTANDING, PLANNING, DATA_PROFILING, ANALYSIS, MODELING, VALIDATION, SYNTHESIS, REPORTING, COMPLETED, FAILED, HUMAN_REVIEW

class AnalysisStep(BaseModel): id: str; name: str; description: str; tool: str; inputs: dict; depends_on: list[str]

class AnalysisPlan(BaseModel): objective: str; assumptions: list[str]; steps: list[AnalysisStep]; required_tools: list[str]; expected_outputs: list[str]

class AnalysisState(BaseModel):
    run_id: str; project_id: str; dataset_id: str
    user_query: str; objective: str
    plan: list[AnalysisStep]; current_step: int
    agent_messages: list[AgentMessage]; tool_calls: list[ToolCall]
    artifacts: list[Artifact]; evidence: list[Evidence]
    validation_results: list[ValidationResult]; insights: list[Insight]
    report_id: str | None; status: AnalysisStatus; error: str | None

class Evidence(BaseModel):
    id: str; claim: str
    source_type: Literal["sql","python","statistical_test","model","visualization"]
    source_id: str; result: dict; confidence: float; validation_status: str  # pending/verified/failed

class Artifact(BaseModel): id: str; type: ArtifactType; path: str; metadata: dict; created_by: str; created_at: datetime

class EvidenceGraph: Insight → Evidence → Computation(ToolCall) → Dataset (traceable)
```

Reproducibility bundle: `experiment.json` = {dataset_hash, schema, python_version, package_versions, llm_provider/model, prompt_version, seed, SQL, code, params, model_config, timestamp}

---

## 7. Tool Contracts (uniform, typed, validated)

```python
class Tool(BaseModel):
    name: str; description: str; input_schema: type[BaseModel]; output_schema: type[BaseModel]
    async def execute(self, input: ToolInput) -> ToolOutput: ...

# Contract guarantees: input validation (Pydantic) → permission check → execution → output validation → evidence emission
```

**V0.1 required tools (≥22):**

| Tool | Input | Output |
|------|-------|--------|
| `profile_dataset` | dataset_id | DatasetProfile (rows/cols/dtypes/missing/duplicates/cardinality/distribution) |
| `inspect_schema` | dataset_id | schema |
| `describe_columns` | dataset_id | stats per column |
| `detect_missing_values` | dataset_id | missing map |
| `detect_duplicates` | dataset_id | dup count/rows |
| `detect_outliers` | dataset_id, method | outliers |
| `run_sql` | sql (read-only, DuckDB) | rows + columns |
| `run_python` | code (sandbox) | stdout/stderr/plots/variables |
| `correlation_analysis` | cols, method[pearson/spearman/kendall] | r, p, CI, interpretation |
| `hypothesis_test` | test[t/welch/mannwhitney/anova/kruskal/chisq/fisher], cols | statistic, p, CI, effect_size, assumptions, interpretation, limitations |
| `regression_analysis` | type[linear/logistic/ridge/lasso/elastic], X, y | coef, metrics, diagnostics |
| `train_model` | task, X,y, candidates, cv | model_id, cv_scores |
| `evaluate_model` | model_id, metrics | Accuracy/Precision/Recall/F1/ROC/PR or MAE/MSE/RMSE/R2 |
| `feature_importance` | model_id | importance + plot |
| `create_chart` | spec → Plotly | chart artifact |
| `save_artifact` | type, content | artifact_id |
| `create_evidence` | claim, source | evidence_id |
| `validate_result` | evidence_id | ValidationResult |
| `generate_report` | run_id | report paths |

All tools: `Typed Input/Output`, `Validation`, `Error Handling`, `Unit Tests`, `Cost/Latency logged`.

---

## 8. Evidence Model & Graph

Every Insight must trace:

```
Insight #003: "East region revenue +27.4% (highest)"
  ├─ Evidence E-014 {claim, source_type=sql, source_id=TC-042, result={East:27.4,South:18.2,North:12.1}, confidence=0.92, validation=verified}
  │    ├─ ToolCall TC-042 run_sql: SELECT region, growth FROM ...
  │    └─ Dataset D-001 sales.csv hash=sha256:...
  ├─ Chart C-007 Revenue Growth by Region (bar)
  └─ Validation V-014 {aggregation verified, missing checked, n=...}
```

Unsupported-claim guard: output guardrail rewrites `causes/impact/effect` → `associated with` unless causal inference evidence exists.

---

## 9. API Specification (FastAPI, /api/v1)

```
POST   /datasets              → upload (multipart, validate size/ext/MIME/traversal) → dataset_id
GET    /datasets/{id}         → profile + metadata
POST   /analysis              → {dataset_id, task} → run_id (creates AnalysisRun, enqueues graph)
GET    /analysis/{id}         → AnalysisState (polling fallback)
GET    /analysis/{id}/events  → SSE: agent_started, agent_completed, tool_started, tool_completed, analysis_progress, validation_started/completed, report_generated
GET    /analysis/{id}/artifacts → list artifacts
GET    /analysis/{id}/report  → markdown/html/pdf/notebook
POST   /analysis/{id}/approve → human-in-the-loop approval
GET    /health  GET /version

Event schema: {event, agent, tool, status, timestamp, duration_ms, run_id}
```

Auth: none in V0.1 (local-first). Storage: `data/projects/{id}/artifacts/...`

---

## 10. Security Boundary

```
Untrusted perimeter: uploaded files + dataset cell text + user task
         ↓
File Security: max_size (100MB MVP), allowlist [csv,parquet,json,xlsx], MIME sniff, filename sanitization, path traversal block, zip bomb check, hash
         ↓
SQL Boundary: SQL Validation → allowlist read-only; deny DROP/DELETE/UPDATE/INSERT/ALTER/ATTACH/COPY; DuckDB read-only connection; row limit
         ↓
Python Boundary: Static AST validation → deny os/subprocess/socket/requests/eval/exec/open(file beyond workdir) → Sandbox (subprocess jail, no net, no env, tmp WorkDir, timeout, mem limit) → capture stdout/stderr/plots only
         ↓
Prompt Injection: all dataset content tagged UNTRUSTED DATA; system prompt instructs to treat as data; input guardrail scans for "ignore previous instructions"
         ↓
Output Guardrail: Unsupported Claim Detection (causal language without causal evidence) + Evidence Coverage check before report
         ↓
Resource Limits: max_tokens, max_steps, max_tool_calls, max_time → STOP with message
Human-in-the-loop: delete/overwrite/unrestricted code/large compute/network → WAITING_FOR_APPROVAL
Logging: JSON structured, no secrets; API keys only env vars
```

---

## 11. Technology Decision Record (TDR)

| Decision | Chosen | Rejected | Why |
|----------|--------|----------|-----|
| Frontend | Next.js 15 + TS + Tailwind + shadcn + Plotly | CRA, Vue | SSR, app router, ecosystem, shadcn quality, Plotly statistical charts |
| Backend | FastAPI + Pydantic v2 + SQLAlchemy | Flask, Django | async, auto OpenAPI, typed, DI, SSE |
| Agent Framework | **LangGraph** | OpenAI Agents SDK (also MIT) | Explicit StateGraph, checkpoints, conditional routing, retry/recovery, long-running — required by spec §8; single framework rule |
| Data Engine | DuckDB + Polars + PyArrow | Pandas-only, Spark | Local analytical SQL, zero-cost, reads CSV/Parquet natively, Arrow interop, avoids loading all into memory |
| DB | SQLite (MVP) → Postgres | MySQL, Redis | Zero-dep local, file cache; Postgres for prod without code change (SQLAlchemy) |
| LLM Abstraction | Custom LLMProvider (async generate/structured_output/stream) | LangChain LLM wrapper | Lightweight, provider-agnostic, supports OpenAI/Anthropic/Google/OpenRouter/Ollama, no lock-in |
| Cache | Local File Cache | Redis Cloud | Free-first, no paid dependency |
| Observability | OTel-compatible interface, optional | Datadog | No SaaS requirement |
| Package Mgr | uv + Ruff + MyPy + Pytest | Poetry + flake8 | Speed, modern, strict typing |
| MCP | Adapter layer over Tool Layer | MCP everywhere | Domain not dependent on MCP; stateless 2026-07-28 spec |

Risks: LangGraph version churn → pin; DuckDB memory on huge files → Polars streaming fallback; LLM cost → budget guards + local Ollama default.

---

## 12. Development Roadmap (Phased, test-gated)

```
Phase 0  Architecture Freeze        ← WE ARE HERE (no business code)
Phase 1  Repository Scaffold        Monorepo, uv, Next.js, FastAPI, SQLite, DuckDB, Polars, Pytest/Ruff/MyPy/Docker/CI → all tests pass
Phase 2  Data Layer                 upload/registry/schema/profiling/DuckDB/Polars/hash → CSV/Parquet/large/malformed tests
Phase 3  Tool Layer                 20+ tools typed+validated+unit-tested
Phase 4  Agent Graph                4 agents via LangGraph, explicit state/transitions/retry/human approval
Phase 5  Evidence System            Evidence/Insight model, graph, traceability, validation
Phase 6  API                        Dataset/Analysis/SSE/Artifact/Report endpoints
Phase 7  Frontend                   Dashboard/Datasets/Analysis workspace/Trace/Charts/Evidence/Reports
Phase 8  Security                   Sandbox, injection defense, file/SQL guards, limits
Phase 9  Benchmark                  DS-Agent-Benchmark 20 datasets/50 tasks/5 categories + metrics
Phase 10 MCP Server                 10+ tools, decoupled adapter
Phase 11 Documentation              README (demo/arch/quickstart/benchmark), MkDocs, examples

Per-phase gate: Implement → Test → Run → Review → Fix → Commit
Quality gates before report: Data → Statistical → Code → Model → Evidence → UnsupportedClaim → Report
Final acceptance: "Analyze why revenue declined and forecast 30 days" + Titanic survival task → full E2E reproducible
```

**What NOT to build in V0.1:** K8s, microservices, cloud deploy, billing, multi-tenancy, mobile, social, custom foundation model, distributed GPU, complex RAG, vector DB, real-time collaboration.

---

### Next Step

> Awaiting **Architecture Confirmation** before proceeding to Phase 1 (Scaffold). No business code will be written until freeze is approved.
