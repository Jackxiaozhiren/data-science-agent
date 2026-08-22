# Data Science Agent V4.1

## Ecosystem Validation, Integration Hardening & Production Readiness

---

# 0. PROJECT STATUS

## Project

**Data Science Agent**

## Positioning

> **An Evidence-Grounded Autonomous Data Science Platform**

## Core Slogan

> **From Natural Language to Reproducible Data Science.**

---

# 1. CURRENT RELEASE BASELINE

Current release:

```text
Version: v4.0.0
Git Tag: v4.0.0
Release Commit: fbf6dd7
```

---

# 2. CURRENT VERIFIED STATUS

V4.0.0 当前已完成：

## Engineering

```text
pytest:
157 passed

mypy:
104 clean (strict)

ruff:
All checks passed

npm build:
13/13 routes

docker compose config:
valid

dsa verify-release v4.0.0:
12/12 PASS
```

## Benchmark

```text
dsa:
50/50 @ 1.00

dsa v2:
100/100 @ 1.00
```

## SDK

```text
Agent
Dataset
Benchmark
Repro
API_STABILITY
4.0.0
```

## Plugins

```text
DataSciencePlugin
PluginManifest
Local Plugin Registry
dsa-time-series
```

## MCP

```text
MCP 2026-07-28
Stateless
Resources
MCP App Shell
```

## DX

```text
dsa doctor
dsa init
dsa analyze
dsa profile
dsa benchmark
--json
--help
structured errors
exit codes
```

## Integrations

```text
Jupyter:
stub

VS Code:
light extension stub

MCP Apps:
App shell
```

---

# 3. IMPORTANT V4.0 ASSESSMENT

V4.0 已完成：

```text
Core Platform Architecture
SDK
CLI
Plugin Architecture
MCP Integration
Benchmark Infrastructure
Research Infrastructure
Open-source Infrastructure
```

但以下能力目前仍处于：

```text
Jupyter:
Stub / Minimal

VS Code:
Stub / Minimal

MCP App:
Shell / Initial Integration
```

因此：

> V4.1 的核心目标不是增加新的平台层，而是将现有"骨架能力"转变成"真实可用能力"。

禁止通过修改 README、版本号或文档来伪装某项功能已经成熟。

---

# 4. V4.1 CORE OBJECTIVE

V4.1 定位：

> **Ecosystem Validation, Integration Hardening & Production Readiness**

核心转变：

```text
V4.0
Platform Skeleton
      ↓
V4.1
Real Integrations
      ↓
External Developer Validation
      ↓
Package Distribution
      ↓
Security Hardening
      ↓
Stable Ecosystem
```

---

# 5. V4.1 NORTH STAR

一个完全陌生的开发者应该能够：

```text
Clone
↓
Install
↓
Run
↓
Use SDK
↓
Use CLI
↓
Install Plugin
↓
Run Jupyter
↓
Use MCP
↓
Inspect Evidence
↓
Generate Report
↓
Contribute
```

且不需要：

```text
Developer-specific path
Developer secret
Private dataset
Internal service
Manual source patch
```

---

# 6. V4.1 PRINCIPLES

优先级：

```text
Correctness
>
Real Usability
>
Compatibility
>
Security
>
Reproducibility
>
Developer Experience
>
Maintainability
>
Performance
>
UI Polish
```

---

# 7. NON-GOALS

V4.1 暂时不要建设：

```text
Enterprise SaaS
Billing
Complex Multi-tenancy
Large Kubernetes Deployment
Custom Foundation Model
Massive Distributed Training
Complex Social Platform
Commercial CRM
```

除非有真实需求。

---

# 8. ARCHITECTURE FREEZE

