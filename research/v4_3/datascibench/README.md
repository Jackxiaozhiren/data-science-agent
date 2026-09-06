# DataSciBench Research Output — V4.3 W3 §44

> **Spec:** V4.3 §44 DATASCIBENCH OUTPUT.
> **Date:** 2026-08-28 (execution lane) · **GT lane scored:** 2026-09-05.
> **Honesty note:** this directory is an **index**, not a fork. Canonical raw data
> lives at `benchmarks/external/datascibench/results/raw_runs.json` (sha256
> `a9b15af8…efdd`, 45 runs). Nothing here duplicates GT or upstream content
> (upstream has no LICENSE; GT is gated — see `../UPSTREAM.md`
> i.e. `benchmarks/external/datascibench/UPSTREAM.md`).

---

## Layout (§44 required)

```text
research/v4_3/datascibench/
├── README.md                  # this file
├── manifest.json              # run provenance (§31 fields)
├── DATASCIBENCH_REPORT.md     # §44 report (all required sections)
├── raw/                       # pointer → canonical raw_runs.json (no copy)
├── processed/                 # pointer → generated Phase F artifacts
└── failures/                  # failure taxonomy (from real runs)
```

## Canonical pointers

| Artifact | Location |
|---|---|
| Raw runs (45) | `benchmarks/external/datascibench/results/raw_runs.json` |
| Results summary | `benchmarks/external/datascibench/results/datascibench_results.json` + `research/external/datascibench_results.json` |
| Full narrative report | `research/external/DATASCIBENCH_REPORT.md` |
| Phase F tables/figures | `research/v4_3/results/{processed,tables,figures,manifests}/` |
| Adapter + manifest | `benchmarks/external/datascibench/{adapter.py,manifest.json}` |
| Upstream record (§36) | `benchmarks/external/datascibench/UPSTREAM.md` |

## Verdict (one line, honest)

**GT lane 2026-09-05: 44/45 scored, 0 passed (CR ≥ 0.5), mean CR 0.026**
(human_ mean 0.048/max 0.300; csv_excel_ all 0.000 — output-layout mismatch +
VLM-judge credential gap, §9 of the canonical report); **human_7
`execution_error` (OOM on 79 MB xlsx, 16 GB box).**
Canonical narrative: `research/external/DATASCIBENCH_REPORT.md` §9.
