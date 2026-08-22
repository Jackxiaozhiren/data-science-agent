# Data Science Agent V4.0

## Open-Source Ecosystem, Developer Platform & Productization

---

# 0. PROJECT STATUS

## Project

**Data Science Agent**

## Positioning

> **An Evidence-Grounded Autonomous Data Science Platform**

## Core Slogan

> **From Natural Language to Reproducible Data Science.**

---

# 1. CURRENT RELEASE

```text
Current Version:
v3.0.0

Git Tag:
v3.0.0

Release Commit:
9ea647f
```

---

# 2. V3.0 VERIFIED BASELINE

V3.0 已完成 12 个 Workstream。

## Engineering

```text
pytest:
155 passed

mypy:
94 clean

ruff:
All checks passed

coverage:
81%

Statements:
4597

npm:
13/13 routes

docker:
valid
```

## Benchmark

```text
dsa:
50/50 @ 1.00

dsa v2:
100/100 @ 1.00

Datasets:
30

Tasks:
100

Categories:
11

Seed:
42
```

## Research

```text
Benchmark Audit
Independent Reproduction
Statistical Evaluation
Reliability Research
Cross-Model Evaluation
Human Evaluation
External Validation
Research Report
Claim-Evidence Matrix
Related Work
Ablation A-F
```

## Security

```text
23 security cases
```

## MCP

```text
MCP 2026-07-28
Stateless
17 tools
```

## Release

```text
README
ROADMAP
CITATION
SECURITY
CHANGELOG
MkDocs
Research Package
Demo
External Validation
Release Verification
```

---

# 3. V4.0 CORE OBJECTIVE

V4.0 不再以：

```text
Feature Count
Agent Count
Tool Count
Lines of Code
```

作为主要成功指标。

V4.0 的核心目标：

> **Transform Data Science Agent from a mature research artifact into a usable open-source developer platform and extensible ecosystem.**

核心转变：

```text
V3.0
Research Artifact
      ↓
V4.0
Developer Platform
      ↓
Open Source Ecosystem
      ↓
Real Users
      ↓
Real Integrations
      ↓
Community Contributions
      ↓
Productization
```

---

# 4. V4.0 NORTH STAR

一个完全陌生的开发者应该能够：

```text
Discover
   ↓
Install
   ↓
Run
   ↓
Use
   ↓
Integrate
   ↓
Extend
   ↓
Contribute
   ↓
Publish Plugin
```

一个数据科学用户应该能够：

```text
Upload Dataset
   ↓
Ask Question
   ↓
Analyze
   ↓
Inspect Evidence
   ↓
Generate Report
   ↓
Export Notebook
```

一个 AI Agent 应该能够：

```text
Discover Data Science Tools
   ↓
Call DSA MCP
   ↓
Execute Analysis
   ↓
Retrieve Evidence
```

---

# 5. V4.0 STRATEGIC THEMES

V4.0 分为 12 个 Workstream：

```text
W1  Public Release Audit
W2  Core SDK & API Stabilization
W3  Plugin & Extension Architecture
W4  MCP Apps & Agent Integration
W5  Developer Experience
W6  Jupyter / VS Code Integration
W7  Community & Contribution System
W8  Benchmark Leaderboard & Dataset Hub
W9  Performance & Scalability
W10 Productization Layer
W11 Open-Source Growth Infrastructure
W12 V4 Release & Ecosystem Launch
```

---

# 6. V4.0 NON-GOALS

V4.0 暂时不要建设：

```text
Enterprise SaaS
Complex Billing
Multi-Tenant Cloud
Large Kubernetes Cluster
Paid Infrastructure
Custom Foundation Model
Massive Distributed Training
Full Commercial CRM
Complex Social Network
```

除非这些东西成为真实用户需求。

---

# 7. ARCHITECTURE FREEZE

V3.0 核心系统默认保持稳定：

```text
LangGraph
FastAPI
Next.js
DuckDB
Polars
SQLite
Evidence Graph
Evaluation Framework
Python Sandbox
MCP
```

V4 可以做：

```text
Adapters
SDK
Plugins
Integrations
Extensions
```

但不能破坏核心 Domain Layer。

---

# 8. ARCHITECTURAL PRINCIPLE

V4 架构从：

```text
Monolithic Application
```

逐渐演进成：