保持：

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
SDK
Plugin Layer
```

不得进行无必要的架构重写。

如需重大变化：

必须创建 ADR：

```text
Problem
Evidence
Impact
Alternatives
Recommendation
Migration Plan
Rollback Plan
```

---

# 9. WORKSTREAMS

V4.1 分为 10 个 Workstream：

```text
W1  V4 Freeze & Claim Audit
W2  SDK / CLI Distribution Hardening
W3  Plugin Runtime Hardening
W4  Jupyter Real Integration
W5  VS Code Real Integration
W6  MCP App Real Integration
W7  Public Security & Supply Chain
W8  External Developer Validation
W9  Performance / Compatibility / Reliability
W10 V4.1 Release & Ecosystem Certification
```

---

# W1 — V4 FREEZE & CLAIM AUDIT

## 10. Baseline Verification

在任何修改前，实际执行：

```bash
pytest -q
mypy .
ruff check packages apps/api tests
npm build
docker compose config

dsa doctor
dsa verify-release v4.0.0

dsa --limit 50
dsa v2 --limit 100

dsa demo
```

---

## 11. Integration Verification

实际运行：

```text
SDK smoke test
CLI smoke test
Plugin discovery
Plugin execution
MCP server startup
MCP tool discovery
MCP resource access
MCP App startup
Jupyter stub
VS Code stub
```

必须把：

```text
PASS
PARTIAL
STUB
NOT IMPLEMENTED
NOT VERIFIED
```

严格区分。

---

## 12. Claim Audit

扫描：

```text
README
Docs
CHANGELOG
ROADMAP
CITATION
Website
Examples
CLI help
```

寻找可能过度宣传的：

```text
Production-ready
Fully supported
Stable
Cross-platform
MCP Apps support
Jupyter support
VS Code support
Plugin ecosystem
```

如果实际只是：

```text
Stub
Shell
Prototype
Experimental
```

必须明确标记。

---

## 13. V4.0 Truth Report

创建：

```text
docs/v4_1/V4_IMPLEMENTATION_TRUTH.md
```

每个功能记录：

| Capability | Status | Evidence | Maturity |
| ---------- | ------ | -------- | -------- |
| SDK        |        |          |          |
| CLI        |        |          |          |
| Plugin     |        |          |          |
| MCP        |        |          |          |
| MCP App    |        |          |          |
| Jupyter    |        |          |          |
| VS Code    |        |          |          |
| Benchmark  |        |          |          |
| Research   |        |          |          |

Maturity：

```text
Production
Stable
Experimental
Prototype
Stub
```

---

# W2 — SDK / CLI DISTRIBUTION HARDENING

目标：

> 让 Data Science Agent 真正成为可以被其他项目依赖的 Python SDK + CLI。

---

## 14. SDK Public Surface

最终稳定 API：

```python
from data_science_agent import (
    Agent,
    Dataset,
    Analysis,
    Evidence,
    Artifact,
    Benchmark,
    Reproduction,
)
```

---

## 15. Public API Audit

将 API 分类：

```text
Stable
Experimental
Internal
Deprecated
```

禁止：

```text
public code
```

依赖：

```text
_internal
implementation modules
```

---

## 16. SDK Documentation

每个 Stable API 必须有：

```text
Description
Parameters
Return Value
Errors
Example
Version
```

---

## 17. SDK Contract Tests

创建：

```text
tests/sdk/
tests/api/compatibility/
```

验证：

```text
input schema
output schema
error schema
backward compatibility
serialization
async behavior
```

---

## 18. Package Metadata

检查：

```text
pyproject.toml
version
dependencies
optional dependencies
license
authors
URLs
classifiers
README
```

---

## 19. Package Installation

必须验证：

```bash
pip install .
```

以及：

```bash
python -c "from data_science_agent import Agent"
```

如果准备公开 PyPI：

```bash
pip install jack-data-science-agent
```

必须通过真实发布流程验证。

禁止模拟：

```text
PyPI published
```

---

## 20. CLI Contract

必须保证：

```text
dsa --help
dsa doctor
dsa init
dsa demo
dsa analyze
dsa profile
dsa benchmark
dsa reproduce
dsa research
dsa plugin
dsa mcp
```

都具备：

```text
help
exit code
structured output
clear errors
```

---

# W3 — PLUGIN RUNTIME HARDENING

当前：

```text
dsa-time-series
```

已经能够发现。

V4.1 的目标是：

> **Plugin 不只是"能被发现"，而是能稳定安装、执行、验证、卸载。**

---

## 21. Plugin Lifecycle

实现：

```text
Discover
↓
Validate
↓
Install
↓
Load
↓
Execute
↓
Disable
↓
Remove
```

---

## 22. Plugin Manifest

强制：

```yaml
name:
version:

