# Data Science Agent V2.0

## Research-Grade Evaluation, Reliability, Reproducibility & Production Hardening

---

# 0. IMPORTANT CONTEXT

项目：

> **Data Science Agent**

核心定位：

> **An Evidence-Grounded Autonomous Data Science System**

当前项目已经完成：

* `DATA_SCIENCE_AGENT_V0_1.md`：92 章详细权威规范
* `DATA_SCIENCE_AGENT.md`：精简版规范
* Phase 0–11 全部完成
* V1.0–V1.8 全部完成
* CI 已通过
* pytest 已通过
* mypy clean
* ruff gated
* Docker Compose 配置有效
* Web 7/7 routes build successful
* CLI benchmark `50/50`
* MCP 17 tools
* SSE
* Evidence trace
* Python sandbox
* SQL read-only protection
* Prompt injection guard
* HITL
* Notebook generation
* Report generation
* Cache
* Parallel execution
* `/health`
* `/metrics`
* MkDocs documentation
* Git tags `v0.1.0 ... v1.8.0`

**这些现有成果必须视为当前稳定基线，不得破坏。**

---

# 1. V2.0 OBJECTIVE

V2.0 的目标不是继续增加大量普通功能。

V2.0 的核心任务：

> **把 Data Science Agent 从一个"功能完整的 AI 数据分析系统"提升为一个"可被科学评估、可复现、可审计、可比较、可扩展、具备研究价值的 Agent System"。**

核心升级方向：

```text
V1.8
   ↓
Evaluation
   ↓
Reliability
   ↓
Reproducibility
   ↓
Scientific Benchmark
   ↓
Agent Observability
   ↓
Failure Analysis
   ↓
Production Hardening
   ↓
MCP Modernization
   ↓
Research Package
```

---

# 2. NON-NEGOTIABLE RULE

这是一个：

> **HARDENING + RESEARCH PHASE**

不是重写阶段。

禁止：

```text
rewrite architecture
rewrite frontend
rewrite backend
replace LangGraph
replace DuckDB
replace Polars
replace FastAPI
replace SQLite
replace existing Agent Graph
```

除非发现：

* Critical security vulnerability
* Critical correctness flaw
* Fundamental architectural incompatibility
* MCP protocol incompatibility
* Irreproducibility issue

如果需要架构改变：

必须先创建 ADR：

```text
docs/ADR/ADR-XXX-*.md
```

包含：

```text
Problem
Evidence
Impact
Alternatives
Recommendation
Migration Plan
Rollback Plan
```

然后才能实施。

---

# 3. BASELINE FREEZE

在开始任何开发之前：

## 3.1 Verify current baseline

实际执行：

```bash
pytest -q
mypy .
ruff check .
npm run build
docker compose config
dsa --limit 50
```

并记录：

```text
baseline test result
baseline coverage
baseline benchmark
baseline latency
baseline build status
baseline dependency lock
```

创建：

```text
docs/v2/Baseline Report.md
```

---

# 4. DO NOT TRUST PREVIOUS CLAIMS

即使项目说明中写：

```text
50/50 @ 1.0
coverage 75%
mypy clean
```

也必须重新验证。

不要引用历史结果作为当前结果。

规则：

> **No metric is valid until reproduced in the current working tree.**

---

# 5. V2.0 DEVELOPMENT PRINCIPLE

核心优先级：

```text
Correctness
>
Statistical Rigor
>
Evaluation Quality
>
Security
>
Reproducibility
>
Observability
>
Maintainability
>
Performance
>
UI
```

---

# 6. MAJOR WORKSTREAMS

V2.0 分为 10 个工作流：

```text
W1  Baseline & Regression Freeze
W2  Evaluation Framework
W3  Scientific Benchmark
W4  Agent Reliability
W5  Reproducibility & Replay
W6  Failure Analysis
W7  Observability & Telemetry
W8  MCP 2026-07-28 Alignment
W9  Production Security Hardening
W10 Research Package & Publication Layer
```

---

# 7. W1 — BASELINE & REGRESSION FREEZE

目标：

建立：

> **V1.8 → V2.0 Regression Contract**

创建：

```text
benchmarks/baseline/
tests/regression/
docs/v2/baseline/
```

必须记录：

```text
functional correctness
API correctness
tool correctness
agent trajectory
benchmark result
latency
memory
token usage
artifact generation
reproducibility
security checks
```

---

# 8. REGRESSION TEST MATRIX

建立：

```text
Regression Matrix
```

至少覆盖：

### Data

