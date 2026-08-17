# Technical Report — V3.0 §52–54

> `research/technical-report/` mirrors `research/V3_RESEARCH_REPORT.md` (§51) with versioned provenance.

## Versioning (§53)

- `V3.0 Research Report`: `research/V3_RESEARCH_REPORT.md` (this release, `benchmark 0.3.0`, commit at `ROADMAP`).
- `V3.1 Revision`: future `research/technical-report/V3.1_RESEARCH_REPORT.md` when results change — do not overwrite `V3.0`.

Each result links: `Git Commit / Benchmark Version / Dataset Version / Experiment Configuration` (§53).

## Figure Reproducibility (§54)

All figures have a generation script:

```
research/
├── figures/*.png   (generated)
└── scripts/generate_figures.py  (run: uv run python research/scripts/generate_figures.py)
```

No hand-edited finale without a script.

## Table Reproducibility (§55)

Each table: `Raw Result → Analysis Script → Generated Table` (§55):

```
research/
├── tables/*.md     (generated: benchmark_summary, claim_evidence, ablation)
└── scripts/generate_tables.py  (run: uv run python research/scripts/generate_tables.py)
```

See `research/figures/README.md` + `research/tables/README.md` for the long-form note.