dsa:
  min_version:
  max_version:

license:

permissions:

dependencies:

entrypoint:

capabilities:
```

---

## 23. Plugin Permissions

权限至少：

```text
filesystem.read
filesystem.write
network
process
dataset.read
dataset.write
artifact.write
```

默认：

```text
DENY
```

---

## 24. Plugin Validation

安装 Plugin 前检查：

```text
manifest
version
dependency
license
hash
signature if available
permissions
compatibility
```

---

## 25. Plugin Failure Isolation

一个 Plugin 失败：

不得使：

```text
Core Agent
Other Plugins
Benchmark
MCP
```

全部崩溃。

---

## 26. Plugin Evaluation

官方 Plugin 必须至少具有：

```text
unit tests
integration tests
security tests
documentation
example
benchmark task
```

---

## 27. dsa-time-series

把当前旗舰 Plugin 从：

```text
discoverable plugin
```

升级为：

```text
fully executable plugin
```

至少实现：

```text
forecast
backtest
metrics
visualization
evidence
```

并能够接入：

```text
Agent
SDK
CLI
Benchmark
Report
```

---

# W4 — JUPYTER REAL INTEGRATION

当前：

```text
stub
```

必须明确：

> **V4.1 不允许把 Stub 当成完成。**

---

## 28. Jupyter MVP

至少实现：

```text
%dsa
```

以及：

```python
from data_science_agent import Agent

agent = Agent(...)
```

---

## 29. Notebook UX

必须支持：

```text
Ask Question
↓
Run Analysis
↓
Show Progress
↓
Show Chart
↓
Show Evidence
↓
Show Result
```

---

## 30. Notebook Artifact Integration

支持：

```text
Chart
Table
Evidence
Report
Artifact
```

直接嵌入 Notebook。

---

## 31. Reproducibility

Notebook metadata：

```text
dataset_hash
agent_version
sdk_version
prompt_version
tool_version
experiment_id
```

---

## 32. Jupyter Installation

提供明确：

```bash
pip install ...
```

并通过 clean environment 验证。

---

# W5 — VS CODE REAL INTEGRATION

当前为：

```text
light extension stub
```

V4.1 只实现一个真正可用的最小闭环。

---

## 33. VS Code MVP

至少：

```text
Open Dataset
↓
Ask DSA
↓
Run Analysis
↓
View Result
↓
View Evidence
↓
Open Report
```

---

## 34. VS Code Architecture

保持：

```text
Extension
↓
Public SDK / CLI
↓
Core Engine
```

不要在 Extension 中复制 Agent 逻辑。

---

## 35. VS Code Failure Handling

必须支持：

```text
LLM unavailable
Python unavailable
Dataset missing
Plugin failure
Backend unavailable
```

且提供明确解决建议。

---

# W6 — MCP APP REAL INTEGRATION

当前：

```text
MCP App Shell
```

需要升级到真正可用。

---

## 36. MCP App Objective

支持：

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
↓
Report
```

在 MCP-compatible Client 中完成最小闭环。

---

## 37. MCP Resource Model

至少提供：

```text
dataset://
evidence://
report://
artifact://
analysis://
```

---

## 38. Explicit Application State

不要依赖：

```text
protocol session
```

应用状态必须使用：

```text
analysis_id
run_id
project_id
artifact_id
```

等显式句柄。

MCP 2026-07-28 正式规范明确采用 stateless protocol core；如果应用需要状态，应通过显式 handle 传递，而不是重新引入协议层 session 状态。

---

## 39. MCP App Acceptance Test

真实验证：

```text
Client
↓
Connect
↓
Discover
↓
Call Tool
↓
Receive Result
↓
Open Resource
↓
Render App
↓
Inspect Evidence
```

---

## 40. MCP Compatibility

建立：

```text
docs/v4_1/MCP_COMPATIBILITY.md
```

检查：

```text
stateless core
tools/list
tools/call
resources
authorization
errors
cache hints
Tasks
MCP Apps
```

不要为了测试而重新实现协议。