```text
Core Engine
     +
SDK
     +
CLI
     +
MCP
     +
Plugins
     +
Integrations
     +
Web UI
```

---

# 9. TARGET ARCHITECTURE

```text
                    Data Science Agent
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
       Core Engine       SDK/API          MCP Server
          │                │                │
          └────────────────┼────────────────┘
                           │
                 ┌─────────┴─────────┐
                 ▼                   ▼
              Plugins           Integrations
                 │                   │
          ┌──────┼──────┐       ┌────┼────┐
          ▼      ▼      ▼       ▼         ▼
         ML    Stats   Viz   Jupyter    VS Code
```

---

# 10. W1 — PUBLIC RELEASE AUDIT

V3 已经发布。

V4 第一阶段不是开发。

先检查：

```text
GitHub repository
README
Release
Tags
License
Citation
Security
Issues
Discussions
Actions
Packages
Documentation
```

---

## 11. GITHUB HEALTH AUDIT

检查：

```text
README.md
LICENSE
CITATION.cff
CONTRIBUTING.md
CODE_OF_CONDUCT.md
SECURITY.md
CHANGELOG.md
ROADMAP.md
```

另外检查 GitHub Security：

```text
Dependabot
Dependency Review
Secret Scanning
Push Protection
Code Scanning
```

GitHub 官方目前将这些作为公开仓库的重要安全与维护能力，应尽可能启用并配置。

---

# 12. PUBLIC RELEASE CHECKLIST

创建：

```text
docs/v4/PUBLIC_RELEASE_AUDIT.md
```

检查：

```text
Repository discoverability
README clarity
Installability
Security
License
Citation
Contribution flow
Issue templates
PR templates
Documentation
Examples
Releases
```

---

# 13. REPOSITORY FIRST-IMPRESSION TEST

模拟：

> 一个第一次看到 GitHub 项目的人。

判断在：

```text
10 seconds
30 seconds
2 minutes
10 minutes
```

分别能够回答：

```text
What is it?
Why should I care?
How do I run it?
Why is it different?
How do I contribute?
How is it evaluated?
```

---

# 14. W2 — CORE SDK & API STABILIZATION

V3 有 CLI 和 API。

V4 要正式把它们提升成稳定开发接口。

---

# 15. PYTHON SDK

建立稳定：

```python
from data_science_agent import Agent


agent = Agent()


result = await agent.analyze(
    dataset="sales.csv",
    task="Analyze revenue decline"
)
```

---

# 16. SDK DESIGN

定义清晰 API：

```text
Agent
Dataset
Analysis
Evidence
Artifact
Report
Benchmark
Reproduction
```

---

# 17. SDK VERSIONING

采用：

```text
SemVer
```

规则：

```text
MAJOR
Breaking API


MINOR
Backward-compatible feature


PATCH
Bug fix
```

---

# 18. API STABILITY

定义：

```text
Stable
Experimental
Internal
Deprecated
```

禁止外部开发者依赖：

```text
Internal
```

API。

---

# 19. API CONTRACT TESTING

所有 Public API 必须拥有：

```text
Input validation
Output schema
Backward compatibility
Error contract
Documentation
Example
```

---

# 20. API COMPATIBILITY

建立：

```text
tests/api/compatibility/
```

每次 Release 自动检查：

```text
breaking changes
schema changes
endpoint changes
SDK changes
```

---

# 21. W3 — PLUGIN & EXTENSION ARCHITECTURE

这是 V4 最重要的架构升级之一。

V3：

```text
Core
+
17 Tools
```

V4：

```text
Core
+
Built-in Tools
+
External Plugins
```

---

# 22. PLUGIN CONCEPT

定义：

> A plugin is an independently installable extension that provides additional Data Science capabilities without modifying the core engine.

---

# 23. PLUGIN TYPES

支持：

```text
Statistics Plugin
ML Plugin
Visualization Plugin
Data Source Plugin
Forecasting Plugin
Report Plugin
LLM Provider Plugin
Evaluation Plugin
```

---

# 24. PLUGIN INTERFACE

设计：

```python
class DataSciencePlugin:


    name: str
    version: str


    def register_tools(self):
        ...


    def register_models(self):
        ...


    def register_evaluators(self):
        ...
```

---

# 25. PLUGIN MANIFEST

例如：

