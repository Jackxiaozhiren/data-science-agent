# Data Science Agent V3.0

## Research Validation, External Reproducibility & Open-Source Release

---

# 0. PROJECT STATUS

## Project

**Data Science Agent**

## Positioning

> **An Evidence-Grounded Autonomous Data Science System**

## Core Slogan

> **From Natural Language to Reproducible Data Science.**

---

## Current Release

```text
Version: v2.0.0
Git Tag: v2.0.0
```

---

## V2.0 Verified Status

当前项目已经完成 V2.0 的 10 个 Workstream。

### Engineering Gates

```text
pytest:
136 passed

mypy:
87 clean

coverage:
80%

ruff:
All checks passed

npm build:
13/13 routes

docker compose:
valid

dsa:
50/50 @ 1.0

dsa v2:
100/100 @ 1.0

Benchmark:
30 datasets
100 tasks
11 categories
seed=42

Security:
23 cases

MCP:
2026-07-28
stateless

Research:
RQs
ablation A-F
real benchmark integration
V2 paper draft
```

---

## Existing V2.0 Capabilities

当前系统已经具备：

```text
Agent Runtime
LangGraph
Planner
Data Scientist
Critic
Report Agent

Data Layer
DuckDB
Polars
SQLite

Tool Layer
Data Tools
SQL Tools
Python Tools
Statistics Tools
ML Tools
Visualization Tools

Evidence
Insight
Evidence Trace
Tool Trace
Dataset Lineage
Reproducibility Package

Evaluation
EvaluationResultV2
10 dimensions
6 evaluation levels
Significance testing

Benchmark
30 datasets
100 tasks
11 categories

Reliability
Trajectory
Checkpoint
Retry
Recovery
Failure Taxonomy F01-F15

Observability
Trace
Span
Metrics

Security
File validation
SQL validation
Python sandbox
Prompt guard
HITL
23 security tests

MCP
17 tools
Stateless implementation
2026-07-28 compatibility
ADR-001

Research
Research Questions
A-F Ablation
Real benchmark integration
Paper draft

Frontend
13 routes

Documentation
README
MkDocs
CHANGELOG
```

---

# 1. V3.0 CORE OBJECTIVE

V3.0 **不是功能扩展版本**。

V3.0 的定位：

> **Research Validation + External Reproducibility + Open-Source Release**

V2.0 解决的是：

> "系统是否完整？"

V3.0 要解决的是：

> **"这个系统是否真实可靠、可验证、可复现、可研究、可被第三方独立使用与评价？"**

---

# 2. V3.0 NORTH STAR

第三方开发者或研究人员在完全不了解项目内部实现的情况下，应该能够：

```text
Clone Repository
        ↓
Install
        ↓
Run Demo
        ↓
Run Benchmark
        ↓
Inspect Agent Trajectory
        ↓
Inspect Evidence
        ↓
Replay Analysis
        ↓
Reproduce Results
        ↓
Reproduce Research Figures
        ↓
Evaluate Claims
```

最终目标：

> **任何重要结论都可以从最终报告向下追溯到 Evidence、Tool、Computation 和 Dataset。**

---

# 3. V3.0 DESIGN PHILOSOPHY

优先级：

```text
Scientific Validity
>
Reproducibility
>
Statistical Rigor
>
Evaluation Integrity
>
Security
>
External Usability
>
Open-Source Quality
>
Performance
>
UI Polish
```

---

# 4. NON-GOALS

V3.0 暂时不以以下内容为主要目标：

```text
Another Chatbot Feature
Another Random Agent
Another Large Tool Set
Another Dashboard
Another Vector Database
Another Cloud Infrastructure
Billing System
Payment System
Enterprise Multi-Tenancy
Mobile App
Custom Foundation Model
Distributed GPU Training
Large-scale RAG System
```

如果一个需求不能明显提升：

```text
Reliability
Research Validity
Reproducibility
Security
Open-Source Adoption
External Usability
```

则不应进入 V3.0 核心范围。

---

# 5. ARCHITECTURE FREEZE

V2.0 架构视为稳定基线。

默认不得重写：