---

# W7 — PUBLIC SECURITY & SUPPLY CHAIN

这是 V4.1 的重要升级。

---

## 41. GitHub Security

检查并尽可能启用：

```text
Dependabot Alerts
Dependabot Security Updates
Dependency Review
Secret Scanning
Push Protection
Code Scanning / CodeQL
```

GitHub 官方目前建议公共仓库至少启用这些安全能力；其中 Dependency Review 可以在 PR 中检查依赖变化及其安全和许可证影响。

---

## 42. CodeQL

建立：

```text
.github/workflows/codeql.yml
```

至少覆盖：

```text
Python
JavaScript / TypeScript
```

---

## 43. Dependency Review

PR 中检查：

```text
vulnerability
license
dependency change
```

---

## 44. Secret Protection

确保：

```text
API keys
tokens
passwords
credentials
```

不会进入：

```text
repository
Git history
CI artifacts
logs
```

GitHub Secret Scanning 会扫描整个 Git 历史中的硬编码凭据，因此不仅要检查当前工作树，也要检查发布历史是否存在潜在泄漏。

---

## 45. Plugin Supply Chain

插件安装必须防范：

```text
malicious plugin
dependency confusion
typosquatting
malicious dependency
arbitrary code execution
```

---

## 46. Dependency Pinning

生产依赖尽量：

```text
locked
versioned
auditable
```

开发依赖与运行时依赖区分。

---

## 47. SBOM

生成：

```text
release/sbom.json
```

包含：

```text
package
version
license
source
```

---

# W8 — EXTERNAL DEVELOPER VALIDATION

V4.1 必须真正验证：

> "陌生开发者能不能使用？"

---

## 48. Fresh Clone Test

从一个新的临时目录：

```text
git clone
↓
install
↓
setup
↓
doctor
↓
demo
```

不能依赖当前开发目录。

---

## 49. External Developer Test

模拟：

```text
Developer A
```

不知道内部实现。

任务：

```text
1. Install
2. Run demo
3. Use SDK
4. Create analysis
5. Install plugin
6. Run benchmark
7. Generate report
```

记录：

```text
time
errors
confusion
manual fixes
```

---

## 50. External Validation Report

创建：

```text
docs/v4_1/EXTERNAL_DEVELOPER_VALIDATION.md
```

包含：

```text
Environment
Steps
Failures
Fixes
Time to First Success
Developer Friction
Recommendations
```

---

# W9 — PERFORMANCE / COMPATIBILITY / RELIABILITY

---

## 51. Benchmark Performance

实际运行：

```text
Concurrency:
1
5
10
25
50
```

记录：

```text
P50
P95
P99
error rate
memory
CPU
throughput
```

---

## 52. SDK Performance

测试：

```text
dataset load
profile
analysis
report
evidence lookup
```

---

## 53. Plugin Performance

比较：

```text
Core only
Core + Plugin
```

确保 Plugin 引入不会导致明显异常开销。

---

## 54. Large Dataset

继续测试：

```text
10MB
50MB
100MB
250MB
500MB
1GB
```

必须明确：

```text
supported
degraded
unsupported
```

不得夸大兼容范围。

---

## 55. Cancellation

分析必须支持：

```text
start
cancel
timeout
recover
```

不能出现：

```text
orphaned process
永久占用资源
```

---

# W10 — V4.1 RELEASE & ECOSYSTEM CERTIFICATION

---

## 56. Version

```text
v4.1.0
```

---

## 57. Release Gate

必须通过：

```text
pytest
mypy
ruff
npm build
docker
security
CodeQL
dependency review
SDK compatibility
Plugin tests
MCP tests
Jupyter tests
VS Code tests
Benchmark regression
External validation
Demo
Documentation
```

---

## 58. Feature Maturity Gate

发布前必须明确：

```text
Stable
Experimental
Prototype
Stub
```

不得把 Stub 写进：

```text
Stable Features
```

---

## 59. V4.1 RELEASE MATRIX

创建：

```text
docs/v4_1/RELEASE_MATRIX.md
```

包含：

