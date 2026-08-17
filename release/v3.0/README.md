# Release v3.0 — Immutable (§74)

> `release/v3.0/` is **immutable** (§74). If an error is found, bump to `v3.0.1` — do not overwrite `v3.0`.

```
release/v3.0/
├── results/   (frozen benchmark/repro/tables)
├── figures/   (frozen PNGs from research/figures/)
└── tables/    (frozen MD/CSV from research/tables/)
```

Populate on `v3.0.0` tag by copying `research/results` + `research/figures` + `research/tables` + `reproduction/v2/results.json` + `benchmarks/baseline` snapshot. See `research/V3_RESEARCH_REPORT.md` Appendix + `docs/v3/V2_FINAL_BASELINE.md`.