```yaml
name: dsa-time-series
version: 1.0.0


type:
  - forecasting


requires:
  dsa: ">=4.0,<5.0"


license: MIT


entrypoint:
  python: dsa_time_series.plugin:register
```

---

# 26. PLUGIN SECURITY

插件必须：

```text
declare permissions
declare dependencies
declare network requirements
declare filesystem requirements
```

禁止插件默认拥有：

```text
unrestricted filesystem
unrestricted network
unrestricted shell
```

---

# 27. PLUGIN DISCOVERY

首先支持：

```text
Local Plugin Discovery
```

不要一开始搭建复杂云端 Marketplace。

---

# 28. PLUGIN REGISTRY

建立：

```text
plugins/
```

保存：

```text
manifest
metadata
license
documentation
version
compatibility
security
```

---

# 29. W4 — MCP APPS & AGENT INTEGRATION

MCP 2026-07-28 已经将 MCP Apps 作为扩展体系的一部分，因此 V4 可以开始探索：

> **让 Data Science Agent 的分析结果成为其他 AI Agent 可以直接交互的应用界面。**

---

# 30. MCP INTEGRATION LEVELS

Level 1：

```text
MCP Tools
```

Level 2：

```text
MCP Resources
```

Level 3：

```text
MCP Apps
```

Level 4：

```text
Task-based Long-running Analysis
```

---

# 31. MCP DATA SCIENCE APP

实现一个 MCP-oriented analysis UI：

```text
Dataset
↓
Question
↓
Analysis
↓
Evidence
↓
Visualization
```

---

# 32. MCP APP PRINCIPLE

不要把前端全部绑定到 MCP。

架构：

```text
Core Domain
     ↓
MCP Adapter
     ↓
MCP App
```

---

# 33. W5 — DEVELOPER EXPERIENCE

V4 的关键：

> **Developer Experience > Feature Count**

---

# 34. ONE COMMAND SETUP

目标：

```bash
dsa doctor
```

检查：

```text
Python
Node
Docker
LLM
Database
Ollama
Environment
Permissions
Disk
Memory
```

---

# 35. ONE COMMAND DEMO

继续保持：

```bash
dsa demo
```

并增加：

```bash
dsa demo --mode local
dsa demo --mode api
```

---

# 36. ONE COMMAND PROJECT

增加：

```bash
dsa init my-project
```

生成：

```text
my-project/
├── datasets/
├── analyses/
├── reports/
├── notebooks/
├── config.yaml
└── README.md
```

---

# 37. CLI UX

命令：

```text
dsa init
dsa doctor
dsa demo
dsa analyze
dsa profile
dsa benchmark
dsa reproduce
dsa research
dsa plugin
dsa mcp
```

每条命令必须具备：

```text
--help
clear error
exit code
structured output
```

---

# 38. W6 — JUPYTER INTEGRATION

Data Science 用户的重要入口之一是 Jupyter。

V4 应提供：

```text
Data Science Agent Jupyter Extension
```

---

# 39. JUPYTER WORKFLOW

允许：

```python
from data_science_agent import Agent


agent = Agent()


result = await agent.analyze(...)
```

并：

```text
Evidence
Charts
Tables
Reports
```

直接显示在 Notebook。

---

# 40. NOTEBOOK MAGIC

考虑提供：

```text
%dsa
```

例如：

```text
%dsa analyze revenue.csv
```

---

# 41. NOTEBOOK REPRODUCIBILITY

Notebook 必须保留：

```text
Dataset Hash
Tool Version
Prompt Version
Agent Version
Experiment ID
```

---

# 42. W6B — VS CODE INTEGRATION

V4 可以提供轻量 VS Code Extension。

第一版只做：

```text
Dataset Explorer
Ask DSA
Run Analysis
View Evidence
Open Report
```

不要一开始开发复杂 IDE。

---

# 43. W7 — COMMUNITY & CONTRIBUTION

V3 是成熟项目。

V4 必须开始考虑：

> **别人怎么参与？**

---

# 44. CONTRIBUTOR PATH

建立：

```text
Contributor
    ↓
First Issue
    ↓
Small PR
    ↓
Tool Plugin
    ↓
Benchmark Contribution
    ↓
Research Contribution
```

---

# 45. GOOD FIRST ISSUES

准备：

```text
docs
examples
tests
benchmark
plugins
statistics
visualization
```

标签：

```text
good first issue
help wanted
benchmark
research
documentation
```

