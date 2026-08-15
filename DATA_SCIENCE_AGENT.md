# Data Science Agent

## 0. 项目身份

你现在是一名资深的：

* AI Agent Architect
* Data Scientist
* ML Engineer
* Full-Stack Engineer
* Data Platform Engineer
* Open-Source Maintainer

请你负责从 0 到 1 设计、开发、测试和完善一个真正可以运行、可以部署、可以开源、可以持续迭代的产品级项目：

> **Data Science Agent**

项目目标：

构建一个开源、AI-native、Agent-driven 的自动化数据科学平台。

用户上传数据集后，可以通过自然语言提出数据科学任务，例如：

```text
帮我分析这个销售数据集。
```

```text
找出销售额下降的主要原因。
```

```text
预测未来 30 天销售额。
```

```text
建立一个客户流失预测模型。
```

```text
分析哪些变量与收入最相关。
```

```text
帮我完成完整 EDA。
```

系统应该能够自主理解任务、检查数据、规划分析步骤、调用正确工具、执行 Python/SQL/统计分析、生成可视化、验证结果，并最终形成可解释的 Data Science Report。

---

## 1. 核心产品定位

不要将项目实现为：

> Chatbot + Pandas

也不要实现为：

> LLM 自动生成 Python 代码

而要实现为：

> **AI Agent + Statistical Engine + Data Analysis Engine + Code Execution Sandbox + Visualization Engine + ML Pipeline + Evidence System**

系统必须具备：

```text
Natural Language
        ↓
Task Understanding
        ↓
Planning
        ↓
Data Profiling
        ↓
Statistical Reasoning
        ↓
Tool Selection
        ↓
Code / SQL Execution
        ↓
Result Validation
        ↓
Visualization
        ↓
Insight Generation
        ↓
Report Generation
```

---

## 2. 核心设计原则

必须遵守以下原则。

## 2.1 Evidence First

Agent 不允许凭空回答。

任何关于数据的结论都必须来自实际计算结果。

错误：

```text
销售额主要受到价格影响。
```

正确：

```text
根据 Pearson correlation：

price vs revenue:
r = 0.71

p < 0.001

因此，当前数据中价格与收入存在较强正相关。
```

---

## 2.2 Code Before Claim

任何需要计算的数据结论必须：

```text
Generate Code
↓
Execute Code
↓
Inspect Result
↓
Validate Result
↓
Generate Claim
```

禁止：

```text
LLM 直接猜答案
```

---

## 2.3 Statistical Rigor

系统不是简单的 BI 工具。

必须加入统计学能力：

* Descriptive Statistics
* Distribution Analysis
* Correlation
* Hypothesis Testing
* Confidence Interval
* Regression
* ANOVA
* Chi-square Test
* Time Series Analysis
* Outlier Detection
* Missing Value Analysis
* Sampling Analysis
* Statistical Significance
* Effect Size
* Multiple Testing Awareness

对于统计结论，必须尽可能区分：

```text
Correlation
```

和：

```text
Causation
```

禁止 Agent 将相关性直接表述为因果关系。

---

## 3. 项目目标用户

第一阶段针对：

### User 1 — Data Science Student

帮助学生：

* EDA
* ML
* Statistics
* Visualization
* Report

### User 2 — Data Analyst

帮助分析师：

* SQL
* Business Analysis
* Dashboard
* Automated Reports

### User 3 — Researcher

帮助研究人员：

* Statistical Analysis
* Hypothesis Testing
* Regression
* Reproducible Research

### User 4 — ML Engineer

帮助：

* Dataset inspection
* Baseline modeling
* Experimentation
* Model evaluation

---

## 4. 产品核心工作流

用户上传：

```text
sales.csv
```

然后输入：

```text
分析销售额下降的原因，并预测未来30天销售额。
```

系统执行：