| Capability         | Status | Version | Test | Documentation |
| ------------------ | ------ | ------- | ---- | ------------- |
| Core Agent         |        |         |      |               |
| SDK                |        |         |      |               |
| CLI                |        |         |      |               |
| Plugin             |        |         |      |               |
| Time Series Plugin |        |         |      |               |
| MCP                |        |         |      |               |
| MCP App            |        |         |      |               |
| Jupyter            |        |         |      |               |
| VS Code            |        |         |      |               |
| Benchmark          |        |         |      |               |
| Reproduction       |        |         |      |               |

---

# 60. MIGRATION GUIDE

创建：

```text
docs/v4_1/MIGRATION_V4_0_TO_V4_1.md
```

包含：

```text
Breaking Changes
New APIs
Deprecated APIs
Plugin Changes
SDK Changes
CLI Changes
MCP Changes
Jupyter Changes
VS Code Changes
```

---

# 61. DOCUMENTATION

新增：

```text
docs/v4_1/
├── overview.md
├── sdk.md
├── plugins.md
├── jupyter.md
├── vscode.md
├── mcp.md
├── security.md
├── external-validation.md
├── performance.md
├── release.md
└── migration.md
```

---

# 62. PUBLIC README UPDATE

README 必须明确区分：

```text
Stable
Experimental
Coming Soon
```

特别处理：

```text
Jupyter
VS Code
MCP Apps
Plugin Ecosystem
```

不要模糊描述。

---

# 63. CHANGELOG

添加：

```text
v4.1.0
```

明确：

```text
Added
Changed
Fixed
Security
Compatibility
Deprecated
```

---

# 64. V4.1 RESEARCH OPPORTUNITY

V4.1 不是主要研究版本。

但应该记录一个新研究方向：

> **How does ecosystem modularity affect the reliability, usability, and maintainability of autonomous data science agents?**

可观察指标：

```text
integration_success
developer_time_to_first_success
plugin_failure_rate
extension_overhead
API_stability
user_friction
```

---

# 65. NO FABRICATED ADOPTION

禁止虚构：

```text
users
downloads
stars
plugins
contributors
external integrations
```

任何数量都必须来自：

```text
GitHub
PyPI
Docker
actual logs
actual surveys
actual submissions
```

---

# 66. NO FAKE SUPPORT

如果：

```text
Jupyter = Stub
```

不能写：

```text
Jupyter supported
```

应该写：

```text
Jupyter integration: Experimental / Stub
```

同样适用于：

```text
VS Code
MCP Apps
Plugin Marketplace
Cloud Deployment
```

---

# 67. PUBLIC SECURITY STANDARD

公开仓库必须至少具备：

```text
SECURITY.md
Dependabot
Secret Scanning
Push Protection
Code Scanning
Dependency Review
```

并通过 CI 检查。

GitHub 官方明确将这些能力作为公开仓库安全实践的重要组成部分。

---

# 68. FINAL V4.1 ARCHITECTURE

目标结构：

```text
                         Data Science Agent
                                  │
             ┌────────────────────┼────────────────────┐
             │                    │                    │
             ▼                    ▼                    ▼
         Core Engine             SDK                  MCP
             │                    │                    │
             └────────────────────┼────────────────────┘
                                  │
                   ┌──────────────┴──────────────┐
                   ▼                             ▼
               Plugins                     Integrations
                   │                             │
          ┌────────┼────────┐          ┌─────────┼─────────┐
          ▼        ▼        ▼          ▼         ▼         ▼
         ML      Stats      Viz     Jupyter    VS Code   MCP App
          │
          ▼
      Evaluation
          │
          ▼
      Evidence
          │
          ▼
      Research
```

---

# 69. V4.1 SUCCESS DEFINITION

V4.1 成功不是：

```text
more code
more tools
more agents
more pages
```

而是：

```text
A new developer can install the project.

A new developer can run the demo.

A new developer can use the SDK.

A new developer can install a plugin.

A new developer can run Jupyter integration.

A new developer can use the MCP integration.

A new developer can inspect evidence.

A new developer can reproduce an analysis.

A new developer can contribute code.

A new developer can understand which features are stable.
```

---

# 70. V4.1 QUALITY BAR

最终要求：