```text
CSV
Parquet
JSON
Excel
100MB boundary
Malformed input
Unicode
Missing values
Duplicate rows
High cardinality
```

### Analysis

```text
EDA
Correlation
Hypothesis Test
Regression
Classification
Clustering
Forecasting
Visualization
```

### Agent

```text
Planner
Data Scientist
Critic
Report
Retry
Recovery
HITL
Checkpoint
```

### Output

```text
Report
Notebook
Evidence
Artifacts
Metrics
```

---

# 9. W2 — EVALUATION FRAMEWORK

建立正式：

# Data Science Agent Evaluation Framework

不要继续使用单一：

```text
50/50
```

作为唯一指标。

必须至少区分：

```text
Task Success
Statistical Correctness
Tool Correctness
Evidence Grounding
Code Correctness
SQL Correctness
Report Correctness
Reproducibility
Safety
Efficiency
```

---

# 10. EVALUATION MODEL

定义：

```python
class EvaluationResult:
    task_id: str
    run_id: str

    task_success: float
    statistical_correctness: float
    tool_correctness: float
    evidence_coverage: float
    unsupported_claim_rate: float
    code_execution_rate: float
    sql_correctness: float
    reproducibility_score: float
    safety_score: float

    latency_ms: float
    token_cost: float
```

所有评测结果必须保存。

---

# 11. HARD METRICS

至少实现：

## Task Success Rate

```text
successful_tasks / total_tasks
```

## Statistical Accuracy

衡量：

```text
correct test
correct statistic
correct p-value
correct interpretation
```

## Evidence Coverage

定义：

```text
supported claims / total claims
```

## Unsupported Claim Rate

定义：

```text
unsupported claims / total claims
```

这是核心指标。

---

# 12. EVIDENCE COVERAGE

每一条最终 Insight：

必须拥有：

```text
Evidence ID
Tool Call ID
Artifact ID
Dataset ID
```

如果缺少：

```text
Evidence Coverage = 0
```

不要因为文字"看起来合理"而给予满分。

---

# 13. STATISTICAL CORRECTNESS

定义统计评估器：

```text
correct_method
correct_assumptions
correct_statistic
correct_p_value
correct_effect_size
correct_interpretation
```

例如一个问题：

> "Group A 和 Group B 的平均收入是否存在显著差异？"

Gold Standard：

```text
Welch t-test
```

Agent 使用：

```text
ordinary t-test
```

如果方差不齐：

统计正确性不能判为满分。

---

# 14. W3 — SCIENTIFIC BENCHMARK

把现在的：

```text
20 datasets
50 tasks
```

升级成：

# DS-Agent-Benchmark v2

推荐规模：

```text
30+ datasets
100+ tasks
8+ analytical categories
```

---

# 15. BENCHMARK CATEGORIES

必须包含：

```text
1. Data Profiling

2. EDA

3. Statistical Testing

4. Regression

5. Classification

6. Clustering

7. Time Series

8. Data Quality

9. Visualization

10. Evidence Validation
```

---

# 16. TASK DIFFICULTY

每个 Benchmark 添加：

```text
difficulty:
easy
medium
hard
expert
```

例如：

```text
EASY:
mean / median / distribution

MEDIUM:
hypothesis testing

HARD:
confounding / leakage / model selection

EXPERT:
multi-step analytical reasoning
```

---

# 17. GOLD STANDARD

每个任务必须有：

```json
{
  "task_id": "...",
  "dataset": "...",
  "question": "...",
  "expected_task_type": "...",
  "required_tools": [],
  "gold_method": "...",
  "gold_metrics": {},
  "required_evidence": [],
  "forbidden_claims": [],
  "difficulty": "hard"
}
```

---

# 18. MULTI-LEVEL EVALUATION

每个任务必须分别评估：

```text
Level 1
Tool Execution

Level 2
Numerical Correctness

Level 3
Statistical Method

Level 4
Interpretation

Level 5
Evidence

Level 6
Final Report
```

这样可以定位：

> Agent 到底错在哪里。

---

# 19. W4 — AGENT RELIABILITY

重点从：

> "能不能完成任务"

升级到：

> **"为什么完成 / 为什么失败？"**

建立：

# Agent Reliability Layer

记录：

```text
agent trajectory
node transitions
tool calls
tool failures
retry
critic findings
correction
final outcome
```

---

# 20. TRAJECTORY MODEL

定义：

```python
class AgentTrajectory:
    run_id: str
    nodes: list[NodeExecution]
    tool_calls: list[ToolExecution]
    retries: list[RetryEvent]
    interruptions: list[InterruptEvent]
    checkpoints: list[Checkpoint]
    final_state: dict
```