```text
User Request
     ↓
Planner Agent
     ↓
Data Understanding
     ↓
Data Profiling
     ↓
EDA
     ↓
Hypothesis Generation
     ↓
Statistical Analysis
     ↓
Feature Engineering
     ↓
Forecasting
     ↓
Model Validation
     ↓
Insight Synthesis
     ↓
Visualization
     ↓
Final Report
```

最终输出：

```text
Executive Summary

Dataset Overview

Data Quality

Key Findings

Statistical Evidence

Visualizations

Predictive Model

Model Performance

Forecast

Limitations

Recommendations

Reproducibility Information
```

---

## 5. Multi-Agent Architecture

采用 Multi-Agent Architecture。

核心 Agent：

## 5.1 Supervisor Agent

负责：

* 理解用户任务
* 创建任务计划
* 分配任务
* 管理 Agent
* 处理失败
* 汇总结果

---

## 5.2 Data Analyst Agent

负责：

* 数据探索
* Data Profiling
* EDA
* 数据质量检查
* 聚合分析

---

## 5.3 Statistician Agent

负责：

* 假设检验
* 置信区间
* 相关分析
* 回归
* ANOVA
* Effect Size
* Statistical Significance

---

## 5.4 ML Scientist Agent

负责：

* Problem Definition
* Feature Engineering
* Train/Test Split
* Baseline
* Model Selection
* Hyperparameter Optimization
* Evaluation

---

## 5.5 Visualization Agent

负责：

* 图表选择
* 图表生成
* 图表解释
* 可视化质量检查

---

## 5.6 Code Agent

负责：

* Python Code Generation
* SQL Generation
* Code Repair
* Code Optimization

---

## 5.7 Critic Agent

负责：

检查：

```text
是否存在数据泄漏？

是否存在统计错误？

是否存在逻辑错误？

是否存在幻觉？

模型是否过拟合？

结论是否有证据？

图表是否误导？
```

---

## 5.8 Report Agent

负责：

生成：

* Markdown Report
* HTML Report
* PDF Report
* Jupyter Notebook
* Executive Summary

---

## 6. Agent Workflow

不要让所有 Agent 自由聊天。

使用明确的 State Machine。

状态：

```text
INITIALIZED
↓
UNDERSTANDING
↓
PLANNING
↓
DATA_PROFILING
↓
ANALYSIS
↓
MODELING
↓
VALIDATION
↓
VISUALIZATION
↓
SYNTHESIS
↓
REPORTING
↓
COMPLETED
```

失败：

```text
FAILED
↓
RECOVERY
↓
RETRY
```

如果连续失败超过阈值：

```text
HUMAN_REVIEW
```

---

## 7. Data Understanding Layer

用户上传文件后自动执行：

```text
File Detection
↓
Schema Detection
↓
Data Type Inference
↓
Missing Value Analysis
↓
Duplicate Detection
↓
Cardinality Analysis
↓
Outlier Detection
↓
Distribution Analysis
```

自动生成：

```text
Dataset Profile
```

包括：

* rows
* columns
* memory
* dtypes
* missing ratio
* unique values
* categorical columns
* numerical columns
* datetime columns
* potential target columns

---

## 8. Data Engine

优先采用：

```text
Pandas
Polars
DuckDB
PyArrow
```

对于：

```text
CSV
Parquet
JSON
```

优先使用 DuckDB/Polars。

DuckDB 适合本地分析型查询，并且是 MIT 开源，可以直接读取 CSV 和 Parquet，因此非常符合"除了 Token 外尽可能零成本"的项目约束。

---

## 9. SQL Agent

Agent 应能够自动生成：

```sql
SELECT
    category,
    SUM(revenue)
FROM sales
GROUP BY category;
```

执行后必须返回：

```text
SQL
↓

Result

↓

Interpretation
```

SQL 必须记录到：

```text
analysis_history
```

---

## 10. Python Execution Engine

建立安全的 Python Sandbox。

Agent 生成：

```python
import pandas as pd

df.groupby("category")["revenue"].sum()
```

系统：