```text
LangGraph Agent Runtime
FastAPI
Next.js
DuckDB
Polars
SQLite
Evidence Graph
Python Sandbox
MCP Adapter
Evaluation Framework
```

只有以下情况允许修改：

```text
Critical Security Issue
Critical Correctness Issue
Fundamental Protocol Incompatibility
Reproducibility Blocker
Major Maintainability Failure
```

所有架构变化必须通过 ADR。

---

# 6. ARCHITECTURAL CHANGE PROTOCOL

任何架构变化必须先创建：

```text
docs/ADR/ADR-XXX-*.md
```

必须包含：

```text
Problem
Evidence
Impact
Alternatives
Recommendation
Migration Plan
Rollback Plan
```

没有 ADR，不允许进行重大架构改变。

---

# 7. V3.0 WORKSTREAMS

V3.0 共分为 12 个 Workstream：

```text
W1  Baseline Revalidation
W2  Benchmark Scientific Audit
W3  Independent Reproduction
W4  Statistical Evaluation Upgrade
W5  Agent Reliability Research
W6  Cross-Model Evaluation
W7  Human Evaluation
W8  External User Validation
W9  Open-Source Release Engineering
W10 Documentation & Research Packaging
W11 Publication & Citation Infrastructure
W12 V3 Release & Post-Release Monitoring
```

---

# W1 — BASELINE REVALIDATION

## 8. Objective

在开发 V3.0 任何功能之前，重新验证 V2.0。

历史记录不能直接作为当前证据。

---

## 9. Required Baseline Commands

必须实际执行：

```bash
pytest -q
mypy .
ruff check packages apps/api tests
npm run build
docker compose config
dsa --limit 50
dsa v2 --limit 100
```

同时执行：

```text
Security Suite
MCP Conformance Suite
Reproducibility Suite
Research / Ablation Suite
```

---

## 10. Baseline Metadata

记录：

```text
Git Commit
Git Tag
Python Version
Node Version
OS
Dependency Lock
LLM Configuration
Benchmark Configuration
Seed
Dataset Hashes
Prompt Versions
Tool Versions
Coverage
Runtime
Memory
Token Usage
```

---

## 11. Baseline Report

创建：

```text
docs/v3/V2_FINAL_BASELINE.md
```

包含：

```text
1. Repository State
2. Git Commit
3. Release Tag
4. Functional Status
5. Test Status
6. Coverage
7. Benchmark Status
8. Evaluation Status
9. Security Status
10. MCP Status
11. Reproducibility Status
12. Research Status
13. Technical Debt
14. Remaining Polish
15. V3 Priorities
```

---

# W2 — BENCHMARK SCIENTIFIC AUDIT

当前 Benchmark：

```text
30 datasets
100 tasks
11 categories
seed=42
```

V3.0 初期不要急于扩大 Benchmark。

先证明 Benchmark 本身可信。

---

## 12. Benchmark Audit Questions

逐项检查：

```text
Are tasks independent?

Are gold answers correct?

Are expected methods statistically defensible?

Are alternative valid methods supported?

Could benchmark tasks leak implementation details?

Are datasets representative?

Are task patterns duplicated?

Are some tasks trivial?

Are some tasks underspecified?

Does the benchmark reward superficial pattern matching?
```

---

## 13. Task Metadata

每个任务必须包含：

```text
task_id
dataset_id
question
difficulty
gold_method
gold_result
expected_tools
required_evidence
forbidden_claims
evaluation_function
source
license
citation
benchmark_version
```

---

## 14. Benchmark Ownership

每个任务应记录：

```text
benchmark_generator
human_reviewer
statistical_reviewer
```

---

## 15. Difficulty Classification

统一：

```text
Easy
Medium
Hard
Expert
```

Difficulty 不仅由步骤数量决定，还应考虑：

```text
Statistical Ambiguity
Data Quality
Tool Selection Complexity
Multi-Step Reasoning
Evidence Requirements
Interpretation Risk
```

---

## 16. Gold Standard

每项任务定义：

```text
acceptable_method
acceptable_metrics
acceptable_interpretation
acceptable_evidence
forbidden_interpretation
```

允许多个科学上合理的解决方式。

禁止：

> 评测器只承认一种正确统计方法。

