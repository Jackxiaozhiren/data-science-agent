# DataSciBench Research Output — V4.3 W3 §44

> **Spec:** V4.3 §44 DATASCIBENCH OUTPUT.
> **Date:** 2026-09-04 (prompt-completion index; measurements from 2026-08-28 full run).
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

**45/45 supported tasks executed end-to-end (5.8 s); 0 scored — GT absent,
all 45 `failed` (completed-but-unevaluated); 177 unsupported with reasons.
No score is claimed (§42 pilot-success definition).**