```text
Code
↓
Static Validation
↓
Sandbox
↓
Execute
↓
Capture stdout
↓
Capture stderr
↓
Capture plots
↓
Capture variables
↓
Return Result
```

禁止 Agent 直接访问：

```text
host filesystem
environment variables
SSH
system commands
network
credentials
```

除非明确允许。

---

## 11. Tool System

所有能力都应该工具化。

例如：

```text
load_dataset()

profile_dataset()

describe_data()

run_sql()

run_python()

detect_outliers()

test_normality()

correlation_analysis()

hypothesis_test()

run_regression()

train_model()

evaluate_model()

forecast()

create_visualization()

save_artifact()

generate_report()
```

Agent 不直接执行内部逻辑。

必须：

```text
Agent
↓
Tool
↓
Result
↓
Agent
```

---

## 12. MCP Support

项目必须设计 MCP-compatible architecture。

提供：

```text
Data Science MCP Server
```

Tools：

```text
analyze_dataset
run_sql
run_python
profile_dataset
run_statistics
train_model
create_chart
generate_report
```

MCP 的定位正适合这种架构：它提供 LLM 与外部数据源、工具之间的标准化连接方式。官方规范也明确将其定位为连接 AI 应用与外部数据/工具的开放协议。

未来允许：

```text
Claude
ChatGPT
Cursor
VS Code
Other AI Agents
```

调用 Data Science Agent。

---

## 13. LLM Abstraction Layer

不要把项目写死到单一模型。

设计：

```text
LLMProvider
```

接口：

```python
class LLMProvider:
    async def generate(...)
    async def structured_output(...)
    async def stream(...)
```

支持：

```text
OpenAI
Anthropic
Google
OpenRouter
Ollama
Local Models
```

所有 API Key：

```text
Environment Variables
```

禁止硬编码。

---

## 14. Local Model Support

为了满足免费运行需求，必须支持：

```text
Ollama
```

允许：

```text
Local LLM
```

作为默认免费开发模式。

项目架构必须做到：

```text
Cloud LLM
        \
         → LLM Abstraction
        /
Local LLM
```

---

## 15. Statistical Engine

实现独立：

```text
statistics/
```

模块。

包括：

### Descriptive

```text
mean
median
variance
std
skewness
kurtosis
quantiles
```

### Correlation

```text
Pearson
Spearman
Kendall
```

### Hypothesis Testing

```text
t-test
Welch t-test
Mann-Whitney U
ANOVA
Kruskal-Wallis
Chi-square
Fisher exact
```

### Regression

```text
Linear Regression
Logistic Regression
Ridge
Lasso
Elastic Net
```

---

## 16. Time Series Engine

必须支持：

```text
ADF Test
ACF
PACF
ARIMA
SARIMA
Exponential Smoothing
Prophet
```

同时支持现代模型接口：

```text
TimesFM
Chronos
```

但模型必须采用 Plugin Architecture。

---

## 17. Machine Learning Engine

第一版支持：

### Classification

```text
Logistic Regression
Random Forest
XGBoost
LightGBM
CatBoost
```

### Regression

```text
Linear Regression
Random Forest
XGBoost
LightGBM
CatBoost
```

### Clustering

```text
KMeans
DBSCAN
Hierarchical Clustering
```

---

## 18. Automatic Model Selection

Agent 根据：

```text
dataset size
target type
feature types
missingness
class imbalance
task type
```

自动决定：

```text
candidate models
```

例如：

```text
Binary Classification

↓

Logistic Regression
Random Forest
XGBoost
CatBoost
```

然后：

```text
Cross Validation
↓
Compare
↓
Select
```

---

## 19. Model Evaluation

Classification：

```text
Accuracy
Precision
Recall
F1
ROC-AUC
PR-AUC
Log Loss
Confusion Matrix
```

Regression：

```text
MAE
MSE
RMSE
R²
MAPE
```

Time Series：

```text
MAE
RMSE
MAPE
sMAPE
```

---

## 20. Leakage Detection

必须加入：

```text
Data Leakage Detector
```

