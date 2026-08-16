# Figures — V2 Research

All figures generated from `research/results/ablation_*.json` and `benchmarks/v2` runs (seed 42, no fabricated numbers).

- `by_category.png` — task_success per category (EDA/SQL/Statistics/Regression/Classification/Time Series/Visualization/Data Quality/Data Profiling/Clustering/Evidence Validation)
- `ablation.png` — task_success vs evidence_coverage vs unsupported_claim_rate across A–F
- `latency.png` — mean latency per category
- Generate via: `uv run python -c "from pathlib import Path; import json, matplotlib.pyplot as plt; data=json.load(open('research/results/ablation_ablation-feb31c61.json')); print(data['summary'])"`