---

# 21. TRAJECTORY EVALUATION

不要只评估 final answer。

同时评估：

```text
Did the agent select correct tool?

Did it use unnecessary tools?

Did it retry intelligently?

Did it validate?

Did Critic catch errors?

Did it stop when evidence was insufficient?
```

LangGraph 官方当前的测试与评测文档也明确区分 deterministic tests、integration tests 和 trajectory-based evaluations，因此这一层应该成为项目的标准能力，而不是一次性的测试脚本。

---

# 22. TOOL EFFICIENCY SCORE

定义：

```text
necessary_tool_calls
/
actual_tool_calls
```

目标：

减少：

```text
tool thrashing
duplicate queries
redundant computation
unnecessary model calls
```

---

# 23. RETRY QUALITY

不能仅统计：

```text
retry_count
```

还要评估：

```text
retry_success_rate
```

并区分：

```text
useful_retry
pointless_retry
repeated_same_error
```

---

# 24. CRITIC EFFECTIVENESS

建立对照：

```text
Without Critic
vs
With Critic
```

指标：

```text
error detection rate
false positive rate
correction success rate
final task success rate
```

这是未来论文非常重要的一组实验。

---

# 25. W5 — REPRODUCIBILITY & REPLAY

目前已经有：

```text
repro package
checkpoint
```

V2.0 要把它提升成正式：

# Reproducibility Engine

---

# 26. REPRODUCIBILITY LEVELS

定义：

```text
L0:
same request

L1:
same code

L2:
same data

L3:
same environment

L4:
same tool trajectory

L5:
same analytical conclusion
```

---

# 27. REPRODUCIBILITY SCORE

执行：

```text
Original Run
↓
Create Reproduction Package
↓
Fresh Run
↓
Compare
```

比较：

```text
numeric outputs
statistics
model metrics
charts
claims
evidence
```

输出：

```text
Reproducibility Score
```

---

# 28. LANGGRAPH CHECKPOINT / REPLAY

继续强化 checkpoint。

必须实现：

```text
pause
resume
replay
fork
inspect
```

允许：

```text
Run A
    ↓
Checkpoint 12
    ├── Replay A
    └── Fork B
```

LangGraph 的 persistence/checkpoint 机制目前已经支持恢复、time travel、fork 和 fault-tolerant execution，因此不要重新造一个平行的 checkpoint 系统；应优先把现有 checkpoint 能力与 AnalysisRun / Evidence / Repro Package 对齐。

---

# 29. REPLAY POLICY

明确区分：

```text
exact replay
semantic replay
approximate replay
```

必须记录：

```text
LLM model
LLM parameters
seed
prompt version
tool version
dataset hash
environment
```

---

# 30. W6 — FAILURE ANALYSIS

建立：

# Failure Taxonomy

错误至少分为：

```text
F01 Data Understanding Error
F02 Tool Selection Error
F03 SQL Error
F04 Python Error
F05 Statistical Method Error
F06 Numerical Error
F07 Model Error
F08 Interpretation Error
F09 Unsupported Claim
F10 Evidence Missing
F11 Security Error
F12 Reproducibility Error
F13 Agent Loop Error
F14 Prompt Injection
F15 Resource Budget Error
```

---

# 31. FAILURE LOG

每次失败：

必须记录：

```json
{
  "run_id": "...",
  "failure_code": "F08",
  "agent": "data_scientist",
  "node": "analysis",
  "tool": "hypothesis_test",
  "severity": "medium",
  "recoverable": true,
  "recovery_attempts": 2,
  "resolved": true
}
```

---

# 32. FAILURE DASHBOARD

前端新增：

```text
Failure Analysis
```

展示：

```text
Top Failure Categories

Failure Rate

Recovery Rate

Agent with Most Errors

Tool with Most Errors

Average Retries

Unsupported Claim Rate
```

---

# 33. W7 — OBSERVABILITY

建立真正的：

# Agent Observability Layer

不要只记录普通日志。

必须支持：

```text
Trace
Span
Event
Metric
Artifact
Evidence
```

---

# 34. TRACE MODEL

一个 AnalysisRun：

```text
Trace
│
├── Planner Span
│   ├── LLM Call
│   └── Plan
│
├── Data Scientist Span
│   ├── Tool Call
│   ├── SQL
│   └── Result
│
├── Critic Span
│   └── Validation
│
└── Report Span
```

---

# 35. METRICS

新增：