自动检查：

```text
Target leakage
Temporal leakage
Train/test contamination
Duplicate leakage
Feature leakage
```

这是整个系统的重要专业壁垒。

---

## 21. Visualization Engine

支持：

```text
Matplotlib
Plotly
Seaborn
```

优先生成：

```text
Histogram
Boxplot
Scatter Plot
Correlation Heatmap
Line Chart
Bar Chart
ROC Curve
Precision-Recall Curve
Confusion Matrix
Feature Importance
SHAP
Residual Plot
ACF/PACF
Forecast Plot
```

---

## 22. Visualization Intelligence

不要让 LLM 随便画图。

设计：

```text
Question
↓
Data Type
↓
Analytical Goal
↓
Chart Recommendation
↓
Chart Generation
↓
Chart Validation
```

例如：

```text
Compare categories
→ Bar Chart

Distribution
→ Histogram

Relationship
→ Scatter Plot

Time
→ Line Chart

Correlation
→ Heatmap
```

---

## 23. Insight Engine

Agent 不能只输出：

```text
The chart shows...
```

而应该生成：

```text
Finding

Evidence

Magnitude

Statistical Significance

Possible Explanation

Limitation
```

例如：

```text
Finding:
Region A has the highest revenue.

Evidence:
Revenue = $2.31M

Region B:
$1.84M

Difference:
25.5%

Limitation:
Revenue difference does not imply that region causes higher performance.
```

---

## 24. Evidence Graph

这是项目的重要创新点。

建立：

```text
Insight
   ↓
Evidence
   ↓
Computation
   ↓
Code
   ↓
Dataset
```

例如：

```text
Insight #003

Revenue increased 18.4%

↓

SQL #17

↓

Query Result

↓

sales.csv

↓

Rows 12401–23122
```

用户点击 Insight：

```text
View Evidence
```

可以看到：

```text
Code
SQL
Result
Chart
Dataset Column
```

---

## 25. Reproducibility

所有分析都必须可复现。

保存：

```text
dataset metadata
code
SQL
parameters
model
random seed
environment
package versions
LLM model
prompt version
timestamp
```

最终生成：

```text
experiment.json
```

以及：

```text
reproduce.sh
```

用户可以重新执行分析。

---

## 26. Analysis Notebook Generation

最终自动生成：

```text
analysis.ipynb
```

结构：

```text
1. Problem Definition

2. Dataset Overview

3. Data Cleaning

4. Exploratory Data Analysis

5. Statistical Analysis

6. Feature Engineering

7. Modeling

8. Evaluation

9. Visualization

10. Insights

11. Limitations

12. Conclusion
```

---

## 27. Report Generation

支持：

```text
Markdown
HTML
PDF
Jupyter Notebook
```

报告应该类似真正 Data Science Consulting Report。

结构：

```text
Executive Summary

1. Business Question

2. Dataset

3. Data Quality

4. EDA

5. Statistical Findings

6. Modeling

7. Model Evaluation

8. Key Insights

9. Recommendations

10. Limitations

11. Reproducibility
```

---

## 28. Frontend

使用：

```text
Next.js
TypeScript
Tailwind CSS
shadcn/ui
Recharts / Plotly
```

UI 必须具有：

```text
Dashboard
Dataset Upload
Chat
Analysis Plan
Agent Trace
Data Preview
Charts
Code
SQL
Model Results
Report
```

---

## 29. Agent Trace UI

用户应该能够看到：

```text
Agent Planning...

✓ Dataset loaded

✓ Data profiling

✓ Missing value analysis

✓ Correlation analysis

● Running regression

○ Generating report
```

点击某一步：

```text
Agent reasoning summary

Tool

Input

Output

Evidence
```

注意：

不要暴露模型内部 chain-of-thought。

只展示：

```text
Concise reasoning summary
```

---

## 30. Backend

使用：

```text
Python
FastAPI
Pydantic
SQLAlchemy
```

架构：

