# Related Work — V3 §65

> **Covers §65 required areas** · Each entry: `Title / Authors / Year / URL / Citation / Key Contribution / Relationship to Data Science Agent`.

---

### 1. LLM Data Analysis Agents

| Title | Authors | Year | URL | Citation | Key Contribution | Relationship |
|-------|---------|------|-----|----------|------------------|--------------|
| Data Interpreter | Hong et al. | 2024 | https://arxiv.org/abs/2402.18679 | `Hong et al. ICLR 2024` | LLM agent for data science with code generation + iterative refinement | Closest baseline: also tool-using DS agent; differs in evidence grounding + reproducibility |
| DSBench | Jing et al. | 2024 | https://arxiv.org/abs/2409.07703 | `Jing et al. 2024` | Benchmark for data science agents (Kaggle-style tasks) | Benchmark design reference; V3 v2 (30/100/11) follows similar multi-category framing |
| OpenHands (OpenDevin) | Graham et al. | 2024 | https://github.com/All-Hands-AI/OpenHands | `Graham et al. 2024` | General-purpose code agent with sandboxed execution | Execution sandbox reference (§78) — V3 Python AST vs container |
| AutoGen | Wu et al. | 2023 | https://arxiv.org/abs/2308.08155 | `Wu et al. 2023` | Multi-agent conversation framework | Agent graph alternative; V3 uses LangGraph StateGraph (§49) |

### 2. Agentic Data Science

| Title | Authors | Year | URL | Citation | Key Contribution | Relationship |
|-------|---------|------|-----|----------|------------------|--------------|
| SELA | Liu et al. | 2024 | https://arxiv.org/abs/2409.01019 | `Liu et al. 2024` | Search-based LLM agent for data science | Planner/Critic decomposition vs V3 Planner→Scientist→Critic→Report |

### 3. Tool-Using Agents

| Title | Authors | Year | URL | Citation | Key Contribution | Relationship |
|-------|---------|------|-----|----------|------------------|--------------|
| Toolformer | Schick et al. | 2023 | https://arxiv.org/abs/2302.04761 | `Schick et al. 2023` | LM learns to call tools | Tool contract (§49 Tool Arch, `async execute`) prior art |
| Gorilla | Patil et al. | 2023 | https://arxiv.org/abs/2305.15334 | `Patil et al. 2023` | APIBench for tool calling | `MCP_TOOL_MAP` (17 tools) evaluation framing |

### 4. Data Science Automation

| Title | Authors | Year | URL | Citation | Key Contribution | Relationship |
|-------|---------|------|-----|----------|------------------|--------------|
| DataMole | — | 2023 | https://github.com/... | — | Automated EDA pipelines | Profiling/EDA category prior art |

### 5. Statistical Reasoning with LLMs

| Title | Authors | Year | URL | Citation | Key Contribution | Relationship |
|-------|---------|------|-----|----------|------------------|--------------|
| StatQA | — | 2024 | https://arxiv.org/abs/... | — | LLM statistical reasoning benchmark | Statistical Validity rubric + `S01–S10` (§23) motivation |

### 6. Agent Evaluation

| Title | Authors | Year | URL | Citation | Key Contribution | Relationship |
|-------|---------|------|-----|----------|------------------|--------------|
| AgentBench | Liu et al. | 2023 | https://arxiv.org/abs/2308.03688 | `Liu et al. 2023` | Multi-environment agent evaluation | `EvaluationResultV2` 10×6 + `evaluator_v2` vs single-metric |

### 7. Reproducibility

| Title | Authors | Year | URL | Citation | Key Contribution | Relationship |
|-------|---------|------|-----|----------|------------------|--------------|
| Reproducibility in ML | Pineau et al. | 2021 | https://arxiv.org/abs/2003.12206 | `Pineau et al. 2021` | Reproducibility checklists | `L0–L5` + `ReproductionScore` 6-dim (§21), `experiment.json` manifest (§56) |

### 8. Evidence Grounding

| Title | Authors | Year | URL | Citation | Key Contribution | Relationship |
|-------|---------|------|-----|----------|------------------|--------------|
| Tool-integrated grounding | — | 2023 | — | — | Claim → computation grounding | `Insight→Evidence→ToolCall→Dataset` (§49 Evidence Graph), unsupported-claim guard |

### 9. MCP-based Agent Systems

| Title | Authors | Year | URL | Citation | Key Contribution | Relationship |
|-------|---------|------|-----|----------|------------------|--------------|
| Model Context Protocol (Anthropic) | Anthropic | 2024 | https://modelcontextprotocol.io | `Anthropic 2024` | MCP spec (tools/resources) | Stateless 2026-07-28 adapter (§79), `tools/list` + `tools/call` |

---

## Notes

- This is a **survey seed** for `research/technical-report/` and `research/V3_RESEARCH_REPORT.md` — expand with full citations + PDFs when submitting.
- Synthetic-only benchmark means related-work bias toward code-generation agents; add `human-eval` gap analysis in W7 when citing human baselines.
