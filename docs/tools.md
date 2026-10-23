# Tools

All tools derive `BaseTool[Input, Output]` (`dsa_tools.base`) — Pydantic `Input` + `Output`, `bootstrap()` registry via `dsa_tools.__init__`.

| Tool | Purpose | Notes |
|---|---|---|
| profile_dataset | schema/profile | Polars · kind heuristic |
| run_sql | SQL (DuckDB Arrow) | read-only guard + row limit |
| run_python | Python (sandbox) | `df` bound, allowlist |
| correlation_analysis | Pearson/Spearman/Kendall + CI | evidence insight |
| hypothesis_test | t/welch/mann/anova/kruskal/chi2 | Cohen d + assumptions |
| regression_analysis | linear/ridge/lasso/elastic/logistic | metrics |
| train_model | with CV | StratifiedKFold/R² |
| evaluate_model | metrics + confusion | charts downstream |
| create_chart | histogram/bar/scatter/line/boxplot/heatmap | PNG + base64 |
| forecast | linear_trend/moving_average | holdout MAE |
| assumption_check | Shapiro/Levene | recommendation |
| feature_importance | RF + chart | artifact |
| causal_check | difference/adjusted stub | never passes bar |
| save_artifact | run_id-scoped write | traversal block |
| create_evidence | claim↔source link | ledger |
| validate_result | coverage/causal/completeness | 4 checks |

See `packages/tools/src/dsa_tools/tools/` for Typed I/O and tests `tests/unit/test_tools.py`.

## What the two file-touching tools actually bound

`run_sql` takes caller-authored SQL, so its read-only guarantee cannot rest on a list of denied words: the
deny list (`dsa_execution.sql_guard`) is paired with an engine-level fence, `SET
enable_external_access=false` on the in-memory connection. That second half is what makes the guarantee true
-- a quoted path used as a table name reaches DuckDB's replacement scan without naming any denied function, and
it did read files before the fence was added on 2026-10-23. `dataset_path` still works: the dataset is loaded in
Python and registered as an Arrow relation, which is not external access. Pinned by
`tests/security/test_sql_sandbox.py`.

`profile_dataset` has the opposite shape -- the path is the argument, so nothing about the tool makes it
confined: it reads any path whose extension `dsa_datasets.validate` recognises, and it reports whether a path
exists before it reports that the extension is unrecognised. On a deployed `/mcp` surface that is a host-wide
path oracle; the boundary, the measurements and the open decision are in `MCP_DESIGN.md`.

`run_python`'s `dsa_execution.python_sandbox` is a deny list over an AST, and measured on 2026-10-23 it is not a
security boundary. It denies `import os`, `.system(`, `.environ`, `getenv` and `open()`, and the module objects
it allows carry the same API: `pl.os.walk('/')`, `pl.os.remove('…')` and
`pl._dependencies.subprocess.Popen('…')` each pass `_check_ast` -- polars re-exports `os` and `subprocess`, so
no denied name is needed. Treat it as what it is: arbitrary code as the API's own user, appropriate for
narrowing an LLM's generated analysis and nothing else. The name lists are still worth having for that purpose,
which is why they were not widened into a 25th pattern: an interpreter has no `enable_external_access`, so the
control belongs to whoever can reach the endpoint. `_check_ast`'s `ast.Subscript` branch is a comment about
blocking `__builtins__.__dict__` followed by `pass`, and the `Popen`/`popen` case difference is the whole gap
between denied and permitted.