---

# W3 — INDEPENDENT REPRODUCTION

V3.0 最重要的工作流之一。

---

## 17. Reproduction System

建立：

```text
reproduction/
```

完整流程：

```text
Developer Run
      ↓
Archive
      ↓
Fresh Environment
      ↓
Fresh Clone
      ↓
Fresh Install
      ↓
Run Benchmark
      ↓
Compare Results
```

---

## 18. Reproduction Commands

实现：

```bash
dsa reproduce --run <run_id>
```

以及：

```bash
dsa reproduce --benchmark v2
```

输出：

```text
reproduction/
├── manifest.json
├── environment.json
├── results.json
├── comparison.json
└── logs/
```

---

## 19. Reproduction Comparison

比较：

```text
Task Success
Statistical Results
Numerical Metrics
Tool Trajectory
Evidence Graph
Artifacts
Report Structure
```

不要求自然语言文本完全一致。

---

## 20. Reproduction Classes

定义：

```text
Exact Reproduction
Numerical Reproduction
Semantic Reproduction
Analytical Reproduction
```

---

## 21. Reproduction Score

实现：

```python
class ReproductionScore:
    execution: float
    numerical: float
    statistical: float
    evidence: float
    semantic: float
    overall: float
```

必须记录评分方法。

---

# W4 — STATISTICAL EVALUATION UPGRADE

Data Science Agent 的核心特色之一是：

> **Statistical Rigor**

因此统计正确性必须成为第一类研究指标。

---

## 22. Statistical Evaluation Dimensions

必须独立评估：

```text
Method Selection
Assumption Validation
Test Execution
Parameter Estimation
P-value Correctness
Confidence Interval Correctness
Effect Size
Interpretation
Uncertainty Communication
Causal Language
```

---

## 23. Statistical Error Taxonomy

建立：

```text
S01 Wrong Test
S02 Missing Assumption Check
S03 Incorrect Statistic
S04 Incorrect P-value
S05 Incorrect Confidence Interval
S06 Incorrect Effect Size
S07 Multiple Testing Error
S08 Misinterpretation
S09 Causal Overclaim
S10 Uncertainty Omission
```

---

## 24. Causal Language Audit

检查：

```text
causes
caused by
leads to
impact
effect
drives
results in
```

如果只有 observational correlation evidence：

必须警告。

错误：

```text
Price causes revenue to increase.
```

正确：

```text
Price is positively associated with revenue in this dataset.
```

---

## 25. Uncertainty Evaluation

评估是否合理报告：

```text
Confidence Interval
Forecast Interval
Model Uncertainty
Sampling Uncertainty
Limitations
```

---

# W5 — AGENT RELIABILITY RESEARCH

V2 已经具备：

```text
Trajectory
Critic
Failure Taxonomy
Observability
```

V3 必须将它们变成正式实验。

---

## 26. Reliability Comparison

至少比较：

```text
Single Agent

Planner + Agent

Planner + Agent + Critic

Full Evidence-Grounded Agent
```

---

## 27. Reliability Metrics

比较：

```text
Task Success
Statistical Correctness
Unsupported Claim Rate
Evidence Coverage
Tool Efficiency
Recovery Success
Reproducibility
```

---

## 28. Critic Effectiveness

统计：

```text
Errors Detected
Errors Corrected
False Positive Warnings
False Negative Errors
Correction Success
Additional Latency
Additional Token Cost
```

同时计算：

```text
Critic Benefit
=
Quality Improvement
/
Additional Cost
```

---

## 29. Tool Selection Quality

记录：

```text
Correct Tool
Unnecessary Tool
Wrong Tool
Missing Required Tool
```

生成：

```text
Tool Selection Accuracy
```

---

## 30. Agent Loop Quality

检测：

```text
Duplicate Tool Calls
Oscillation
Repeated Failures
Unnecessary Retries
Premature Termination
Over-analysis
```

生成：

```text
Agent Efficiency Score
```

---

# W6 — CROSS-MODEL EVALUATION

项目必须保持 Provider-agnostic。

不要把任何单一模型视为系统"真值"。

---

## 31. Model Evaluation Categories

根据实际可用环境测试：

