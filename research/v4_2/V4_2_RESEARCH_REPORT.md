# V4.2 Research Report — W11 §61 (RQ1-5)

> **W11 §61 — Research Evidence** — Candidate RQs, proper experimental design for causal claims (§61)  
> **Date:** 2026-08-22  
> **Commit:** `b79610d` (v4.1.1)  
> **Spec:** `DATA_SCIENCE_AGENT_V4_2.md` §61-63

---

## 1. Research Questions (Candidate per §61)

| RQ | Question | Type | Status |
|----|----------|------|--------|
| **RQ1** | Does benchmark performance correlate with real-world task success? | Correlation | **Partial** — `Benchmark 1.00` (closed) vs `Real 1.00` (open `COMPLETED`) — definition drift, see `research/v4_2/benchmark_vs_real_world.md` §48 (no, not directly) |
| **RQ2** | What failure modes emerge only on real-world datasets? | Exploratory | **10 failures classified** in `benchmark_vs_real_world.md` §49 — `1` covered / `6` underrepresented / `3` missing |
| **RQ3** | Does evidence grounding improve user trust? | Human | **Not measured** — would need `human-eval` 11/100 `Kappa` (V3) vs `CS01` with/without evidence — not yet run for V4.2 |
| **RQ4** | How much developer friction does an AI data science platform introduce? | Usability | **Low** — `Time to First Success 3-5s`, `Manual Intervention 0/3` (W5), `Friction Low` for 10 steps (W5 §38) |
| **RQ5** | Does modular plugin architecture improve extensibility? | Architecture | **Anecdotal** — `dsa-time-series 1.0.0` added with `1.05×` overhead (§53) and `24` tests, no `Core` crash (isolation) — not causal, needs `A/B` with/without plugin |

**All causal conclusions require proper design (§61) — below is correlational, not causal.**

---

## 2. Methods

### 2.1 Datasets

- **Benchmark:** `benchmarks/v2` 30 synthetic CC0 (seed 42) + `benchmarks/ds-agent-benchmark` 20 (8770 rows) — `catalog.json` 0.3.0
- **Case Studies:** `case-studies/01-sales` (500), `02-churn` (synthetic) — real Agent, `case-studies/README.md`

### 2.2 Metrics (§62)

Per case study (§62): `analysis success / execution time / tool count / retry count / token usage / evidence coverage / human intervention / report quality / reproducibility` — see `case-studies/01-sales/outputs/summary.json`:

- **CS01:** `COMPLETED` `1.33s` `6 tool_calls` `0 retry` `0 token (stub)` `evidence 6/6` `0 intervention` `report 3890` `repro via artifacts/`
- **CS02:** `COMPLETED` `0.05s` `7 tool_calls` `0 retry` `3 evidence` `0 intervention`

### 2.3 Human Feedback (§63)

**If real users exist:** Would collect `task usefulness / accuracy / clarity / trust / ease / time saved` (§63).

**Current:** **No real users** — per §63 *禁止伪造*, use `developer validation` / `case study validation` / `internal evaluation` (honest, §65 no fabricated).

- **Internal validation:** `EXTERNAL_VALIDATION.md` `3/3` `High` clarity, `case-studies` `2/2` Verified.
- **No fabricated:** Per §64 — `0` `users`/`stars`/`time saved`.

---

## 3. Results

### 3.1 RQ1 — Benchmark vs Real (§47-48)

**Result:** **No correlation** — `Benchmark 50/50 @1.00` (closed `SELECT`) vs `Real 2/2 @1.00` (`COMPLETED` open) — different `success` def, `Likert` (§48 table). `Benchmark` is **regression unit**, not `business usefulness` (§6 `Does this actually solve my data science problem?`).

**Evidence:** `research/v4_2/benchmark_vs_real_world.md` §48 (7 dims), `QUANTITATIVE_CLAIMS.md`.

### 3.2 RQ2 — Failure Modes (§49)

**Result:** `10` real-world failures (§49) — `1` `Benchmark-covered` (correlation), `6` `underrepresented` (causal, imbalanced, missing_heavy, mixed, financial, wide_table), `3` `missing` (open question, titanic target, marketing ROI). **Gap list** 12 candidates for `v3 0.4.0` (Long-tail 4, Open 4, etc.) — **do not modify now** per §50.

### 3.3 RQ3 — Evidence Grounding & Trust (§61)

**Not measured for V4.2** — would need `A/B` with/without `Evidence` + `human-eval` `Kappa` (V3 `11/100`). Current `CS01` has `6` evidence `confidence 0.7-0.9` but no `trust` Likert.

### 3.4 RQ4 — Friction (§38, W5)

**Result:** **Low friction** — `Time to First Success 3s` (macOS) / `44s` total `10/10` steps `0 manual` (§38). `Friction` `Low` for `Install`/`LLM`/`Plugin`/`Jupyter` (W5 §7).

### 3.5 RQ5 — Plugin Extensibility (§27, §53)

**Anecdotal:** `dsa-time-series` adds `forecast/backtest/metrics/viz/evidence` with `1.05×` overhead ( `performance.md` §53 ) and `24` tests, **no Core crash** (isolation `load_plugin_isolated`).

---

## 4. Limitations

- **N=2** case studies (pilot) — not `8` fully verified (W4 §33) — limited power for RQ1/2.
- **Synthetic datasets** (seed 42) — not real `Business Analytics` with `dirty` data (W4 §29).
- **No human study** for RQ3 — stub LLM, `Cloud $0`, no `trust` Likert.
- **No causal design** for RQ3/RQ5 — correlational, not `RCT`.

---

## 5. Next Research

- **W4 Full:** Execute `CS03-08` fully (8 verified) → power for RQ1/2.
- **W5 External:** `3` envs already `3/3` — add `human` `Kappa` for RQ3.
- **W8 Full:** Run `12` benchmark candidates after evidence (per `benchmark_vs_real_world.md` §5).

---

## 6. No Fabricated Adoption (§64)

Per §64 — `0` `users/downloads/stars` fabricated — only `pytest 257`/`SBOM 192`/`benchmark 1.00`/`case-studies 2`/`external 3/3`.

---

*Generated: 2026-08-22 live — `b79610d` — companion to `research/v4_2/benchmark_vs_real_world.md` + `case-studies/` + `docs/v4_2/EXTERNAL_VALIDATION.md`.*
