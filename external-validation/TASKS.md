# TASKS — External Reviewer Tasks (V4.3 W8 §76-78)

> Complete these **before** reading any internal benchmark results in the
> repository (`benchmarks/ds-agent-benchmark/results/`, `research/v4_3/`) —
> blind-review instruction (§77). Score each task with [RUBRIC.md](RUBRIC.md)
> as you go; submit via [FEEDBACK_TEMPLATE.md](FEEDBACK_TEMPLATE.md).

| # | Task | Time | What you keep |
|---|------|------|---------------|
| T1 | Install + doctor smoke | 5-10 min | installed version, `dsa doctor` output |
| T2 | Run the demo | 5 min | demo report + evidence produced |
| T3 | Run your own analysis | 15-30 min | report, trajectory, evidence for *your* CSV |
| T4 | Inspect evidence & trajectory | 10 min | notes on traceability |
| T5 | Reproduce a run | 10-20 min | comparison notes (same result twice?) |
| T6 | Verify package provenance | 10 min | verification command output |

You may stop after any task; partial feedback is welcome. Say explicitly if a task
failed on your machine — **environment failures are results, not noise**.

---

## T1 — Install + smoke (prereq: [INSTALL.md](INSTALL.md))

1. Install per INSTALL.md; record the `pip show` version line.
2. Run `dsa doctor`. Save the output.
3. Score dimensions: *Correctness* (does the tool behave sanely?), *Clarity*
   (are the diagnostics understandable?), *Trust* (would you proceed?).

## T2 — Guided demo

```bash
dsa demo
```

1. Open the report it produces (path is printed at the end).
2. Check: does every number/claim in the report point at something you could
   re-derive (a table, a statistic, a chart)?
3. Score: *Correctness*, *Evidence Quality*, *Clarity*, *Uncertainty*
   (does the report state its limits?).

## T3 — Your own dataset (the core task)

1. Bring **your own CSV** (any tabular data you know well — you are the ground
   truth here). 100-10,000 rows is comfortable.
2. Ask it a question you already know the answer to (e.g. "which category has the
   highest average value of X?"). Natural language is the intended interface.
3. Read the produced report and tool trajectory.
4. Score against your own knowledge: *Correctness*, *Statistical Validity*
   (right test/tool for the question?), *Evidence Quality*, *Usefulness*
   (would this save you time?).

## T4 — Evidence & trajectory inspection

1. Locate the run artifacts (report, tool calls, evidence records — paths are
   printed by the CLI).
2. Pick one claim from the report; trace it back to the tool call and data step
   that produced it.
3. Score: *Evidence Quality*, *Trust*.

## T5 — Reproduction

1. Re-run the same task/command from T2 or T3 in a fresh working directory.
2. Compare the two reports: same analytical results? Same numbers?
3. Score: *Correctness*, *Trust*; note any divergence — deterministic pipelines
   should not drift without an LLM key.

## T6 — Provenance verification (optional, needs `gh` + `cosign` optional)

Follow the maintainer-documented procedure in the repository:
`docs/security/VERIFY_RELEASE.md` (PyPI publish-attestation path). Record whether
the published wheel's digest matches its PyPI attestation.
Score: *Trust*. If any step fails, capture the exact command + output — that is a
valuable finding, not a personal failure.