```text
Local Small Model
Local Medium Model
Open API Model
Frontier Model
```

禁止虚构模型实验。

---

## 32. Model Evaluation Matrix

对每个模型记录：

```text
Task Success
Statistical Accuracy
Evidence Coverage
Unsupported Claim Rate
Tool Selection Accuracy
Latency
Token Usage
Cost
Failure Rate
```

---

## 33. Quality-Cost Frontier

生成：

```text
Quality vs Cost
Quality vs Latency
Quality vs Token Usage
```

不要只给出：

> "Model X 是最好的。"

而应展示 trade-off。

---

## 34. Local-First Validation

至少一个完整 Benchmark 必须支持：

```text
Local LLM
+
Local Data Engine
+
Local Storage
```

且不依赖付费云服务。

---

# W7 — HUMAN EVALUATION

自动评测不能成为唯一证据。

---

## 35. Human Evaluation

建立：

```text
human-eval/
```

抽取 Benchmark 的：

```text
5%–10%
```

作为人工审核样本。

---

## 36. Human Review Rubric

评估：

```text
Correctness
Clarity
Statistical Validity
Evidence Quality
Interpretation
Uncertainty
Actionability
Report Quality
```

使用：

```text
1 = unacceptable
2 = poor
3 = acceptable
4 = strong
5 = excellent
```

---

## 37. Reviewer Guide

创建：

```text
docs/v3/HUMAN_EVALUATION_GUIDE.md
```

评测依据：

```text
Task
Dataset
Gold Criteria
Evidence
Tool Outputs
```

---

## 38. Inter-Rater Reliability

如果多位 reviewer 评价相同任务：

适当采用：

```text
Cohen's Kappa
Krippendorff's Alpha
```

并报告：

```text
Agreement
Sample Size
Confidence Interval
```

---

# W8 — EXTERNAL USER VALIDATION

V3 必须建立真正面向外部用户的安装流程。

---

## 39. Clean Install

目标：

```text
git clone
↓
install
↓
run
```

不需要：

```text
Developer-only Paths
Private Dataset
Private Credentials
Internal Environment
```

---

## 40. One-Command Demo

提供：

```bash
dsa demo
```

完整执行：

```text
Demo Dataset
↓
Analysis
↓
Evidence
↓
Report
```

---

## 41. Fresh Machine Testing

至少测试：

```text
Linux
macOS
```

Windows 若不支持必须明确文档说明。

---

## 42. Installation Metrics

记录：

```text
Cold Install Time
First Launch Time
Demo Execution Time
Benchmark Setup Time
```

---

# W9 — OPEN-SOURCE RELEASE ENGINEERING

V3 必须达到成熟开源项目的标准。

---

## 43. Repository Audit

检查：

```text
README.md
LICENSE
SECURITY.md
CONTRIBUTING.md
CODE_OF_CONDUCT.md
CHANGELOG.md
ROADMAP.md
CITATION.cff
```

---

## 44. README Structure

README 第一屏应回答：

```text
What is Data Science Agent?

Why does it exist?

Why is it different?

How do I run it?

How is it evaluated?

How is it reproducible?
```

建议目录：

```text
What is Data Science Agent?
Architecture
Quick Start
Demo
Evidence Trace
Benchmark
Research
Reproducibility
MCP
Security
Roadmap
Contributing
```

---

## 45. Quantitative Claim Policy

所有数字必须可以追溯到：

```text
Benchmark
Version
Commit
Methodology
Report
```

避免无证据使用：

```text
State-of-the-art
Best
Most reliable
Enterprise-grade
Production-ready
```

---

## 46. Demo Package

建立：

```text
demo/
├── datasets/
├── questions/
├── runs/
├── reports/
├── evidence/
├── screenshots/
└── README.md
```

---

## 47. One-Command Demo Requirement

```bash
dsa demo
```

必须在 clean installation 中运行。

---

# W10 — DOCUMENTATION & RESEARCH PACKAGING

---

## 48. Documentation Structure

建议：

```text
docs/
├── getting-started.md
├── architecture.md
├── agent-system.md
├── evidence.md
├── evaluation.md
├── benchmark.md
├── reproducibility.md
├── security.md
├── mcp.md
├── research.md
└── contributing.md
```