```text
agent_run_total

agent_run_success_total

agent_run_failure_total

agent_run_duration_seconds

tool_call_total

tool_error_total

tool_retry_total

unsupported_claim_total

evidence_missing_total

critic_correction_total

benchmark_score

reproducibility_score
```

---

# 36. LATENCY BREAKDOWN

不要只记录：

```text
total latency
```

必须记录：

```text
planning latency
LLM latency
tool latency
SQL latency
Python latency
statistics latency
ML latency
critic latency
report latency
```

这样才能研究：

> Agent 为什么慢？

---

# 37. TOKEN EFFICIENCY

记录：

```text
input_tokens
output_tokens
total_tokens
```

以及：

```text
tokens_per_successful_task
tokens_per_insight
tokens_per_analysis
```

目标不是单纯：

> 越少越好

而是：

> **quality / token cost**

---

# 38. COST-EFFECTIVENESS METRIC

建立：

```text
Efficiency Score
=
Task Success
/
Token Cost
```

同时提供：

```text
Quality-Cost Frontier
```

---

# 39. W8 — MCP MODERNIZATION

现有 MCP 必须检查：

> 是否严格对齐 MCP 2026-07-28？

2026-07-28 规范已经正式取消协议层 initialize/initialized handshake 和 `Mcp-Session-Id`，采用 stateless protocol core；Tools list 也支持 cache hints，Tasks 已成为扩展机制。

---

# 40. MCP AUDIT

检查：

```text
protocol version
transport
headers
tool schema
tool discovery
authorization
state handling
task handling
error handling
deprecated features
```

---

# 41. MCP STATE MODEL

如果应用需要状态：

禁止依赖：

```text
Mcp-Session-Id
```

应该使用：

```text
analysis_id
project_id
task_id
run_id
```

作为显式 application-level handle。

---

# 42. MCP TOOLS

继续支持已有：

```text
17 tools
```

但每个 Tool 必须拥有：

```text
name
description
inputSchema
outputSchema
permissions
idempotency
timeout
cost_class
```

---

# 43. MCP TOOL CLASSIFICATION

工具分为：

```text
SAFE_READ
ANALYSIS
COMPUTE
WRITE_ARTIFACT
DESTRUCTIVE
```

例如：

```text
profile_dataset
→ SAFE_READ

run_sql
→ ANALYSIS

run_python
→ COMPUTE

generate_report
→ WRITE_ARTIFACT
```

危险工具必须 HITL。

---

# 44. MCP CONFORMANCE TEST

建立：

```text
tests/mcp/conformance/
```

至少覆盖：

```text
tool discovery
tools/list
tools/call
invalid schema
invalid params
timeouts
errors
authorization
stateless calls
repeated calls
tool caching
```

目标：

> `MCP 2026-07-28 compatible`

---

# 45. W9 — SECURITY HARDENING

在现有安全基础上进行：

# Adversarial Security Testing

---

# 46. PROMPT INJECTION SUITE

至少加入：

```text
Direct Prompt Injection

Indirect Prompt Injection

Dataset Injection

CSV Cell Injection

Markdown Injection

Formula Injection

Tool Description Injection

Report Injection
```

---

# 47. TOOL ABUSE TESTING

尝试：

```text
unauthorized filesystem access

shell escape

network access

resource exhaustion

SQL injection

path traversal

symlink escape

malicious archive

oversized payload
```

---

# 48. SANDBOX RESOURCE LIMITS

Python Sandbox 增加：

```text
max CPU time
max memory
max output size
max file size
max process count
max execution time
```

---

# 49. DENIAL-OF-SERVICE RESISTANCE

测试：

```text
huge CSV
huge JSON
deeply nested JSON
very wide table
high-cardinality categorical data
expensive joins
pathological regex
long-running Python
```

必须确保：

```text
bounded
cancelable
recoverable
```

---

# 50. REPORT SECURITY

防止：

```text
HTML injection
JavaScript injection
formula injection
malicious markdown
unsafe embedded image
```

---

# 51. W10 — RESEARCH PACKAGE

建立：

```text
research/
```

结构：

```text
research/
├── questions/
├── datasets/
├── benchmark/
├── experiments/
├── results/
├── figures/
├── tables/
├── reports/
└── paper/
```

---

# 52. RESEARCH QUESTION 1

验证：

> Does tool augmentation improve statistical correctness?

比较：

```text
LLM-only
vs
LLM + Tools
```

---

# 53. RESEARCH QUESTION 2

验证：

> Does Critic verification reduce unsupported claims?

比较：

```text
without critic
vs
with critic
```

---

# 54. RESEARCH QUESTION 3

