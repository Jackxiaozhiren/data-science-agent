# Open-source Growth Plan

This plan focuses on converting existing engineering depth into discovery, trust, trial, and sharing.

## Positioning

Primary message:

> **The AI data scientist that shows its work.**

Supporting category:

> Verifiable, reproducible AI data science with claim-level evidence.

Avoid competing only on "chat with your CSV". The differentiator is inspectability: claim → evidence → computation → dataset.

## P0 — Repository conversion

- [x] Productize the README first screen around one clear promise.
- [x] Remove headline use of deterministic `100/100` benchmark scores without model context.
- [x] Reframe the current public table as a reproducible evaluation registry until real-model comparisons exist.
- [ ] Set GitHub repository About description.
- [ ] Set repository website to the best live docs/demo URL.
- [ ] Add GitHub topics for discovery.
- [ ] Add/refresh a 1280×640 social preview image.
- [ ] Review open Dependabot PRs and merge/close/group them where appropriate.

### Recommended GitHub About description

```text
Evidence-grounded AI data science agent for CSV, SQL, statistics and ML. Ask questions and get reproducible reports with claim-level provenance.
```

### Recommended topics

```text
ai-agent
data-science
data-analysis
data-analyst
llm
langgraph
machine-learning
statistics
sql
duckdb
polars
python
mcp
reproducibility
data-visualization
agentic-ai
```

## P1 — Benchmark credibility

The next evaluation milestone should prioritize believable, inspectable evidence over a perfect headline score.

Publish the same frozen benchmark with:

1. DSA + a real LLM.
2. Vanilla LLM + Python/tool execution.
3. LLM-only baseline.
4. DSA without the evidence critic.

For every run, preserve provider/model, configuration, commit SHA, evaluator version, token usage, cost, latency, seed where supported, and raw artifacts.

Success criterion: a technically skeptical reader can reproduce or audit the comparison without trusting marketing copy.

## P1 — One-click trial

Reduce the gap between "I found this repo" and "I saw it work".

Preferred options:

- hosted lightweight web playground;
- Hugging Face Space;
- Streamlit deployment;
- GitHub Codespaces configuration.

The demo should optimize for one wow moment rather than feature coverage:

```text
Upload CSV
→ ask one business question
→ see chart/statistical result
→ inspect supporting evidence
→ download reproducible report
```

## P1 — Real demo media

Create a 20–30 second real product capture rather than only a conceptual animation.

Show:

1. a real dataset;
2. one natural-language question;
3. tool execution;
4. one useful chart/statistical result;
5. the evidence trail;
6. generated report/reproduction artifacts.

Keep it short enough to understand without audio.

## P1 — Case-study conversion

Promote three case studies near the top of the README or project site.

Recommended framing:

| User question | Result | Proof |
|---|---|---|
| What drives sales? | Regression + visualization | Open report |
| Who will churn? | Classification + feature importance | Open notebook |
| What happens next month? | Forecast + uncertainty | Reproduce run |

The goal is to make visitors map the examples to their own data problems.

## P2 — Launch content

Lead with a problem/opinion rather than "I built an agent".

Recommended article/title:

> **Why AI data analysts should show their work**

Structure:

1. show an attractive but unsupported AI data claim;
2. explain why generated prose is insufficient for data science;
3. show DSA's claim → evidence → computation chain;
4. reproduce the analysis;
5. discuss limitations honestly;
6. link to the live demo and GitHub repo.

## P2 — Distribution

Once the real-model evaluation and demo are public, coordinate one launch window across:

- Hacker News;
- relevant data-science / machine-learning communities;
- LinkedIn / X;
- LangGraph / agent communities;
- curated `awesome-*` repositories where contribution rules permit it.

Drive all posts toward the same simple path:

> 20-second demo → try it → inspect evidence → GitHub star.

## Release strategy

Prefer fewer releases with user-visible reasons to care.

A strong next release theme would be:

> **Real-model evaluation + live demo + verifiable case studies**

Release notes should lead with user outcomes, not repository-maintenance details.

## Success metrics

Track weekly:

- GitHub unique visitors;
- visitor → star conversion;
- clones;
- PyPI downloads;
- live-demo starts and completions;
- case-study clicks;
- external referrers;
- issues/discussions from new users;
- repeat contributors.

The primary near-term question is not "How many features shipped?" It is:

> **Can a new visitor understand, trust, and try DSA in under five minutes?**