---

## 49. Required Architecture Diagrams

必须包含：

```text
System Architecture
Agent Graph
Tool Architecture
Evidence Graph
Data Lineage
Evaluation Pipeline
Reproduction Pipeline
```

建议使用：

```text
Mermaid
```

或其他可版本控制的源文件。

---

## 50. Benchmark Documentation

必须记录：

```text
Dataset Sources
Dataset Licenses
Task Generation
Task Validation
Gold Standards
Metrics
Scoring
Limitations
Seed
Hardware
Software Environment
```

---

## 51. Research Report

创建：

```text
research/V3_RESEARCH_REPORT.md
```

结构：

```text
Abstract
Introduction
Research Questions
System Architecture
Evaluation Methodology
Benchmark
Experimental Setup
Results
Ablation Study
Failure Analysis
Human Evaluation
Reproducibility
Limitations
Conclusion
```

---

# W11 — PUBLICATION & CITATION INFRASTRUCTURE

---

## 52. Citation

创建：

```text
CITATION.cff
```

并建立：

```text
research/technical-report/
```

---

## 53. Paper Versioning

维护：

```text
V3.0 Research Report
V3.1 Revision
```

每项研究结果必须关联：

```text
Git Commit
Benchmark Version
Dataset Version
Experiment Configuration
```

---

## 54. Figure Reproducibility

所有重要研究图表必须拥有生成脚本。

目录建议：

```text
research/
├── figures/
└── scripts/
```

禁止人工修改最终研究图表后不保留生成路径。

---

## 55. Table Reproducibility

每个研究表格必须由：

```text
Raw Experiment Result
↓
Analysis Script
↓
Generated Table
```

生成。

---

## 56. Experiment Manifest

每次实验必须生成：

```json
{
  "experiment_id": "...",
  "git_commit": "...",
  "benchmark_version": "...",
  "dataset_version": "...",
  "model": "...",
  "prompt_version": "...",
  "seed": 42,
  "timestamp": "...",
  "configuration": {}
}
```

---

## 57. Research Commands

提供：

```bash
dsa research run --experiment <id>
```

以及：

```bash
dsa research reproduce --experiment <id>
```

---

# W12 — V3 RELEASE

---

## 58. Target Version

```text
v3.0.0
```

---

## 59. V3 Release Gates

全部必须通过：

```text
pytest
mypy
ruff
npm build
docker validation
security suite
MCP conformance
benchmark v2
reproduction suite
research experiments
external install test
documentation build
```

---

## 60. Benchmark Release Gate

必须满足：

```text
No unexplained regression
Gold standards reviewed
Evaluation scripts versioned
Results reproducible
Confidence intervals generated where appropriate
Failure analysis available
```

---

## 61. Research Release Gate

必须满足：

```text
All reported experiments executed
No fabricated results
All figures reproducible
All tables reproducible
All claims traceable to data
Limitations documented
```

---

## 62. Open-Source Release Gate

必须满足：

```text
Fresh clone works
Fresh installation works
Demo works
Documentation works
License works
Security policy works
Contribution guide works
Citation file exists
```

---

# 63. RELEASE VERIFICATION COMMAND

实现：

```bash
dsa verify-release v3.0.0
```

输出：

```text
Release Verification Report
```

每一项状态必须是：

```text
PASS
FAIL
NOT VERIFIED
```

---

# 64. RESEARCH QUALITY STANDARD

最终研究结果必须支持：

```text
Claim
+
Metric
+
Experimental Setup
+
Uncertainty
+
Limitations
```

禁止没有实验支持的表述：

```text
Our system is significantly better.
```

除非确实执行了相应统计检验。

---

# 65. RELATED WORK REVIEW

创建：

```text
research/related-work.md
```

至少覆盖：

```text
LLM Data Analysis Agents
Agentic Data Science
Tool-Using Agents
Data Science Automation
Statistical Reasoning with LLMs
Agent Evaluation
Reproducibility
Evidence Grounding
MCP-based Agent Systems
```

每篇文献记录：

```text
Title
Authors
Year
URL
Citation
Key Contribution
Relationship to Data Science Agent
```