```text
API Layer

↓

Application Layer

↓

Agent Layer

↓

Tool Layer

↓

Data Layer
```

严格遵循：

```text
Separation of Concerns
Dependency Injection
Typed Interfaces
```

---

## 31. Database

默认：

```text
SQLite
```

生产环境可以：

```text
PostgreSQL
```

保存：

```text
users
projects
datasets
analysis_sessions
agent_runs
tool_calls
artifacts
experiments
reports
```

第一版禁止引入不必要的云服务。

---

## 32. Storage

默认：

```text
Local Filesystem
```

结构：

```text
data/
projects/
artifacts/
reports/
models/
logs/
```

未来支持：

```text
S3-compatible storage
```

但 MVP 不需要。

---

## 33. Project Structure

建议：

```text
data-science-agent/
│
├── apps/
│   ├── api/
│   └── web/
│
├── packages/
│   ├── agents/
│   ├── tools/
│   ├── statistics/
│   ├── ml/
│   ├── visualization/
│   ├── execution/
│   ├── datasets/
│   ├── reports/
│   ├── evaluation/
│   └── mcp/
│
├── tests/
│
├── benchmarks/
│
├── examples/
│
├── docs/
│
├── scripts/
│
├── docker/
│
├── .github/
│
├── pyproject.toml
├── docker-compose.yml
├── README.md
├── LICENSE
└── CONTRIBUTING.md
```

---

## 34. Python Architecture

使用：

```text
Python 3.12+
```

依赖管理：

```text
uv
```

代码质量：

```text
Ruff
MyPy
Pytest
Coverage
Pre-commit
```

---

## 35. Agent Framework

Agent orchestration 可以采用：

```text
OpenAI Agents SDK
```

或：

```text
LangGraph
```

不要同时无意义地引入多个 Agent Framework。

如果使用 OpenAI Agents SDK，必须利用：

```text
Agents
Tools
Handoffs
Guardrails
```

构建 Agent Workflow。官方 Python SDK 当前为 MIT License，并明确定位为 multi-agent workflow framework。

如果使用 LangGraph，同样保持 Agent 状态机的显式设计；其开源仓库采用 MIT License。

---

## 36. Security

必须实现：

## File Security

检查：

```text
file size
file type
path traversal
malicious filenames
```

## Code Security

禁止：

```python
os.system()
subprocess
eval()
exec()
socket
```

除非经过安全沙箱。

## Prompt Injection

数据集中的文本可能包含：

```text
Ignore previous instructions...
```

Agent 必须将 Dataset Content 视为：

```text
UNTRUSTED DATA
```

不能将数据中的指令当成系统指令执行。

---

## 37. Guardrail System

输入 Guardrail：

```text
Prompt Injection Detection
```

Tool Guardrail：

```text
Permission Check
```

Output Guardrail：

```text
Unsupported Claim Detection
```

例如：

如果 Agent 说：

```text
X causes Y
```

但只有相关分析：

系统应该改成：

```text
X is associated with Y.
Causal inference is not established.
```

---

## 38. Human-in-the-loop

危险操作必须请求用户确认。

例如：

```text
Delete dataset
```

```text
Overwrite original dataset
```

```text
Run expensive model
```

```text
Execute unrestricted code
```

必须：

```text
Approval Required
```

---

## 39. Cost Control

项目必须支持：

```text
Token Budget
```

例如：

```text
MAX_TOKENS_PER_RUN
MAX_AGENT_STEPS
MAX_TOOL_CALLS
MAX_RETRIES
```

如果超出：

```text
Stop
```

并告诉用户：

```text
Analysis stopped because token/tool budget was reached.
```

---

## 40. Caching

缓存：

```text
dataset profile
SQL result
Python result
embedding
LLM response
model result
```

使用：

```text
Local Cache
```

第一版不使用付费 Redis。

---

## 41. Observability

记录：

```text
agent latency
tool latency
LLM latency
token usage
failure rate
retry count
```

支持：

```text
OpenTelemetry
```