验证：

> Does Evidence Graph improve analytical traceability?

指标：

```text
evidence coverage
unsupported claim rate
reproducibility
```

---

# 55. RESEARCH QUESTION 4

验证：

> Does explicit statistical validation improve the reliability of autonomous data science?

比较：

```text
LLM analysis
vs
statistics-aware agent
```

---

# 56. RESEARCH QUESTION 5

验证：

> How does model choice affect autonomous data science reliability?

比较：

```text
local model
small API model
frontier model
```

只允许在实际可用环境下进行。

禁止虚构模型实验结果。

---

# 57. ABLATION MATRIX

至少实现：

```text
A = LLM only

B = LLM + Tools

C = LLM + Tools + Planner

D = LLM + Tools + Planner + Critic

E = LLM + Tools + Planner + Critic + Evidence

F = Full System
```

比较：

```text
Task Success
Statistical Accuracy
Evidence Coverage
Unsupported Claims
Reproducibility
Latency
Token Cost
```

---

# 58. SIGNIFICANCE TESTING

对于 Benchmark 比较：

不要仅展示：

```text
92%
vs
87%
```

尽量提供：

```text
confidence intervals
paired comparison
bootstrap CI
effect size
```

如果适用：

```text
McNemar
Wilcoxon signed-rank
paired bootstrap
```

避免把 benchmark task 当作完全独立的 iid observations。

---

# 59. RESULT STORAGE

所有实验结果保存：

```text
research/results/
```

格式：

```text
JSON
CSV
Parquet
```

每次实验拥有：

```text
experiment_id
git_commit
dataset_version
prompt_version
model
configuration
seed
timestamp
metrics
```

---

# 60. NO FABRICATED RESULTS

绝对禁止：

```text
fake benchmark
fake accuracy
fake p-value
fake latency
fake research result
fake chart
fake comparison
```

任何未运行实验：

```text
NOT RUN
```

任何缺失结果：

```text
N/A
```

---

# 61. PAPER GENERATION

准备：

```text
research/paper/
```

至少自动生成：

```text
Abstract

Introduction

Related Work

System Architecture

Methodology

Benchmark

Experimental Setup

Results

Ablation Study

Failure Analysis

Limitations

Conclusion
```

---

# 62. LIMITATIONS

必须主动记录：

```text
LLM stochasticity

Model dependence

Benchmark leakage

Dataset bias

Evaluation bias

Tool selection bias

Cost constraints

Local model capability limitations
```

不要为了宣传项目而隐藏限制。

---

# 63. DEMO / SHOWCASE

V2.0 必须增加一个完整 Showcase：

```text
Demo 1:
EDA

Demo 2:
Statistical Testing

Demo 3:
ML

Demo 4:
Time Series

Demo 5:
Evidence Trace

Demo 6:
Failure Recovery

Demo 7:
Reproduction
```

每个 Demo：

```text
Input
↓
Agent Trace
↓
Tool
↓
Evidence
↓
Result
↓
Report
```

---

# 64. FRONTEND V2

新增页面：

```text
/benchmarks

/evaluations

/runs

/runs/[id]/replay

/failures

/research

/mcp
```

Dashboard 新增：

```text
Task Success

Statistical Accuracy

Evidence Coverage

Unsupported Claim Rate

Reproducibility

Average Latency

Token Efficiency
```

---

# 65. ANALYSIS RUN INSPECTOR

每次 Run 提供：

```text
Overview

Timeline

Agent Graph

Tool Calls

Evidence

Artifacts

Checkpoints

Failures

Validation

Reproduction
```

---

# 66. REPLAY UI

用户选择：

```text
Checkpoint #12
```

然后：

```text
Replay
```

或者：

```text
Fork
```

生成：

```text
Run #124
Run #124-Fork-A
```

用于分析 Agent trajectory differences。

---

# 67. BENCHMARK UI

提供：

```text
Benchmark Leaderboard
```

列：

```text
System
Task Success
Statistical Accuracy
Evidence Coverage
Reproducibility
Latency
Token Cost
```

---

# 68. RESEARCH DASHBOARD

显示：

```text
Ablation Results

Confidence Intervals

Failure Distribution

Error Categories

Tool Usage

Critic Effectiveness

Reproducibility
```

---

# 69. DEPENDENCY POLICY

V2.0 不允许无计划增加依赖。

每个新增依赖必须说明：

```text
Purpose

License

Size

Security

Maintenance

Alternative

Why needed
```

更新：

```text
THIRD_PARTY_LICENSES.md
```

---