---

# 66. CLAIM-EVIDENCE MATRIX

创建：

```text
research/claim-evidence-matrix.md
```

格式：

| Claim | Evidence | Experiment | Metric | Source | Confidence | Limitation |
| ----- | -------- | ---------- | ------ | ------ | ---------- | ---------- |

所有重要研究结论必须映射到证据。

---

# 67. FAILURE CASE STUDY

选择至少：

```text
10 representative failures
```

每个 Failure：

```text
Task
Initial Agent Behavior
Failure
Failure Category
Why It Happened
Critic Detection
Recovery
Final Outcome
Lesson
```

---

# 68. SUCCESS CASE STUDY

选择至少：

```text
10 representative successful analyses
```

展示：

```text
Question
Plan
Tool Trajectory
Evidence
Validation
Final Result
```

---

# 69. EVIDENCE TRACE SHOWCASE

建立至少一个完整 Demo：

```text
Claim
↓
Evidence
↓
SQL / Python
↓
Result
↓
Chart
↓
Dataset
```

该 Demo 应成为：

> **Data Science Agent 的旗舰案例。**

---

# 70. REPRODUCTION SHOWCASE

建立一个完整案例：

```text
Run A
↓
Archive
↓
Fresh Environment
↓
Run B
↓
Comparison
```

展示：

```text
What Matched
What Differed
Why
Reproduction Score
```

---

# 71. BENCHMARK SHOWCASE

从 Benchmark 中选择：

```text
10 canonical tasks
```

用于 README / Documentation。

展示：

```text
Task
System
Score
Evidence
Failure / Success
```

---

# 72. BENCHMARK VERSIONING

禁止静默修改 Benchmark。

版本：

```text
v2.0
v2.1
v3.0
```

所有结果必须标记 Benchmark Version。

---

# 73. EVALUATION VERSIONING

评测逻辑也必须版本化：

```text
evaluator_v1
evaluator_v2
```

不同 Evaluator 的结果不能直接比较而不注明版本。

---

# 74. RESULT IMMUTABILITY

已经发布的研究结果不得静默修改。

结构：

```text
release/
└── v3.0/
    ├── results/
    ├── figures/
    └── tables/
```

如果发现错误：

```text
v3.0.1
```

而不是直接覆盖历史结果。

---

# 75. COST REPORTING

每次 Benchmark 至少记录：

```text
Token Usage
Estimated API Cost
Runtime
CPU Usage
Memory Usage
```

对于 Local Mode：

```text
Cloud API Cost = $0
```

注意不要将"免费"解释为没有任何硬件和电力成本。

---

# 76. PERFORMANCE REPORTING

记录：

```text
Cold Start
Warm Start
Analysis Duration
Tool Latency
LLM Latency
Report Generation Time
Benchmark Throughput
```

适当使用：

```text
Median
P95
```

不要只使用平均值。

---

# 77. RESOURCE LIMITS

文档明确：

```text
Max Dataset Size
Max Analysis Time
Max Python Runtime
Max Memory
Max Output Size
Max Agent Steps
Max Tool Calls
```

---

# 78. SECURITY DISCLOSURE

完善：

```text
SECURITY.md
```

包括：

```text
Supported Versions
Vulnerability Reporting
Sandbox Model
Known Limitations
Out-of-Scope Threats
```

---

# 79. MCP FINAL AUDIT

MCP 实现必须按照当前正式规范进行最终审计。

重点检查：

```text
Stateless Protocol Core
Tool Discovery
Tool Schemas
Tool Calls
Error Handling
Authorization
Cache Hints
Tasks
```

不得依赖旧式：

```text
Mcp-Session-Id
```

作为协议核心状态。

---

# 80. MCP COMPATIBILITY MATRIX

创建：

```text
docs/v3/MCP_COMPATIBILITY.md
```

至少包含：

| Feature             | Status | Test | Specification Reference | Notes |
| ------------------- | ------ | ---- | ----------------------- | ----- |
| Protocol Version    |        |      |                         |       |
| tools/list          |        |      |                         |       |
| tools/call          |        |      |                         |       |
| Stateless Operation |        |      |                         |       |
| Authorization       |        |      |                         |       |
| Error Handling      |        |      |                         |       |
| Tasks               |        |      |                         |       |
| Cache Hints         |        |      |                         |       |

