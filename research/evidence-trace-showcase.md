# Evidence Trace Showcase — V3 §69 (Flagship Demo)

> **One complete Demo** `Claim → Evidence → SQL/Python → Result → Chart → Dataset` — becomes the **flagship case** for the agent.

## Case

**Question**: `Analyze correlation between price and revenue`  (demo question, also `benchmarks/v2` SQL/Statistics blend)
**Dataset**: `benchmarks/v2/datasets/sales.csv` (copied to `demo/datasets/sales.csv`, 500 rows, 6 cols, seed 42)

## Chain

```
Claim (Insight I-59ce927e)
  "Correlation price vs units: r=-0.057"
  ↓ supports
Evidence (E-884b39b3, statistical_test → TC-a7ac771c)
  result {"r": -0.05678, "p_value": 0.20498, "method": "pearson", "ci_low": -0.143, "ci_high": 0.031}
  interpretation "negligible negative association (r=-0.057) (not significant)."
  limitations "Correlation does not imply causation."
  confidence 0.80 · status pending
  ↓ derives_from
ToolCall (TC-a7ac771c correlation_analysis)
  input  {"dataset_path": "benchmarks/v2/datasets/sales.csv", "x": "price", "y": "units"}
  output {"r": -0.05678, "p_value": 0.20498, ...}
  status ok · duration 4ms · timestamp 2026-08-17T04:47:29Z
  ↓ reads
Dataset (sales, hash sha256 of file, 500 rows)
  path benchmarks/v2/datasets/sales.csv · hash via experiment.json dataset_sha · columns price/revenue/units/category/region/date
```

### Python path (alternative)

```
Claim → E-8ccd7ad2 (python → TC-b6348d87 profile_dataset) → TC-b6348d87 (dataset_path, x=price) → same Dataset
```

### Result → Chart → Dataset closure

```
Result r=-0.057 (above)
  ↓ validated by
Validation (evidence_coverage ok, unsupported_claim ok — no causal language)
  ↓ rendered to
Chart 20997d61e3_histogram.png + 9723f30c20_line.png (artifacts/charts/, embedded as ![chart] in report.md)
  ↓ reproducible via
Dataset hash in demo/runs/demo/manifest.json + experiment.json + reproduce.sh + analysis.ipynb
```

## Inspect

```bash
uv run dsa demo                       # regenerates demo/runs/demo/{report.md,state.json,manifest.json}
cat demo/runs/demo/report.md          # Evidence + Insights + Validation + Limitations
cat demo/evidence/state.json | jq '.evidence, .insights'  # trace
uv run dsa external-validation        # Demo Execution Time ~1.8s, First Launch ~20–90ms
```

## Why flagship (§69)

- End-to-end `Claim → Evidence → Tool → Dataset` (not free-text LLM).
- Two chart artifacts embedded, validator `unsupported_claim` guard exercised (causal wording blocked).
- One-command local-first (`stub/small`, no key, Cloud $0), fresh-machine testable (§41).
