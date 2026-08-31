# Early Adopter Guide — Data Science Agent (V4.3 W10 §74)

> **Spec:** V4.3 W10 §74 — `docs/v4_3/EARLY_ADOPTER_GUIDE.md`, targeted at Data Science
> Students, Data Analysts, Researchers, ML Engineers, AI Engineers.
> **Honesty note:** this project is in the V4.3 benchmarking track; the *DataSciBench*
> external evaluation exists as an execution pipeline with **no score yet** (gated GT).
> Internal benchmarks are 50/50 and 100/100 on closed tasks. Nothing here is marketing hyperbole.
> **Date:** 2026-08-31 · Version in this branch: **4.2.10** (published lineage has a separate
> v4.3.0 release — see `docs/v4_3/SUPPLY_CHAIN_SECURITY.md` §0).

---

## Who this is for

You do data work and you want an agent that:

- turns a **natural-language question** about a dataset into a **reproducible analysis**,
- grounds every insight in **evidence** (SQL results, statistics tests, charts, model outputs),
- keeps a **tool trajectory** you can audit and replay.

That's what this is. Whether you're a student, analyst, or engineer, the fastest path to
value is: install → run a demo → point it at *your* CSV → inspect the evidence.

## 1. Install (≈2–5 min)

```bash
# Option A — source (full dev surface; recommended first)
git clone https://github.com/Jackxiaozhiren/data-science-agent.git
cd data-science-agent
uv sync --dev
.venv/bin/dsa doctor --json     # expects status "warn" on LLM (no key needed for deterministic run)

# Option B — PyPI (self-contained wheel)
pip install jack-data-science-agent
```

**No LLM API key required for the deterministic pipeline** — the agent plans, profiles,
runs stats, and writes an evidence-grounded report locally. Options for a real LLM provider
are documented in the project docs; the default path works out-of-the-box.

## 2. First success (≈30 s)

```bash
.venv/bin/dsa demo            # runs a sales analysis end-to-end, writes artifacts/
```

Or use the SDK directly on your file:

```python
from data_science_agent import Agent
r = Agent().analyze_sync("my_data.csv", "What drives revenue by region and category?")
print(r.status, len(r.evidence), r.report[:300])
```

## 3. What you get back (evidence-grounded, not just text)

Every run produces:

- **report.md** — plain-English analysis with charts embedded,
- **evidence.json** — each claim maps to a tool result (confidence, source_type, source_id),
- **tool_calls.json** — the full trajectory (SQL, stats, model, viz) for audit/replay,
- **insights.json** — findings linked to their backing evidence ids.

Check a sample: `case-studies/01-sales/outputs/` (real Agent run, committed).

## 4. Try it on your own data

```bash
.venv/bin/dsa analyze --dataset your_data.csv --task "your natural language question"
```

Tips that improve results:

- **Cleanest win:** tabular CSV/Excel with clear column names.
- **Closed questions first:** "correlate A and B", "profile missing values", "forecast next 30"
  — exact-metric answers work best. Open "write me a business review" questions still complete,
  but the statistical claims are what get evidence.
- **Evidence ≠ magic:** the agent labels statistical outputs as `pending` validation, not
  auto-`valid`. Treat low-confidence numbers as your signal to look closer, exactly as you
  would with a colleague's draft.

## 5. Known limitations (read before you file a bug)

- **Deterministic pipeline uses no LLM** by default; richer reasoning requires configuring a
  provider. Some tool calls fail and are *preserved* in `tool_calls.json` (that's intentional —
  honest failure, not silent).
- **External benchmark score: not yet published** (gated ground truth). Don't judge the
  project on a number that doesn't exist yet (V4.3 §110: honest reporting over fake scores).
- **No hosted SaaS / team features** — this is a local/self-hosted tool today.
- **Latest published release on PyPI/GitHub is 4.3.0** (published lineage); this branch's
  docs describe the 4.2.10 core. Both share the same architecture.

## 6. Report back (this is how the project grows)

Open an issue via the **User feedback** template
(`.github/ISSUE_TEMPLATE/user-feedback.yml`, label `feedback`) — it asks about your use case,
dataset type, install experience, what worked/failed, evidence usefulness, and feature gaps.
**Do not upload sensitive datasets** — describe them.

Your first genuine issue/PR is, honestly, the single most valuable signal the project can get
(V4.3 §76). Even a one-line "I tried X, it failed because Y" is more useful than a star.

## 7. Further reading

- Getting started: `docs/getting-started.md`
- Architecture: `docs/architecture.md`
- Evidence system: `docs/evidence.md`
- Real-world case studies: `case-studies/README.md`
- Reproduction: `docs/reproducibility.md` + `research/v4_3/reproducibility/README.md`