---

# 81. USER EXPERIENCE AUDIT

模拟完全陌生用户完成：

```text
Install
↓
Upload Dataset
↓
Ask Question
↓
Inspect Evidence
↓
Generate Report
↓
Replay
↓
Benchmark
```

记录所有 friction points。

---

# 82. UX DEFECT TAXONOMY

使用：

```text
U01 Installation
U02 Configuration
U03 Dataset Upload
U04 Analysis
U05 Evidence
U06 Report
U07 Replay
U08 Benchmark
U09 Documentation
```

---

# 83. CONTRIBUTOR EXPERIENCE

新贡献者必须能够：

```text
Clone
↓
Setup
↓
Run Tests
↓
Run Demo
↓
Make Small Change
↓
Run CI Locally
↓
Submit PR
```

---

# 84. CONTRIBUTOR FILES

确认存在：

```text
CONTRIBUTING.md

CODE_OF_CONDUCT.md

.github/ISSUE_TEMPLATE/

.github/PULL_REQUEST_TEMPLATE.md
```

Issue 类型建议：

```text
bug
feature
benchmark
research
```

---

# 85. FUTURE V4 SCOPE

V3 不实施，只记录：

```text
Plugin Ecosystem
Community Benchmark Leaderboard
Third-party Tool Registry
Jupyter Extension
VS Code Extension
MCP Apps UI
Cloud Deployment
Team Collaboration
```

---

# 86. V3 RESEARCH NARRATIVE

最终研究叙事：

> We design and evaluate an evidence-grounded autonomous data science agent that combines tool execution, statistical validation, critic-based verification, evidence tracing, and reproducibility mechanisms.

不要直接宣称 novelty。

需要通过 Related Work 验证。

---

# 87. V3 SUCCESS DEFINITION

当以下所有问题的答案都是 "YES" 时，V3 才算真正完成：

```text
Can a stranger install it?

Can a stranger run the demo?

Can a stranger run the benchmark?

Can a stranger inspect the evidence?

Can a stranger replay an analysis?

Can a stranger reproduce a result?

Can a stranger inspect the Agent trajectory?

Can a stranger understand failure cases?

Can a stranger reproduce research figures?

Can a stranger identify the exact Git commit?

Can a stranger identify the exact benchmark version?

Can a stranger identify the exact evaluator version?

Can a stranger evaluate the project's major claims independently?
```

---

# 88. FINAL V3 CONCEPTUAL ARCHITECTURE

```text
                       USER
                         │
                         ▼
                  ┌────────────┐
                  │  Frontend  │
                  └─────┬──────┘
                        │
                        ▼
                  ┌────────────┐
                  │    API     │
                  └─────┬──────┘
                        │
                        ▼
                ┌───────────────┐
                │ Agent Runtime │
                └───────┬───────┘
                        │
            ┌───────────┼────────────┐
            ▼           ▼            ▼
         Planner     Scientist     Critic
            │           │            │
            └───────────┼────────────┘
                        │
                        ▼
                    Tool Layer
                        │
         ┌──────────────┼──────────────┐
         ▼              ▼              ▼
       DuckDB        Python         Statistics
                     Sandbox
         │              │               │
         └──────────────┼───────────────┘
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
                     Report
                        │
          ┌─────────────┴─────────────┐
          ▼                           ▼
     Reproducibility             Evaluation
          │                           │
          └─────────────┬─────────────┘
                        ▼
                     Research
                        │
                        ▼
               External Validation
                        │
                        ▼
                Open-Source Release
```

Cross-cutting：

```text
Security
Observability
MCP
Versioning
Benchmark
Telemetry
```

---

# 89. V3 DEVELOPMENT ORDER

严格按以下顺序：