但必须保持可选。

---

## 42. Benchmark System

这是项目申请美国硕士时非常重要的一部分。

不要只写：

```text
Demo works.
```

建立：

```text
Data Science Agent Benchmark
```

测试任务：

```text
EDA tasks
SQL tasks
Statistics tasks
ML tasks
Visualization tasks
Time-series tasks
```

每个任务：

```text
Question
Dataset
Expected Analysis
Expected Metrics
Ground Truth
```

评价：

```text
Task Success Rate

Statistical Accuracy

Code Execution Success

SQL Accuracy

Visualization Quality

Hallucination Rate

Cost

Latency
```

---

## 43. Benchmark Example

任务：

```text
Determine whether average revenue differs between Group A and Group B.
```

Ground Truth：

```text
Welch's t-test
```

Agent Output：

```text
Welch's t-test

p = 0.002

Reject H0
```

评价：

```text
Correct Test = 1

Correct Statistic = 1

Correct p-value = 1

Correct Interpretation = 1
```

---

## 44. Ablation Study

为了提高学术价值，建立：

```text
LLM Only

vs

LLM + Tools

vs

LLM + Tools + Critic

vs

Multi-Agent

vs

Multi-Agent + Evidence
```

比较：

```text
Accuracy
Hallucination
Latency
Cost
```

这部分未来可以直接写成 Research Report。

---

## 45. Research Direction

项目未来可以形成论文方向：

> **Evidence-Grounded Autonomous Data Science Agents**

研究问题：

```text
Can tool-using agents improve statistical reliability?

Can evidence graphs reduce hallucinations?

Does multi-agent verification improve data analysis accuracy?

How much does statistical validation improve LLM-generated analysis?
```

这比单纯：

> "I built a chatbot."

具有明显更高的研究价值。

---

## 46. GitHub Strategy

Repository 必须做到：

```text
Professional README

Architecture Diagram

Demo GIF

Quick Start

Installation

Usage

Examples

Benchmark

Documentation

Contribution Guide

Code of Conduct

Security Policy

License

Roadmap
```

README 第一屏必须回答：

```text
What is it?

Why does it exist?

How does it work?

How do I run it?

Why is it different?
```

---

## 47. Demo Dataset

项目必须自带：

```text
examples/data/
```

包括：

```text
sales.csv
customer_churn.csv
financial.csv
timeseries.csv
marketing.csv
```

数据集必须使用：

```text
Public Domain
CC0
Compatible Open Data License
```

不得上传版权不明确的数据。

---

## 48. Example Demo

README 中必须提供：

```text
Upload sales.csv
```

输入：

```text
Analyze why revenue declined and forecast next 30 days.
```

展示：

```text
Planning
↓
EDA
↓
Statistical Analysis
↓
Forecast
↓
Validation
↓
Report
```

最终展示完整结果。

---

## 49. CI/CD

GitHub Actions：

```text
Lint
↓
Type Check
↓
Unit Tests
↓
Integration Tests
↓
Security Scan
↓
Build
```

每次 PR 自动执行。

---

## 50. Testing

至少包含：

## Unit Tests

```text
statistics
tools
data loaders
validators
```

## Integration Tests

```text
Agent → Tool → Result
```

## End-to-End Tests

```text
Upload Dataset
↓
Ask Question
↓
Agent Analysis
↓
Report
```

## Security Tests

```text
Prompt Injection
Path Traversal
Malicious File
Code Injection
```

---

## 51. Documentation

使用：

```text
MkDocs
```

文档：

```text
Getting Started

Architecture

Agent System

Tools

Statistics

ML

MCP

Security

Benchmarks

Development

Contribution
```

---

## 52. Licensing

项目主代码：

```text
MIT License
```

对于第三方数据集必须单独记录：

```text
dataset source
license
citation
```

第三方依赖必须建立：

```text
THIRD_PARTY_LICENSES.md
```

---

## 53. Docker

提供：

```text
docker compose up
```