# 70. VERSIONING

V2.0 开发过程中采用：

```text
v2.0.0-alpha.1
v2.0.0-alpha.2
...
v2.0.0-beta.1
...
v2.0.0
```

禁止：

```text
v2.0.0
```

在所有测试完成之前发布。

---

# 71. GIT DISCIPLINE

每个 Workstream：

```text
feature branch
↓
tests
↓
review
↓
merge
```

Commit 必须清晰：

```text
feat:
fix:
test:
refactor:
docs:
security:
benchmark:
research:
```

---

# 72. RELEASE GATE

V2.0 Release 必须满足：

```text
pytest PASS

mypy PASS

ruff PASS

npm build PASS

docker compose config PASS

MCP conformance PASS

security suite PASS

benchmark PASS

reproduction suite PASS

documentation PASS
```

---

# 73. BENCHMARK RELEASE GATE

不要强制：

```text
100/100
```

作为唯一目标。

真正要求：

```text
No regression relative to V1.8
```

以及：

```text
Benchmark confidence interval available
Failure categories available
Trajectory data available
```

---

# 74. COVERAGE

当前覆盖率：

```text
74–75%
```

V2.0 目标：

```text
>= 80%
```

但：

> 不允许为了覆盖率写无意义测试。

尤其加强：

```text
security
agent graph
evidence
statistics
replay
MCP
```

---

# 75. PERFORMANCE

当前：

```text
73ms → 39.8ms
```

不要盲目继续压缩 latency。

优先：

```text
reliability
quality
predictability
```

如果优化性能：

必须同时记录：

```text
before
after
workload
hardware
benchmark method
```

---

# 76. TOKEN OPTIMIZATION

建立：

```text
Prompt Cache

Context Compression

Tool Result Summarization

Repeated Tool Call Detection

State Compaction
```

但：

> 不允许因为减少 Token 而损失统计证据。

---

# 77. CONTEXT MANAGEMENT

对长任务：

```text
raw tool result
↓
structured summary
↓
evidence reference
```

不要把整个 DataFrame 原样注入 LLM context。

---

# 78. LARGE DATA STRATEGY

对于大于：

```text
100MB
```

的数据：

优先：

```text
DuckDB
Polars
Sampling
Aggregation
Column Projection
Predicate Pushdown
```

禁止：

```text
blindly load entire dataset into prompt
```

---

# 79. DATASET HASHING

每个 Dataset：

```text
sha256
```

并保存：

```text
dataset_hash
size
schema_hash
row_count
column_count
```

用于：

```text
reproducibility
benchmark
cache
artifact lineage
```

---

# 80. ARTIFACT LINEAGE

建立：

```text
Dataset
  ↓
Transformation
  ↓
Tool Result
  ↓
Visualization
  ↓
Evidence
  ↓
Insight
  ↓
Report
```

用户必须能够追溯：

> 这个结论来自哪里？

---

# 81. DATA LINEAGE MODEL

至少包含：

```python
class LineageNode:
    id: str
    type: str
    parent_ids: list[str]
    metadata: dict
```

---

# 82. AGENT VERSIONING

记录：

```text
agent_version
prompt_version
tool_version
graph_version
```

不能只记录：

```text
model=gpt-x
```

---

# 83. PROMPT VERSIONING

每个 Prompt：

```text
planner@v1.2
scientist@v2.0
critic@v1.5
report@v1.1
```

任何 benchmark result：

必须记录 prompt version。

---

# 84. MODEL VERSIONING

每次运行：

```text
provider
model
model_revision
temperature
top_p
max_tokens
```

尽可能记录。

---

# 85. CACHE CORRECTNESS

Cache 不允许导致 stale analytical conclusions。

Cache key 至少考虑：

```text
dataset_hash
query
tool_version
parameters
model_version
prompt_version
```

---

# 86. DETERMINISM MODE

增加：

```text
DSA_DETERMINISTIC=true
```

尽可能固定：

```text
seed
temperature
tool order
dataset snapshot
model parameters
```

明确标记：

```text
deterministic
non-deterministic
```

---

# 87. GOLDEN FILE TESTS

为重要任务生成：

```text
golden/
```

保存：

```text
expected SQL
expected statistics
expected evidence
expected report sections
```

LLM 文本不做严格 byte-to-byte comparison。

重点比较：

```text
structured outputs
metrics
claims
evidence
```

---

# 88. SEMANTIC EVAL

使用：

```text
deterministic evaluator
+
LLM judge
```

但 LLM Judge 不得成为唯一评价标准。

至少：