---

# 46. CONTRIBUTOR DOCUMENTATION

创建：

```text
docs/v4/CONTRIBUTOR_GUIDE.md
```

内容：

```text
Architecture
Setup
Testing
Coding Standards
Plugin Development
Benchmark Development
Research Contributions
PR Process
```

---

# 47. DEVELOPER EXPERIENCE METRIC

记录：

```text
time_to_first_success
time_to_first_test
time_to_first_plugin
time_to_first_contribution
```

---

# 48. W8 — BENCHMARK LEADERBOARD & DATASET HUB

V3 Benchmark 是研究工具。

V4 可以把它做成：

> **Community Benchmark**

---

# 49. BENCHMARK SUBMISSION

允许：

```text
External System
↓
Submit Results
↓
Validate Format
↓
Leaderboard
```

---

# 50. LEADERBOARD SCHEMA

例如：

| System   | Task Success | Statistical Accuracy | Evidence Coverage | Reproducibility | Latency | Cost |
| -------- | -----------: | -------------------: | ----------------: | --------------: | ------: | ---: |
| DSA      |              |                      |                   |                 |         |      |
| System B |              |                      |                   |                 |         |      |

禁止未经验证的提交进入正式排行榜。

---

# 51. LEADERBOARD INTEGRITY

每个结果需要：

```text
system_name
version
commit
benchmark_version
model
configuration
seed
timestamp
results
```

---

# 52. DATASET HUB

V4 可以提供：

```text
examples/
benchmark-data/
```

但必须：

```text
license
source
citation
hash
version
```

---

# 53. W9 — PERFORMANCE & SCALABILITY

V4 需要开始考虑：

> "100 users 同时用会怎样？"

但不立即搭建 Kubernetes。

---

# 54. PERFORMANCE TARGETS

建立：

```text
P50
P95
P99
```

指标：

```text
API latency
Tool latency
Agent latency
Report latency
Dataset loading
Concurrent runs
Memory
CPU
```

---

# 55. CONCURRENCY TESTING

至少测试：

```text
1 run
5 runs
10 runs
25 runs
50 runs
```

记录：

```text
throughput
failure
memory
latency
```

---

# 56. DATA SCALE TESTING

测试：

```text
10MB
50MB
100MB
250MB
500MB
1GB
```

如果超出当前限制：

明确报告。

不要通过偷偷删除数据来制造"支持"。

---

# 57. RESOURCE MANAGEMENT

增加：

```text
Job Queue
Execution Limits
Cancellation
Timeout
Backpressure
```

保持本地优先。

---

# 58. W10 — PRODUCTIZATION LAYER

这是 V4 与 V3 的本质区别。

---

# 59. PRODUCT BOUNDARY

明确区分：

```text
Open Source Core
Optional Product Layer
```

---

# 60. OPEN SOURCE CORE

保持：

```text
Agent
Tools
Statistics
ML
Evidence
Benchmark
Reproduction
MCP
SDK
CLI
```

---

# 61. OPTIONAL PRODUCT LAYER

未来可以：

```text
Hosted Service
Team Workspace
Cloud Execution
Collaboration
Managed Benchmarks
Enterprise Integration
```

但 V4 不强制建设。

---

# 62. PRODUCT DISCOVERY

建立：

```text
docs/v4/product-discovery.md
```

记录：

```text
Potential Users
User Problems
Use Cases
Pain Points
Potential Pricing
Competitors
Differentiators
Risks
```

---

# 63. USER PERSONAS

至少：

```text
Data Science Student
Data Analyst
Researcher
ML Engineer
AI Engineer
```

---

# 64. USER WORKFLOW ANALYSIS

研究：

```text
Discover
Install
First Use
Repeated Use
Integration
Contribution
```

---

# 65. V4 PRODUCT METRICS

不要只看 GitHub stars。

建立：

```text
Install Success Rate
First Demo Success
Weekly Active Users
Repeat Usage
Analysis Runs
Benchmark Submissions
Plugins Created
Contributors
Issues
PRs
Documentation Usage
```

---

# 66. W11 — OPEN-SOURCE GROWTH INFRASTRUCTURE

---

# 67. GITHUB PROJECT HEALTH

继续维护：

```text
Issues
Discussions
Projects
Milestones
Releases
Security
Actions
```