启动：

```text
Frontend
Backend
Database
```

同时必须提供完全本地运行：

```text
uv run ...
npm run ...
```

不允许用户必须购买云服务才能运行。

---

## 54. Free-First Architecture

默认：

```text
Local Machine
+
Open Source Software
+
Local Database
+
Local Storage
+
Ollama
```

可选：

```text
OpenAI API
Anthropic API
Google API
```

但这些仅用于：

```text
LLM Token
```

不能强制用户购买：

```text
Cloud GPU
Paid Database
Paid Vector DB
Paid Observability
Paid Hosting
```

---

## 55. Product Roadmap

## Phase 1 — MVP

实现：

```text
CSV Upload

Data Profiling

Chat

Python Execution

SQL

EDA

Basic Statistics

Visualization

Report
```

---

## Phase 2 — Agent

增加：

```text
Planner Agent

Analyst Agent

Statistician Agent

Critic Agent

Report Agent
```

---

## Phase 3 — ML

增加：

```text
AutoML

Feature Engineering

Model Selection

Model Evaluation

Explainability
```

---

## Phase 4 — Advanced

增加：

```text
Time Series

Causal Analysis

Experiment Tracking

Evidence Graph

Benchmark
```

---

## Phase 5 — Ecosystem

增加：

```text
MCP Server

Plugin System

CLI

Python SDK

VS Code Extension

Jupyter Integration
```

---

## 56. CLI

提供：

```bash
dsa analyze data.csv
```

例如：

```bash
dsa analyze sales.csv \
  --task "Analyze revenue decline"
```

输出：

```text
✓ Dataset loaded
✓ Data profiling
✓ Analysis plan
✓ Statistical analysis
✓ Visualization
✓ Report generated
```

---

## 57. Python SDK

提供：

```python
from data_science_agent import Agent

agent = Agent()

result = agent.analyze(
    dataset="sales.csv",
    task="Analyze revenue decline"
)

print(result.summary)
```

---

## 58. API

提供：

```text
POST /datasets

POST /analysis

GET /analysis/{id}

GET /analysis/{id}/events

GET /analysis/{id}/report

GET /analysis/{id}/artifacts
```

支持：

```text
SSE
```

实现实时 Agent Event Streaming。

---

## 59. Event Schema

统一：

```json
{
  "event": "tool_call",
  "agent": "statistician",
  "tool": "run_hypothesis_test",
  "status": "completed",
  "timestamp": "...",
  "duration_ms": 532
}
```

---

## 60. Agent Memory

实现三种 Memory：

### Session Memory

当前分析任务。

### Project Memory

项目级上下文：

```text
dataset
previous analysis
user preferences
```

### Long-term Memory

可选。

第一版不要过度复杂化。

---

## 61. Prompt Architecture

不要将所有 Prompt 写在代码中。

使用：

```text
prompts/
```

例如：

```text
planner.yaml
analyst.yaml
statistician.yaml
ml.yaml
critic.yaml
report.yaml
```

每个 Prompt 必须：

```text
version
description
variables
expected_output
```

---

## 62. Structured Output

Agent 必须尽可能输出 Pydantic Schema。

例如：

```python
class AnalysisPlan(BaseModel):
    objective: str
    steps: list[AnalysisStep]
    required_tools: list[str]
    expected_outputs: list[str]
```

禁止大量依赖：

```text
free-form text parsing
```

---

## 63. Error Recovery

如果：

```text
Python execution failed
```

Agent：

```text
Read Error
↓
Diagnose
↓
Repair Code
↓
Retry
```

最大：

```text
3 retries
```

否则：

```text
Human Review
```

---

## 64. Quality Gate

最终报告生成前必须经过：

```text
Data Quality Check

Statistical Check

Code Check

Model Check

Evidence Check

Hallucination Check
```

只有：

```text
ALL PASSED
```

才能：

```text
FINAL REPORT
```

---

## 65. Important Anti-Patterns

禁止：