```text
Correct
Secure
Observable
Reproducible
Stable
Installable
Integrable
Extensible
Honest
Open-source friendly
```

---

# 71. DEVELOPMENT ORDER

严格按照：

```text
Phase A
V4 Freeze & Claim Audit


↓


Phase B
SDK / CLI Distribution


↓


Phase C
Plugin Runtime


↓


Phase D
Jupyter


↓


Phase E
VS Code


↓


Phase F
MCP App


↓


Phase G
Security / Supply Chain


↓


Phase H
External Developer Validation


↓


Phase I
Performance / Reliability


↓


Phase J
V4.1 Release
```

---

# 72. PHASE DISCIPLINE

每次只执行一个 Phase：

```text
Inspect
↓
Plan
↓
Implement
↓
Test
↓
Security
↓
Benchmark
↓
Document
↓
Commit
↓
STOP
```

不得自动进入下一 Phase。

---

# 73. FIRST EXECUTION

第一次执行：

> **ONLY PHASE A — V4 FREEZE & CLAIM AUDIT**

---

# 74. PHASE A — REQUIRED READING

阅读：

```text
AGENTS.md

DATA_SCIENCE_AGENT_V0_1.md

DATA_SCIENCE_AGENT_V2_0.md

DATA_SCIENCE_AGENT_V3_0.md

DATA_SCIENCE_AGENT_V4_0.md

docs/DEVELOPMENT_STATUS.md

docs/v3/V2_FINAL_BASELINE.md
```

---

# 75. PHASE A — REPOSITORY INSPECTION

检查：

```text
Core Engine
Agent Graph
SDK
CLI
Plugin Registry
dsa-time-series
MCP
MCP App
Jupyter
VS Code
Benchmark
Research
Security
Frontend
CI/CD
Docker
Documentation
Release
```

---

# 76. PHASE A — LIVE VERIFICATION

实际执行：

```bash
pytest -q

mypy .

ruff check packages apps/api tests

npm build

docker compose config

dsa doctor

dsa verify-release v4.0.0

dsa --limit 50

dsa v2 --limit 100

dsa demo
```

另外：

```text
SDK smoke test
Plugin discovery test
Plugin execution test
MCP test
MCP resource test
Jupyter test
VS Code test
Security suite
```

---

# 77. PHASE A — CLAIM VERIFICATION

重点检查当前所有文档对以下能力的描述是否与实际实现一致：

```text
SDK
CLI
Plugin
MCP
MCP Apps
Jupyter
VS Code
Benchmark
Research
Reproduction
Security
```

---

# 78. PHASE A — TRUTH REPORT

创建：

```text
docs/v4_1/V4_IMPLEMENTATION_TRUTH.md
```

---

# 79. PHASE A — RELEASE MATRIX

创建：

```text
docs/v4_1/RELEASE_MATRIX.md
```

---

# 80. PHASE A — STOP CONDITION

Phase A 完成后：

不要实现任何新功能。

不要：

```text
rewrite SDK
rewrite Plugin
rewrite MCP
rewrite Jupyter
rewrite VS Code
```

除非发现 Critical Regression。

只输出：

```text
V4.0 FREEZE VERIFIED
```

并报告：

```text
Current Status
Regressions
Truth Gaps
Public Release Risks
Integration Gaps
Security Gaps
Developer Experience Gaps
Recommended V4.1 Order
```

然后：

> **STOP**

---

# 81. FINAL STRATEGIC PRINCIPLE

V0.1：

> **Build the system.**

V1.x：

> **Harden the system.**

V2.0：

> **Evaluate the system.**

V3.0：

> **Validate and reproduce the system.**

V4.0：

> **Build the platform skeleton.**

V4.1：

> **Make the platform genuinely usable and integrable.**

最终目标：

```text
Core
↓
SDK
↓
Plugin
↓
MCP
↓
Jupyter
↓
VS Code
↓
External Developer
↓
Community
↓
Ecosystem
```

Data Science Agent 应逐步从：

> **一个优秀的开源 AI 数据科学项目**

演变为：

> **一个真正可扩展、可集成、可复现、可贡献的开源 Data Science Agent Platform。**