GitHub 官方建议公开项目至少配备 README、License、贡献规范和 Code of Conduct，并启用 Dependabot、Secret Scanning、Push Protection 和 Code Scanning 等安全能力。

---

# 68. COMMUNITY HEALTH FILES

确保：

```text
.github/
├── ISSUE_TEMPLATE/
├── PULL_REQUEST_TEMPLATE.md
├── dependabot.yml
├── workflows/
└── CODEOWNERS
```

---

# 69. CODEOWNERS

根据模块设置：

```text
core
agent
statistics
ml
mcp
docs
benchmark
security
```

---

# 70. AUTOMATED RELEASE

GitHub Actions 自动：

```text
test
build
package
publish
release notes
```

但：

> 正式 Release 必须经过 release verification。

---

# 71. PACKAGE DISTRIBUTION

考虑：

```text
PyPI
npm
Docker
```

优先级：

```text
PyPI
Docker
npm / CLI components
```

---

# 72. CONTAINER DISTRIBUTION

提供：

```bash
docker pull ...
```

并明确：

```text
image version
Python version
build commit
```

---

# 73. DOCUMENTATION SITE

MkDocs 必须继续维护。

目标：

```text
docs.data-science-agent...
```

如果没有免费域名，则继续使用 GitHub Pages。

禁止为了文档强制使用付费 SaaS。

---

# 74. W12 — V4 RELEASE & ECOSYSTEM LAUNCH

---

# 75. VERSION

目标：

```text
v4.0.0
```

---

# 76. V4 RELEASE GATES

必须通过：

```text
pytest
mypy
ruff
npm build
docker build
docker run
CLI smoke tests
SDK tests
plugin tests
MCP tests
benchmark regression
security suite
reproduction suite
external install
documentation build
```

---

# 77. BACKWARD COMPATIBILITY

确保：

```text
V3 SDK
V3 CLI
V3 API
```

至少存在明确：

```text
migration guide
deprecation policy
compatibility matrix
```

---

# 78. MIGRATION GUIDE

创建：

```text
docs/v4/MIGRATION_V3_TO_V4.md
```

包含：

```text
Breaking Changes
New APIs
Deprecated APIs
Plugin Migration
MCP Migration
CLI Migration
SDK Migration
```

---

# 79. V4 DOCUMENTATION

新增：

```text
docs/v4/
├── overview.md
├── sdk.md
├── cli.md
├── plugins.md
├── mcp.md
├── jupyter.md
├── vscode.md
├── benchmark.md
├── contributing.md
├── product.md
└── migration.md
```

---

# 80. V4 SHOWCASE

建立至少：

```text
Showcase 1:
Natural Language → Data Analysis

Showcase 2:
Statistical Analysis

Showcase 3:
ML

Showcase 4:
Evidence Trace

Showcase 5:
Reproducibility

Showcase 6:
Jupyter

Showcase 7:
MCP

Showcase 8:
Plugin
```

---

# 81. FLAGSHIP PLUGIN

V4 必须至少实现：

> 一个真正独立于 Core 的官方示例 Plugin。

例如：

```text
dsa-time-series
```

功能：

```text
Forecasting
Backtesting
Forecast Visualization
```

要求：

```text
separate package
separate tests
separate README
own manifest
own version
```

---

# 82. FLAGSHIP INTEGRATION

至少完成一个：

```text
Jupyter
VS Code
MCP App
```

完整集成。

---

# 83. V4 PRODUCT DEMO

最终 Demo：

```text
User
 ↓
Upload Data
 ↓
Ask Question
 ↓
Agent
 ↓
Statistics
 ↓
Plugin
 ↓
Evidence
 ↓
Report
 ↓
Notebook
 ↓
MCP / SDK Integration
```

---

# 84. V4 SUCCESS METRICS

不允许只以：

```text
GitHub Stars
```

衡量成功。

至少跟踪：

```text
GitHub Stars
GitHub Forks
Issues
Pull Requests
Contributors
Downloads
Installs
Demo Success
Plugin Count
Benchmark Submissions
Documentation Visits
Repeat Usage
```

---

# 85. COMMUNITY TARGETS

V4 可以设定软目标，而非硬性承诺：

```text
First external contributor
First external plugin
First external benchmark submission
First external integration
First external research citation
```

---

# 86. PRODUCTIZATION RULE

除非已有真实用户需求：

不要提前建设：