```text
❌ 一个巨大 Agent

❌ 一个巨大 Prompt

❌ LLM 直接生成答案

❌ LLM 直接执行 Shell

❌ 没有验证的统计结论

❌ 没有 Benchmark

❌ 没有测试

❌ 把所有东西放在一个 Python 文件

❌ 强制使用付费云服务

❌ API Key 写入 GitHub

❌ 只做漂亮 UI

❌ 只做 Chatbot
```

---

## 66. MVP 成功标准

MVP 必须能够完成以下任务：

```text
User uploads CSV

↓

Agent understands dataset

↓

Agent generates analysis plan

↓

Agent performs EDA

↓

Agent executes statistical analysis

↓

Agent generates visualization

↓

Agent validates result

↓

Agent produces evidence-grounded insights

↓

Agent generates report
```

整个过程必须真实运行。

禁止使用：

```text
Fake Data
Fake API
Mock Result
Hard-coded Answer
```

---

## 67. Final Acceptance Test

使用：

```text
Titanic Dataset
```

执行：

```text
Analyze survival patterns and build a predictive model.
```

系统应该自动：

```text
1. Load dataset

2. Profile dataset

3. Detect missing values

4. Identify target

5. Perform EDA

6. Generate hypotheses

7. Perform statistical tests

8. Create features

9. Train baseline models

10. Compare models

11. Evaluate

12. Explain important features

13. Generate charts

14. Critique conclusions

15. Generate final report

16. Generate notebook

17. Save reproducibility metadata
```

---

## 68. Developer Working Rules

开发过程中必须遵循：

### Rule 1

先设计：

```text
Architecture
```

再写代码。

### Rule 2

优先：

```text
Simple
Typed
Testable
Modular
```

### Rule 3

不要为了"看起来高级"增加不必要的 Agent。

### Rule 4

所有 AI 输出必须可以追溯到：

```text
Tool
Result
Evidence
```

### Rule 5

所有重要功能必须有测试。

### Rule 6

所有第三方依赖必须检查 License。

### Rule 7

所有 API Key 必须通过 Environment Variable。

### Rule 8

每完成一个阶段都必须运行测试。

### Rule 9

不要一次生成整个项目的所有代码。

采用：

```text
Architecture
→
Scaffold
→
Core Engine
→
Tools
→
Agents
→
API
→
Frontend
→
Testing
→
Benchmark
→
Documentation
```

逐阶段开发。

---

## 69. First Development Task

现在不要立即编写整个项目。

第一阶段只完成：

```text
1. Product Architecture

2. Repository Structure

3. Technology Stack

4. Domain Models

5. Agent State Model

6. Tool Interface

7. LLM Provider Interface

8. Execution Sandbox Interface

9. Database Schema

10. API Specification

11. Frontend Information Architecture

12. Development Roadmap
```

然后输出：

```text
Architecture Diagram
Repository Tree
Database ERD
Agent State Diagram
Tool Architecture
API Specification
MVP Milestones
```

确认架构完整后，再开始写代码。

---

## 70. Ultimate Product Vision

最终 Data Science Agent 应该成为：

> **An open-source autonomous data science workspace that transforms natural-language questions into reproducible, statistically rigorous, evidence-grounded data science workflows.**

它不是：

```text
Chatbot
```

而是：

```text
AI Data Scientist
```

完整能力：

```text
Understand
    ↓
Plan
    ↓
Explore
    ↓
Analyze
    ↓
Model
    ↓
Validate
    ↓
Explain
    ↓
Visualize
    ↓
Report
    ↓
Reproduce
```

最终目标：

```text
Data
+
Question
        ↓
Data Science Agent
        ↓
Reproducible Analysis
+
Statistical Evidence
+
ML Model
+
Visualization
+
Research Report
```

请始终优先保证：

```text
Correctness
>
Reproducibility
>
Security
>
Evidence
>
Maintainability
>
Performance
>
UI
```

不要为了 Demo 效果牺牲统计正确性和工程可靠性。
