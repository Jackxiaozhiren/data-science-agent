# Feedback Template (V4.3 W8 §76)

> Fill this in and return it (as a file or pasted text) together with one
> machine-readable JSON per task set matching [RESULTS_SCHEMA.json](RESULTS_SCHEMA.json).
> You may remain pseudonymous; do not include secrets or private data in the CSV
> you used — describe it, don't attach it.

---

## Reviewer context

- Reviewer ID / pseudonym:
- Date(s) of review:
- Background (one line, e.g. "data analyst, 5 years"):
- Install path used: ☐ PyPI `pip install` ☐ source clone
- Package version reviewed (`pip show jack-data-science-agent`):
- OS + Python version:

## Environment notes

- Anything that surprised you during install/setup:
- Did any task fail to run? ☐ No ☐ Yes → task #, exact command, error output:

## Per-task scores (1-5, from RUBRIC.md; use `n/a` only per rubric rules)

| Task | Correctness | Statistical Validity | Evidence Quality | Clarity | Uncertainty | Usefulness | Trust |
|------|------------:|---------------------:|-----------------:|--------:|------------:|-----------:|------:|
| T1 doctor smoke | | | | | | | |
| T2 demo | | | | | | | |
| T3 own dataset | | | | | | | |
| T4 evidence trace | | | | | | | |
| T5 reproduction | | | | | | | |
| T6 provenance (if attempted) | | | | | | | |

## Written answers

1. **T3 — your dataset & question** (describe, do not attach the file):
2. **What the agent got right:**
3. **What it got wrong or missed (be specific):**
4. **Evidence & trajectory:** could you trace a report claim to its computation? Example:
5. **Reproduction (T5):** did the second run match the first? Any divergence:
6. **Uncertainty honesty:** did the report surface its own limitations/failures?
7. **Most valuable capability:**
8. **Biggest weakness:**
9. **One change that would most increase your trust:**
10. **Would you use/recommend this tool? Why / why not:**

## Free-form notes

(anything else, including raw command outputs you want to preserve)

---

*Submission checklist:* ☐ this template filled ☐ JSON result file(s) valid against
`RESULTS_SCHEMA.json` ☐ no private data attached.
