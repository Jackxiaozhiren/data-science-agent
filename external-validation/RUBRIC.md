# RUBRIC — Human Review Dimensions (V4.3 W8 §78)

> Seven dimensions (§78). Every dimension is scored 1-5 (whole numbers).
> Score what **you** observed on **your** machine with **your** data — there is no
> "correct" score. Rate before reading internal benchmark results (blind, §77).

## Dimensions

### 1. Correctness
Are the analytical results right — by your own knowledge of your data?
- **5** All checked results match my own ground truth.
- **3** Mostly right; some minor errors I could identify.
- **1** Results were wrong or unverifiable.
- *n/a* — only if you had no way to know (say so explicitly rather than guessing).

### 2. Statistical Validity
Are the right methods applied to the right questions (test choice, assumptions, effect reporting)?
- **5** Method choices defensible; assumptions stated or checked.
- **3** Reasonable choices with notable gaps (e.g. no assumption discussion).
- **1** Misapplied methods (e.g. wrong test, misread correlation as causation).

### 3. Evidence Quality
Can every claim be traced to a concrete artifact (table, statistic, chart, tool call)?
- **5** Every claim traceable; artifacts complete and inspectable.
- **3** Most claims traceable; some leaps.
- **1** Claims without visible grounding.

### 4. Clarity
Is the output understandable to a data practitioner?
- **5** Clear, well-structured, readable without help.
- **3** Understandable with effort.
- **1** Confusing or misleading structure/wording.

### 5. Uncertainty
Does the report state confidence, limitations, and failure cases honestly?
- **5** Limitations + uncertainty surfaced proactively (including tool failures).
- **3** Some caveats; missing important ones.
- **1** Overconfident; failures hidden.

### 6. Usefulness
Would this save you real time on your own work?
- **5** Yes — a usable draft I would keep and refine.
- **3** Partially — useful fragments, meaningful rework needed.
- **1** No — faster to do it myself.

### 7. Trust
Would you rely on this tool for real work?
- **5** Yes, with routine checking.
- **3** For exploration, not for final answers.
- **1** No.

## Aggregation rules

- Per-task scores stay per-task; do not average away failures.
- If multiple real reviewers exist, agreement is computed on the **ordinal** 1-5
  structure: Krippendorff's α (ordinal) or weighted Cohen's κ — report the metric
  and why (§79). **No agreement number may be computed or quoted from a single
  reviewer or from simulated runs** (§80: `NOT CONDUCTED` until real submissions).
- A missing dimension (n/a) is recorded as absent, never imputed.