```text
50% deterministic / executable checks
```

尽可能避免：

```text
LLM says it looks good
```

成为唯一成绩。

---

# 89. LLM JUDGE POLICY

LLM judge 输入：

```text
task
gold criteria
agent answer
evidence
tool results
```

输出结构：

```json
{
  "score": 0.0,
  "criteria": {},
  "errors": [],
  "justification": "..."
}
```

必须记录 judge model/version。

---

# 90. HUMAN REVIEW

随机抽取：

```text
5–10%
```

Benchmark 任务进行人工审核。

特别审核：

```text
expert tasks
statistical claims
causal language
failure cases
```

---

# 91. INTER-RATER AGREEMENT

如果人工审核超过两人：

尽可能计算：

```text
Cohen's Kappa
```

或：

```text
Krippendorff's Alpha
```

用于评估：

```text
reviewer consistency
```

---

# 92. RESEARCH QUALITY BAR

最终研究结果必须支持：

```text
claim
+
metric
+
uncertainty
+
experimental setup
+
limitations
```

不要写：

```text
Our system is significantly better.
```

除非存在：

```text
statistical evidence
```

---

# 93. V2.0 DOCUMENTATION

新增：

```text
docs/v2/
├── evaluation.md
├── benchmark.md
├── reliability.md
├── reproducibility.md
├── failure-analysis.md
├── observability.md
├── mcp-2026.md
├── security.md
├── research.md
└── release.md
```

---

# 94. README UPDATE

README 第一屏增加：

```text
Research Grade

Benchmark

Evidence Grounding

Reproducibility

MCP

Security
```

展示真实指标。

禁止夸大。

---

# 95. PROJECT BADGES

可以考虑：

```text
CI
Coverage
License
Python
Docker
MCP
Benchmark
```

但不要使用虚假的：

```text
Production Ready
Enterprise Grade
State of the Art
```

除非有证据支持。

---

# 96. FINAL V2.0 ARCHITECTURE

目标：

```text
                 USER
                   │
                   ▼
          ┌─────────────────┐
          │     Frontend    │
          └────────┬────────┘
                   │
                   ▼
          ┌─────────────────┐
          │      API        │
          └────────┬────────┘
                   │
                   ▼
          ┌─────────────────┐
          │   LangGraph     │
          │ Agent Runtime   │
          └────────┬────────┘
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
     Planner   Scientist    Critic
        │          │          │
        └──────────┼──────────┘
                   ▼
               Tool Layer
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
      DuckDB    Python      Statistics
        │        Sandbox        │
        └──────────┼────────────┘
                   ▼
                  ML
                   │
                   ▼
             Visualization
                   │
                   ▼
             Evidence Graph
                   │
                   ▼
              Validation
                   │
                   ▼
                Report
                   │
          ┌────────┴────────┐
          ▼                 ▼
      Reproduce          Benchmark
          │                 │
          └────────┬────────┘
                   ▼
              Research
```

旁路系统：

```text
Observability
Security
MCP
Evaluation
Telemetry
```

---

# 97. V2.0 CORE RESEARCH LOOP

最终实现：

```text
Run
 ↓
Observe
 ↓
Evaluate
 ↓
Detect Failure
 ↓
Correct
 ↓
Replay
 ↓
Compare
 ↓
Learn
```

注意：

这里的 "Learn" 不表示自动修改模型参数。

表示：

```text
prompt improvement
tool improvement
graph improvement
policy improvement
```

所有改动必须通过 Benchmark。

---

# 98. NO SELF-MODIFYING AGENT

V2.0 禁止：

```text
Agent automatically rewrites itself
```

允许：

```text
Agent proposes improvement
↓
Human approval
↓
Git change
↓
Benchmark
↓
Merge
```

---

# 99. FINAL ACCEPTANCE SCENARIO

执行：

```text
Analyze why revenue declined and forecast the next 30 days.
```

系统必须：

```text
1. Create AnalysisRun

2. Create checkpoint

3. Generate plan

4. Profile data

5. Select tools

6. Execute analysis

7. Generate evidence

8. Critic validation

9. Correct errors if needed

10. Generate visualization

11. Generate forecast

12. Calculate metrics

13. Generate report

14. Generate notebook

15. Generate reproduction package

16. Save lineage

17. Save trajectory

18. Save evaluation result

19. Allow replay

20. Allow fork

21. Expose MCP-compatible operations where applicable
```

---

# 100. V2.0 FINAL ACCEPTANCE CRITERIA

必须满足：

