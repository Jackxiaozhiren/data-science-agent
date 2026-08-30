# Data Science Agent Product Tour

> **Verified interactive-style tour, not a live hosted analysis service.**
>
> This page walks through repository outputs produced by real DSA runs. It does not submit new datasets or call a live model/API. The separate [Hosted Demo](hosted-demo.md) page documents the requirements for a future real-time public deployment.

## What DSA is designed to show

Data Science Agent is built around a simple requirement: an AI data-science claim should remain traceable to the computation and dataset that produced it.

```text
Question
  ↓
Plan and tool calls
  ↓
Statistics / SQL / ML / visualization
  ↓
Evidence
  ↓
Claim
  ↓
Reproducible report and artifacts
```

A completed run can produce `report.md`, `experiment.json`, `evidence_graph.json`, `analysis.ipynb`, and `reproduce.sh` so the result is inspectable instead of being only chat output.

## Start with three verified workflows

The repository contains eight verified end-to-end case studies. These three are the clearest entry points.

### 1. Sales analytics — shortest end-to-end path

**Question:** Which regional and category patterns matter for revenue, and what evidence supports the conclusion?

The verified CS01 run completed in **1.33 s**, produced **6 evidence items**, **6 tool calls**, and **5 artifacts**. It demonstrates profiling, correlation analysis, SQL aggregation, a statistical test, visualization, evidence capture, and report generation on a versioned synthetic dataset.

[Open CS01 Sales on GitHub](https://github.com/Jackxiaozhiren/data-science-agent/tree/main/case-studies/01-sales){ .md-button .md-button--primary }

### 2. Time-series forecasting — evidence plus visible failure recovery

**Question:** What are the next 30 values, and how well does the baseline forecast perform?

The verified CS03 run completed in about **1.28 s** with **5 evidence items**. The case intentionally keeps recorded tool failures visible instead of removing them from the demo record, so the workflow also shows capability boundaries and recovery behavior.

[Open CS03 Time Series on GitHub](https://github.com/Jackxiaozhiren/data-science-agent/tree/main/case-studies/03-time-series){ .md-button }

### 3. ML classification — model evaluation in the same provenance trail

**Question:** Can DSA train, evaluate, and explain an imbalanced classifier?

The verified CS08 run completed in about **0.11 s** with **5 evidence items**. It demonstrates classification, evaluation, feature importance, evidence capture, and explicit limitations in one reproducibility-oriented workflow.

[Open CS08 Classification on GitHub](https://github.com/Jackxiaozhiren/data-science-agent/tree/main/case-studies/08-classification){ .md-button }

## What the eight-case suite covers

| Case | Domain | Verified state | Evidence | Main purpose |
|---|---|---:|---:|---|
| CS01 | Business analytics | `COMPLETED` | 6 | SQL + statistics + evidence + report |
| CS02 | Customer analytics | `COMPLETED` | 3 | Churn analysis with failed tools retained |
| CS03 | Forecasting | `COMPLETED` | 5 | Temporal workflow + reproducible outputs |
| CS04 | Marketing | `COMPLETED` | 5 | Clean end-to-end run |
| CS05 | Financial data | `COMPLETED` | 5 | Time-series analysis + explicit limitations |
| CS06 | Public statistics | `COMPLETED` | 3 | Statistical fallback behavior |
| CS07 | Data quality | `COMPLETED` | 3 | Profiling / quality investigation |
| CS08 | Machine learning | `COMPLETED` | 5 | Classification + feature importance |

[Browse all eight case studies](https://github.com/Jackxiaozhiren/data-science-agent/tree/main/case-studies){ .md-button .md-button--primary }

## What counts as verified here

A case is only treated as verified when it runs from a clean environment, executes the real agent rather than mocked output, produces real tool calls and evidence, generates a report and reproduction package, and keeps tool errors and limitations visible.

The current eight-case suite uses synthetic datasets generated with a fixed seed to avoid unclear third-party redistribution rights. These examples are product-behavior and reproducibility demonstrations; they are **not** independent real-LLM leaderboard results.

## Inspect the evidence path

For the flagship sales case, the recorded trajectory includes:

1. dataset profiling;
2. correlation analysis;
3. SQL aggregation;
4. a statistical test;
5. visualization;
6. evidence and report generation.

Each evidence item links a claim to a source/tool call and ultimately to the hashed input dataset. The repository keeps the generated report and evidence files under the corresponding case-study output directories.

[Inspect CS01 evidence and outputs](https://github.com/Jackxiaozhiren/data-science-agent/tree/main/case-studies/01-sales/outputs){ .md-button }

## Run it yourself

Install the published package:

```bash
pip install jack-data-science-agent
```

Then run the built-in demo:

```bash
dsa demo
```

Or analyze a local CSV:

```bash
dsa analyze sales.csv \
  --task "Which factors explain revenue, and are the effects statistically significant?"
```

Python **3.12+** is required.

## Product-tour boundary

This static tour is intentionally narrower than a live hosted DSA service:

- it does **not** accept file uploads;
- it does **not** execute a new analysis in the browser;
- it does **not** require or expose model-provider credentials;
- it only presents repository artifacts from already verified runs.

For the architecture and security requirements of a true public Web + API deployment, see [Hosted Demo Deployment](hosted-demo.md).

---

**Next:** [Install DSA](getting-started.md) · [Evaluation](evaluation.md) · [Research & limitations](research.md) · [GitHub repository](https://github.com/Jackxiaozhiren/data-science-agent)
