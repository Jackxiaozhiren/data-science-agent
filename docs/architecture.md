# Architecture — V3 W10 §48–49

> **Version-controlled source (§49): Mermaid diagrams in this file. System + Agent + Tool + Evidence + Lineage + Evaluation + Reproduction are all derived from live code, not slides.**

---

## 1. System Architecture (§49 Required)

```mermaid
flowchart TB
    U[User / External Evaluator] --> WEB[Frontend<br/>Next.js 15 + TypeScript<br/>13 routes §48]
    U --> API[API Layer<br/>FastAPI + Pydantic v2 + SQLAlchemy<br/>/api/v1/datasets /analysis /artifacts /reports]
    WEB -->|HTTPS + SSE /events| API
    API --> G[Agent Runtime<br/>LangGraph Stateful Graph<br/>Planner → DataScientist → Critic → Report]
    G --> TL[Tool Layer<br/>Typed Tool Contract async execute]
    TL --> DL[Data Layer<br/>DuckDB read-only + Polars + SQLite]
    TL --> EL[Evidence Graph<br/>Insight → Evidence → ToolCall → Dataset hash]
    TL --> RL[Reports & Artifacts<br/>report.md + experiment.json + reproduce.sh + analysis.ipynb]
    G --> OBS[Observability<br/>Trace/Span + Metrics + /metrics + /health /ready]
    EL --> VAL[Validation<br/>insight_evidence / traceability / unsupported_claim / dataset_hash]
    VAL --> RL
    RL --> REP[Reproducibility<br/>artifacts/reports/runId + reproduction/ fresh clone]
    API --> MCP[MCP Adapter<br/>Stateless 2026-07-28<br/>tools/list + tools/call]
    MCP --> TL
    DL --> STORE[(Storage<br/>data/ + artifacts/ + reproduction/<br/>Local-first, Cloud $0 §34)]
```

**Roles**: Frontend (upload, profile, trace) → API (validation, rate limit, logging) → Agent Runtime (stateful graph, checkpoints, retry 3, `max_steps 20 / max_tool_calls 40`) → Tool Layer (17 tools) → Data/Stats/ML/Viz → Evidence → Validation → Reports/Repro. MCP is an adapter over the same Tool Layer, stateless.

---

## 2. Agent Graph (§49 Required)

```mermaid
stateDiagram-v2
    [*] --> understand: user_query + dataset_id
    understand --> plan: Planner heuristics (no LLM required)
    plan --> exec_step: sequential batches (async gather for independent tools)
    exec_step --> exec_step: next tool in plan
    exec_step --> critic: plan exhausted or budget hit
    critic --> report: evidence_coverage + assumption + causal guard
    report --> [*]: artifacts + ValidationResult
    exec_step --> retry: tool error and retries < 3
    retry --> exec_step
    critic --> exec_step: Critic requests re-analysis (bounded)
```

Implementation: `packages/agent/src/dsa_agent/graph.py` (`run_analysis` MVP sequential) + `langgraph_graph.py` (`StateGraph` with `MemorySaver`, `checkpoint` for pause/resume/replay/fork). Budgets enforced in graph. See `docs/agent.md`.

---

## 3. Tool Architecture (§49 Required)

```mermaid
flowchart LR
    subgraph contracts[Typed Tool Contract]
        T[Tool async execute<br/>input schema + output + evidence]
    end
    subgraph data[Data]
        P[profile_dataset]
        Q[query_dataset]
        S[run_sql DuckDB read-only]
        PY[run_python AST sandbox]
    end
    subgraph stats[Statistics]
        C[correlation_analysis]
        H[hypothesis_test]
        R[regression]
        A[assumption_check]
        CC[causal_check]
    end
    subgraph ml[ML]
        TM[train_model]
        EM[evaluate_model]
        FI[feature_importance]
        FC[forecast]
    end
    subgraph viz[Viz]
        CH[create_visualization → PNG]
    end
    subgraph evid[Evidence]
        GE[get_evidence]
        GR[generate_report]
        SA[save_artifact]
    end
    T --> data & stats & ml & viz & evid
    data & stats & ml & viz & evid --> EG[Evidence Nodes<br/>E-xxx per tool_call TC-yyy]
```

All tools registered via `MCP_TOOL_MAP` (`packages/mcp/src/dsa_mcp/adapter.py`) and invoked through `dsa_agent` planner. Added in V3: `external_validation` metrics are evaluation-side, not tools.

---

## 4. Evidence Graph (§49 Required)

```mermaid
flowchart LR
    I[Insight I-xxx<br/>claim + limitation + evidence_ids]
    E[Evidence E-xxx<br/>kind + result + confidence]
    TC[ToolCall TC-xxx<br/>tool + input + output + status]
    DS[Dataset<br/>path + sha256 + rows/hash]
    I -->|supports| E
    E -->|derives_from| TC
    TC -->|reads| DS
    VAL[Validator<br/>insight_evidence / traceability<br/>unsupported_claim / dataset_hash]
    I & E & TC & DS --> VAL
```