```text
✓ No regression from V1.8

✓ Baseline reproducible

✓ Evaluation framework operational

✓ Benchmark v2 operational

✓ Failure taxonomy operational

✓ Trajectory evaluation operational

✓ Reproducibility score operational

✓ Replay operational

✓ Evidence coverage measurable

✓ Unsupported claim rate measurable

✓ Critic effectiveness measurable

✓ Token efficiency measurable

✓ Security adversarial suite operational

✓ MCP 2026-07-28 compatibility audited

✓ MCP conformance tests pass

✓ Research experiment runner operational

✓ Results reproducible from Git commit

✓ Documentation complete
```

---

# 101. FINAL DELIVERABLES

最终必须产生：

```text
docs/v2/

benchmarks/v2/

research/

tests/evals/

tests/security/

tests/mcp/

reports/

figures/

results/
```

以及：

```text
V2_BASELINE.md

V2_EVALUATION.md

V2_BENCHMARK.md

V2_RESEARCH_REPORT.md

V2_SECURITY_REPORT.md

V2_MCP_COMPATIBILITY.md
```

---

# 102. DEVELOPMENT ORDER

严格按照：

```text
Phase A
Baseline Freeze
        ↓
Phase B
Evaluation Framework
        ↓
Phase C
Benchmark v2
        ↓
Phase D
Reliability
        ↓
Phase E
Reproducibility
        ↓
Phase F
Failure Analysis
        ↓
Phase G
Observability
        ↓
Phase H
MCP Modernization
        ↓
Phase I
Security Hardening
        ↓
Phase J
Research Package
        ↓
Phase K
V2 Release
```

---

# 103. PHASE EXECUTION RULE

不要一次实现所有 Phase。

每阶段：

```text
Inspect
↓
Plan
↓
Implement
↓
Test
↓
Benchmark
↓
Review
↓
Document
↓
Commit
```

完成后才允许进入下一阶段。

---

# 104. FIRST TASK

当前只执行：

# PHASE A — BASELINE FREEZE

不要实现任何新功能。

首先：

```text
1. Inspect repository

2. Read DATA_SCIENCE_AGENT_V0_1.md

3. Read DATA_SCIENCE_AGENT.md

4. Read existing docs

5. Read existing tests

6. Read benchmark implementation

7. Read MCP implementation

8. Read Agent Graph

9. Read Evidence system

10. Read current security implementation
```

然后重新执行：

```bash
pytest -q
mypy .
ruff check .
npm run build
docker compose config
dsa --limit 50
```

---

# 105. BASELINE REPORT

创建：

```text
docs/v2/Baseline Report.md
```

内容：

```text
1. Current Architecture

2. Current Functional Scope

3. Current Test Results

4. Current Coverage

5. Current Benchmark Results

6. Current MCP Status

7. Current Security Status

8. Current Performance

9. Current Dependency Status

10. Known Technical Debt

11. Regression Risks

12. V2 Priority Recommendations
```

---

# 106. STOP CONDITION

Phase A 完成后：

不要实现 Evaluation Framework。

不要修改业务逻辑。

不要修改 Agent Graph。

不要修改 MCP。

只输出：

```text
BASELINE VERIFIED

Current Status

Regressions

Technical Debt

V2 Risks

Recommended Workstream Order
```

然后停止。

---

# 107. IMPORTANT

如果实际测试结果与你提供的历史结果不同：

以实际结果为准。

如果：

```text
50/50
```

变成：

```text
48/50
```

不要修饰。

报告：

```text
REGRESSION DETECTED
```

如果：

```text
coverage 75%
```

变成：

```text
72%
```

报告真实值。

如果某项无法验证：

```text
NOT VERIFIED
```

禁止猜测。

---

# 108. FINAL ENGINEERING PRINCIPLE

本阶段不是为了让项目"看起来更大"。

而是为了让项目具备：

```text
Scientific Validity
Engineering Reliability
Operational Observability
Reproducibility
Open-Source Credibility
```

最终目标：

> **A reviewer should be able to clone the repository, reproduce the benchmark, inspect an agent trajectory, trace every analytical claim to executable evidence, replay the analysis from a checkpoint, and independently evaluate whether the system actually works.**

这才是 Data Science Agent 从：

```text
Good AI Project
```

升级到：

```text
Serious Research + Open-Source System
```

的标准。

---

# 109. START NOW

只执行：

> **PHASE A — BASELINE FREEZE**

不要越级。

不要实现新功能。

不要修改架构。

先重新验证整个 V1.8 基线，并生成：

```text
docs/v2/Baseline Report.md
```

完成后停止，等待下一阶段指令。