```text
Phase A
V2 Freeze & Revalidation

↓

Phase B
Benchmark Scientific Audit

↓

Phase C
Independent Reproduction

↓

Phase D
Statistical Evaluation Upgrade

↓

Phase E
Agent Reliability Research

↓

Phase F
Cross-Model Evaluation

↓

Phase G
Human Evaluation

↓

Phase H
External User Validation

↓

Phase I
Open-Source Release Engineering

↓

Phase J
Documentation & Research Packaging

↓

Phase K
Publication / Citation Layer

↓

Phase L
V3 Release
```

---

# 90. PHASE EXECUTION RULE

每个 Phase 必须：

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

完成后：

```text
STOP
```

不得自动进入下一阶段。

---

# 91. CHANGE CONTROL

所有重要改动必须说明：

```text
Why
Impact
Risk
Tests
Benchmark Impact
Security Impact
Research Impact
```

---

# 92. NO FABRICATED RESULTS

绝对禁止虚构：

```text
Benchmark Score
Accuracy
Latency
Token Cost
P-value
Confidence Interval
Research Result
Human Evaluation
Reproduction Result
Security Result
```

未执行：

```text
NOT RUN
```

无法验证：

```text
NOT VERIFIED
```

发现回归：

```text
REGRESSION DETECTED
```

必须如实报告。

---

# 93. FINAL ENGINEERING PRINCIPLE

V3 的目标不是：

> "让项目拥有更多代码。"

而是：

```text
Correct
Reliable
Secure
Reproducible
Statistically Rigorous
Evidence-Grounded
Maintainable
Open-Source
Research-Ready
```

---

# 94. FINAL RESEARCH PRINCIPLE

项目最终要从：

> "We built an AI data science agent."

升级为：

> "We built an evidence-grounded autonomous data science system, developed a rigorous evaluation framework, measured statistical correctness and reliability, studied failure modes, demonstrated reproducibility, and released the complete system, benchmark, evaluation suite, and research artifacts as open source."

---

# 95. FIRST EXECUTION

第一次执行本文件时：

## ONLY EXECUTE PHASE A

即：

> **V2.0 Freeze & Revalidation**

不得直接进入 Benchmark Audit。

---

# 96. PHASE A — FIRST ACTIONS

首先阅读：

```text
DATA_SCIENCE_AGENT_V0_1.md
DATA_SCIENCE_AGENT.md
DATA_SCIENCE_AGENT_V2_0.md
AGENTS.md
docs/DEVELOPMENT_STATUS.md
```

然后检查：

```text
Repository
Agent Graph
Evaluation Framework
Benchmark Framework
Research Package
MCP Implementation
Security Suite
Reproduction System
Frontend
Documentation
```

---

# 97. PHASE A — REQUIRED VERIFICATION

实际执行：

```bash
pytest -q
mypy .
ruff check packages apps/api tests
npm run build
docker compose config
dsa --limit 50
dsa v2 --limit 100
```

同时执行：

```text
Security Tests
MCP Conformance
Reproduction Suite
Ablation Suite
```

---

# 98. PHASE A — BASELINE REPORT

创建：

```text
docs/v3/V2_FINAL_BASELINE.md
```

必须包含：

```text
1. Repository State
2. Current Commit
3. Current Tag
4. Functional Status
5. Test Status
6. Coverage
7. Benchmark Status
8. Evaluation Status
9. Security Status
10. MCP Status
11. Reproducibility Status
12. Research Status
13. Technical Debt
14. Remaining Polish
15. V3 Priority Recommendations
```

---

# 99. PHASE A — STOP CONDITION

Phase A 完成后：

不要：

```text
implement Benchmark Audit
modify Agent Graph
modify MCP
modify Evidence
modify Frontend
modify research metrics
add dependencies
```

只输出：

```text
V2.0 BASELINE VERIFIED
```

并汇报：

```text
Current Status
Regressions
Technical Debt
V3 Risks
Recommended Workstream Order
```

然后停止。

---

# 100. FINAL V3 NORTH STAR

最终标准：

> **A reviewer should be able to clone the repository, install the system, run a benchmark, inspect an agent trajectory, trace every analytical claim to executable evidence, replay an analysis from a checkpoint, reproduce research results, and independently evaluate whether the system actually works.**

这才是 Data Science Agent 从：

```text
Good AI Project
```

升级到：

```text
Serious Research + Open-Source System
```

的标准。