```text
Billing
CRM
Complex Authentication
Enterprise SSO
Large Cloud Infrastructure
```

---

# 87. RESEARCH CONTINUITY

V4 不应放弃 Research。

继续支持：

```text
Benchmark
Evaluation
Research API
Experiment Manifest
Reproduction
Evidence
```

这样：

```text
Product
+
Research
```

继续共存。

---

# 88. V4 RESEARCH QUESTIONS

可探索：

```text
RQ1:
Can extensible agent architectures improve domain-specific data science performance?

RQ2:
Can plugins reduce the need for monolithic Agent architectures?

RQ3:
How does MCP-based interoperability affect data science agent utility?

RQ4:
Can external developers reproduce benchmark results?

RQ5:
How does agent modularity affect reliability and maintainability?
```

---

# 89. V4 ARCHITECTURAL RESEARCH

重点研究：

```text
Monolithic Agent
vs
Composable Agent Platform
```

比较：

```text
Development Cost
Reliability
Extensibility
Performance
Community Contribution
```

---

# 90. NO SELF-MODIFYING CORE

Core 不允许自行：

```text
rewrite code
install arbitrary plugin
change policy
change benchmark
change evaluator
```

所有扩展都必须：

```text
Explicit
Versioned
Validated
Permissioned
```

---

# 91. PLUGIN TRUST MODEL

分级：

```text
Official
Verified
Community
Experimental
```

---

# 92. PLUGIN COMPATIBILITY

每个 Plugin 必须声明：

```text
core version
API version
Python version
dependencies
license
permissions
```

---

# 93. PLUGIN SECURITY REVIEW

官方 Plugin：

```text
security scan
dependency scan
tests
documentation
```

Community Plugin：

显示：

```text
unverified
```

不要让 UI 将社区 Plugin 伪装成官方安全组件。

---

# 94. EXTERNAL API SECURITY

任何未来 Remote API 必须支持：

```text
authentication
authorization
rate limiting
request size limits
timeout
audit logs
```

---

# 95. PRIVACY

默认：

```text
Local-first
```

明确文档说明：

```text
Which data leaves machine
Which data stays local
When LLM API is called
What is logged
```

---

# 96. TELEMETRY POLICY

默认：

```text
No invasive telemetry
```

如果引入匿名统计：

必须：

```text
Opt-in
Documented
Disableable
Privacy-preserving
```

---

# 97. LICENSE POLICY

Core：

```text
MIT
```

Plugin：

允许：

```text
MIT
Apache-2.0
BSD
other compatible licenses
```

但必须：

```text
license metadata
```

---

# 98. DEPENDENCY POLICY

V4 新增依赖必须记录：

```text
Purpose
License
Security
Maintenance
Size
Alternatives
Vendor Lock-in
```

---

# 99. PERFORMANCE PRINCIPLE

V4 不以"最大吞吐"作为唯一目标。

优先：

```text
Predictability
Reliability
Resource Bounds
Graceful Degradation
```

---

# 100. FAILURE POLICY

如果：

```text
Plugin fails
Model unavailable
MCP unavailable
LLM unavailable
Dataset too large
```

核心系统必须：

```text
fail clearly
recover where possible
preserve state
```

---

# 101. OBSERVABILITY

V4 新增：

```text
Plugin execution traces
SDK execution traces
MCP execution traces
Integration errors
User workflow events
```

但不得泄漏：

```text
API Key
Private Dataset
Sensitive User Data
```

---

# 102. ERROR UX

错误消息必须回答：

```text
What happened?
Why?
Can I recover?
How?
```

例如：

```text
Plugin dependency missing.


Required:
statsmodels >= X


Fix:
pip install ...
```

---

# 103. V4 DEVELOPMENT ORDER

严格：

```text
Phase A
V3 Freeze
       ↓
Phase B
Public Release Audit
       ↓
Phase C
SDK/API Stabilization
       ↓
Phase D
Plugin Architecture
       ↓
Phase E
MCP Apps / Integrations
       ↓
Phase F
Jupyter / VS Code
       ↓
Phase G
Community Infrastructure
       ↓
Phase H
Benchmark Leaderboard
       ↓
Phase I
Performance / Scale
       ↓
Phase J
Productization
       ↓
Phase K
Release Engineering
       ↓
Phase L
V4 Release
```

---

# 104. PHASE DISCIPLINE