Model: `packages/evidence/src/dsa_evidence/models.py` (`EvidenceGraph`). Validation: `validator.py` (`§37` insight→evidence→tool→dataset chain + causal guard). Bundle: `artifacts/reports/<runId>/{report.md, experiment.json, reproduce.sh, analysis.ipynb, evidence_graph.json}`.

---

## 5. Data Lineage (§49 Required)

```mermaid
flowchart TB
    DS[Dataset CSV<br/>benchmarks/v2/datasets or examples/datasets<br/>sha256 + schema]
    DS --> P[Profiler<br/>rows/cols/missing/duplicates/cardinality]
    DS --> DU[DuckDB read-only<br/>SELECT/WITH/SHOW/DESCRIBE/EXPLAIN]
    DS --> SB[Python Sandbox<br/>AST allowlist]
    DU & SB & P --> EV[Evidence + Insights<br/>E-xxx / I-xxx]
    EV --> REP[Report<br/>report.md + chunks]
    REP --> VAL2[Validation<br/>coverage + unsupported]
    VAL2 --> BNDL[Reproducibility Bundle<br/>experiment.json + reproduce.sh + analysis.ipynb]
    BNDL --> REPRO[Fresh clone → uv sync → dsa reproduce<br/>L0–L5 score]
```

Lineage is hashed at `experiment.json` creation (dataset hash + schema + code/SQL/params + python/platform/package_versions + llm/prompt/seed/timestamp) and re-verified by `validator.dataset_hash`. See `repro.py` / `reproducibility.py` L0–L5.

---

## 6. Evaluation Pipeline (§49 Required)

```mermaid
flowchart LR
    CAT[Catalog<br/>benchmarks/v2/catalog.json 0.3.0<br/>100 tasks, 11 cats, seed 42]
    RUN[Runner<br/>dsa_evaluation/runner.py<br/>run_benchmark → _run_one per task]
    MET[Metrics<br/>metrics.py TaskMetrics<br/>task_success / statistical / sql / evidence / unsupported / code]
    STAT[evaluator_v2<br/>statistical_eval.py 10 dims<br/>S01-S10 + causal + uncertainty]
    AGG[Aggregate<br/>by_category / by_difficulty<br/>bootstrap CI / McNemar]
    REL[Reliability §27<br/>4 configs × 7 metrics]
    HUM[Human Eval<br/>11/100, Kappa/Alpha]
    CM[Cross-Model<br/>4 classes + 3 frontiers]
    CAT --> RUN --> MET --> AGG
    MET --> STAT --> AGG
    AGG --> REL & HUM & CM
```

Gates: `dsa --limit 50` (v1, 8 cats) + `dsa --catalog benchmarks/v2/... --limit 100` (v2, 11 cats) both `100%` on live code; `evaluator_v2` attaches `statistical_eval` per task under `details` with `evaluator_version`.

---

## 7. Reproduction Pipeline (§49 Required)

```mermaid
flowchart LR
    DEV[Developer Run<br/>uv sync → dsa --limit 100<br/>out/results.json]
    ARC[Archive<br/>results/ CAPSULE + uv.lock<br/>commit + catalog_sha]
    FRESH[Fresh Environment<br/>fresh clone + fresh install<br/>no private dataset/credential §39]
    CLONE[Fresh Clone<br/>git clone + uv sync]
    INST[Fresh Install<br/>uv sync --dev]
    RUN2[Run Benchmark<br/>dsa --reproduce v2<br/>reproduction/v2 first+second]
    CMP[Compare<br/>Task Success / Statistical / Numerical<br/>Tool Trajectory / Evidence / Report]
    SCO[ReproductionScore<br/>6-dim overall + by_level L0-L5]
    DEV --> ARC --> FRESH --> CLONE --> INST --> RUN2 --> CMP --> SCO
```

Commands: `dsa reproduce --benchmark v2` / `uv run dsa --reproduce v2 --out reproduction/v2`. Output `reproduction/{manifest.json, environment.json, results.json, comparison.json, logs/}` + per-task `L0..L5` via `compare_runs`.

---

## 8. References

- Agent & Architecture: `docs/agent.md` + `docs/architecture.md`
- Benchmark v2: `benchmarks/v2/catalog.json` + `benchmarks/v2/README.md` (+ `docs/benchmark.md`)
- Evidence & Validation: `docs/evidence.md` / `docs/evaluation.md`
- Evaluation & Significance: `docs/evaluation.md` + `packages/evaluation/src/dsa_evaluation/significance.py`
- Reproducibility: `docs/reproducibility.md` + `packages/evidence/src/dsa_evidence/reproducibility.py`
- Security: `docs/security.md` + `SECURITY.md`
