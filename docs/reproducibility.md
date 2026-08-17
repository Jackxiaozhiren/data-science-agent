# Reproducibility — V3 W10 §48

> `docs/v3/REPRODUCTION.md` + `docs/architecture.md` (Reproduction Pipeline Mermaid) + `demo/README.md` + `packages/evidence/src/dsa_evidence/reproducibility.py`.

## Pipeline (§49 / §70)

```
Developer Run → Archive → Fresh Environment → Fresh Clone → Fresh Install → Run Benchmark → Compare
```

Commands (§57):

```bash
dsa reproduce --run <run_id>            # single run via artifacts/reports/<runId>/reproduce.sh + analysis.ipynb
dsa reproduce --benchmark v2            # full benchmark fresh-twice
uv run dsa --reproduce v2 --out reproduction/v2   # equivalent (alias)
```

Output (§18): `reproduction/{manifest.json, environment.json, results.json, comparison.json, logs/}`.

## Comparison (§19) & Classes (§20) & Score (§21)

Compare: `Task Success / Statistical Results / Numerical Metrics / Tool Trajectory / Evidence Graph / Artifacts / Report Structure`. Classes: `Exact / Numerical / Semantic / Analytical`. Score: `ReproductionScore {execution, numerical, statistical, evidence, semantic, overall}` + `by_level L0..L5` via `compare_runs`:

| Level | Meaning |
|-------|---------|
| L0 | Request (user_query + dataset) |
| L1 | Code (lenient, semantic) |
| L2 | Data hash |
| L3 | Env (python/platform) |
| L4 | Trajectory (tool sequence) |
| L5 | Conclusion (insights ±20%) |

## External Validation (§39–42)

`uv run dsa demo` — `Demo Dataset → Analysis → Evidence → Report` (`demo/runs/demo`); `uv run dsa external-validation` — installation metrics (`Cold/First Launch/Demo/Benchmark`). See `docs/v3/EXTERNAL_VALIDATION.md` + `demo/README.md`. Linux/macOS tested, Windows explicitly not tested (§41).

## Showcase (§70)

One full case: `Run A → Archive → Fresh Env → Run B → Comparison` with `What Matched / What Differed / Why / ReproductionScore` — see `docs/v3/REPRODUCTION.md` and live `reproduction/v2` artifacts.

## Immutability (§74)

`release/v3.0/{results,figures,tables}` are immutable; fixes go to `v3.0.1`.