每次只执行一个 Phase。

流程：

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
Security
↓
Document
↓
Commit
↓
STOP
```

---

# 105. NO BULK IMPLEMENTATION

禁止一次性：

```text
implement V4
```

必须逐 Phase。

---

# 106. FIRST EXECUTION

当前第一次执行 V4：

> **ONLY PHASE A — V3 FREEZE**

不得直接实现：

```text
SDK
Plugin
MCP Apps
Jupyter
VS Code
Leaderboard
Product Layer
```

---

# 107. PHASE A — V3 FREEZE

首先阅读：

```text
DATA_SCIENCE_AGENT_V0_1.md
DATA_SCIENCE_AGENT.md
DATA_SCIENCE_AGENT_V2_0.md
DATA_SCIENCE_AGENT_V3_0.md
AGENTS.md
docs/DEVELOPMENT_STATUS.md
docs/v3/V2_FINAL_BASELINE.md
```

---

# 108. CURRENT REPOSITORY INSPECTION

检查：

```text
repository
Agent Graph
Core Domain
SDK / CLI
Evaluation
Benchmark
Evidence
Reproduction
Research
MCP
Security
Frontend
Documentation
CI
Release
```

---

# 109. BASELINE REVALIDATION

执行：

```bash
pytest -q
mypy .
ruff check packages apps/api tests
npm run build
docker compose config

dsa --limit 50
dsa v2 --limit 100
dsa demo

dsa verify-release v3.0.0
```

---

# 110. GITHUB / PUBLIC RELEASE AUDIT

检查：

```text
README
LICENSE
CITATION
SECURITY
CONTRIBUTING
CODE_OF_CONDUCT
CHANGELOG
ROADMAP
Issue Templates
PR Template
Dependabot
Secret Scanning
Push Protection
Code Scanning
```

---

# 111. V3 FREEZE REPORT

创建：

```text
docs/v4/V3_FREEZE_REPORT.md
```

内容：

```text
1. V3 Release Verification
2. Current Architecture
3. Public Repository Health
4. SDK / CLI Status
5. MCP Status
6. Benchmark Status
7. Research Status
8. Security Status
9. Documentation Status
10. Technical Debt
11. Ecosystem Gaps
12. V4 Priorities
```

---

# 112. V4 PRIORITY DECISION

根据实际代码和用户体验提出：

```text
Top 10 V4 Problems
```

每项包括：

```text
Problem
Evidence
Impact
Effort
Risk
Priority
```

---

# 113. PHASE A STOP CONDITION

完成后：

不要实现任何 V4 新功能。

只输出：

```text
V3 FREEZE VERIFIED
```

以及：

```text
Current Status
Regressions
Public Release Risks
Developer Experience Risks
Ecosystem Risks
Recommended V4 Workstream Order
```

然后：

> **STOP**

等待下一阶段指令。

---

# 114. FINAL V4 VISION

V4 最终应该把：

```text
Data Science Agent
```

升级为：

```text
Data Science Agent Platform
```

概念结构：

```text
                         Data Science Agent
                                  │
               ┌──────────────────┼──────────────────┐
               │                  │                  │
               ▼                  ▼                  ▼
            Core Engine          SDK               MCP
               │                  │                  │
               └──────────────────┼──────────────────┘
                                  │
                      ┌───────────┴───────────┐
                      ▼                       ▼
                   Plugins               Integrations
                      │                       │
              ┌───────┼───────┐        ┌─────┼─────┐
              ▼       ▼       ▼        ▼           ▼
             ML     Stats    Viz   Jupyter       VS Code
              │
              ▼
         Community
              │
              ▼
         Benchmark
              │
              ▼
          Research
```

---

# 115. FINAL PRODUCT PRINCIPLE

V3 的核心：

> **Prove that it works.**

V4 的核心：

> **Make others use it, extend it, integrate it, and contribute to it.**

---

# 116. FINAL SUCCESS DEFINITION

V4 成功不是：

```text
more code
more agents
more tools
more pages
```

而是：

```text
External Developer
      ↓
Install
      ↓
Use
      ↓
Integrate
      ↓
Extend
      ↓
Plugin
      ↓
Contribution
      ↓
Benchmark
      ↓
Research
```

如果这条链路真正形成：

> Data Science Agent 才从一个优秀个人项目正式进入一个有生命力的开源生态。