# MCP Design — Stateless Adapter (2026-07-28)

## Principle
MCP is an **adapter** over the Tool Layer. Core domain (dsa_agent / dsa_datasets / dsa_tools) does NOT import dsa_mcp.

```
Core Domain (dsa_tools, dsa_agent, dsa_datasets)
      ↑
   MCP Adapter (dsa_mcp) — stateless, tool discovery, call dispatch
      ↑
   MCP Clients (Claude / Cursor / VS Code / etc) via stdio / HTTP+SSE
```
`dsa mcp` prints the surface as JSON; `dsa mcp --stdio` serves the same `tools/list` / `tools/call` / `resources/*`
methods over line-delimited stdin/stdout, which is what a client config that launches a command needs.

## Protocol (2026-07-28 stateless core)
- No server-side session. Each `tools/call` is self-contained.
- Tool discovery via `tools/list`; calls via `tools/call` with JSON args.
- Auth: **none on this surface.** `AuthMiddleware` covers `/api/*` only -- it returns early for any path that does
  not start with `/api/` -- so `/mcp` and `/mcp-app` are reachable without a credential even when `DSA_AUTH_TOKEN`
  is set, and there is no `DSA_MCP_TOKEN` anywhere in the code.
- What that surface can actually do, measured on a local instance rather than asserted.
  `profile_dataset` takes any `path` the caller names and validates only its extension, so a file outside the
  repository is read and its first values come back -- `sample_values` in the column profile, measured returning
  the literal cell contents of a CSV in a temporary directory. On a deployed instance that means any `.csv`,
  `.json`, `.jsonl`, `.parquet`, `.xls` or `.xlsx` file on the host. The same tool checks that the path exists
  *before* it looks at the extension, and that reaches further than the six formats: an existing path with no
  allowed suffix answers `Unsupported file extension` while an absent one answers `File not found`, so the
  surface is a host-wide path-existence oracle -- it reports on files it can never read. Both halves are pinned
  in `tests/security/test_upload_guard.py`, the extension set against `ALLOWED_EXTS` and the oracle against the
  two error strings, so widening the reach or reordering those checks has to change this paragraph on purpose.
- `run_sql` was fenced at the engine on 2026-10-23: its connection sets `enable_external_access=false`, because
  the 24-pattern deny list did not see a quoted path used as a table name, and that path was readable. The
  guarantee is the setting *and* the list now; `docs/tools.md` says which half does what.
- `run_python` is **not a sandbox in the security sense**, and the claim this file carried until the same day --
  that it denies `import os`, so the surface is not a shell -- is withdrawn. Its AST checker blocks the names
  somebody wrote down (`import os`, `.system(`, `.environ`, `getenv`, `open()`, `__class__`), while the module
  objects it permits carry the same API: `pl.os.walk('/')`, `pl.os.remove('…')` and
  `pl._dependencies.subprocess.Popen('…')` each pass `_check_ast` unexecuted, because polars re-exports `os` and
  `subprocess`. A child process makes the rest of the list beside the point. There is no in-process equivalent
  of the DuckDB switch here -- an interpreter running as the same user holds that user's rights -- so the
  boundary is which hosts can reach `/mcp`, not what a payload spells.
- Decided and executed the same day: `run_python` and `run_sql` are withheld from the HTTP surface -- neither is
  advertised by `tools/list`, and a `tools/call` for either is refused before the dispatcher with `-32000`, a code
  in the range the JSON-RPC spec leaves to the server, naming the tool and pointing at `dsa mcp`. The exclusion is
  one frozen set (`adapter.HTTP_WITHHELD_TOOLS`) applied by one function (`http_tools_for_wire`) used by every HTTP
  boundary, so no fifth route can re-publish what the last one withheld. `tests/security/test_mcp_http_surface.py`
  pins both directions, including that a withheld call never reaches `call_mcp_tool`. Stdio is deliberately
  unaffected: `dsa mcp` is launched by whoever owns that machine and publishes the whole registry.
- What a credential-less caller can still do over HTTP after that: read and probe through `profile_dataset`, with
  the reach and the path-existence oracle described two bullets up, plus the analysis and reporting tools that
  operate on data the caller supplies. Narrower, not closed -- authenticating the surface or binding it to
  loopback remains the owner's open decision (`AUDIT_LEDGER.md` §265).
- One limit this file cannot express: what a running instance publishes is decided by the build it was made
  from, not by the paragraph above. The Render demo was redeployed from `main` on 2026-10-24 and its
  credential-free `tools/list` then omitted both names, with a call to either answered by `-32000`; that is the
  check, and it is worth running before repeating any sentence from this file about a live host. The command is
  in `docs/hosted-demo.md`.
- MCP surface mirrors the Tool Layer with friendly names.

## Tools Exposed
The table is the surface; `dsa mcp` prints what `tools/list` publishes, and a client reads the parameters from each
tool's `inputSchema`, which is derived from the backend's own pydantic input model rather than typed here. So this
table names the backend and the argument subset, and the schema on the wire is the authority on types and required
fields.

| MCP name | Backend | Input subset |
|---|---|---|
| profile_dataset | dsa_tools/profile_dataset | path/dataset_id |
| inspect_dataset | wrapper around profile_dataset (schema view) | path |
| query_dataset | run_sql convenience (SELECT) | sql, dataset_path |
| run_sql | run_sql | sql, dataset_path, max_rows |
| run_python | run_python | code, dataset_path |
| run_statistical_test | hypothesis_test | dataset_path, test, group_col... |
| correlation_analysis | correlation_analysis | dataset_path, x, y, method |
| train_model | train_model | dataset_path, target, task... |
| evaluate_model | evaluate_model | dataset_path, target... |
| create_visualization | create_chart | dataset_path, chart_type, x, y... |
| get_evidence | create_evidence + validate_result (read) | evidence_id / claim |
| generate_report | generate_report | run_id, markdown... |
| save_artifact | save_artifact | run_id, type, filename, content |
| export_artifact | export_artifact | source, filename, format, workspace |
| forecast | forecast | dataset_path, date_col, value_col, periods, method |
| assumption_check | assumption_check | dataset_path, column/columns, check, group_col |
| causal_check | causal_check | dataset_path, treatment, outcome, confounders, method |
| feature_importance | feature_importance | dataset_path, target, task, top_k |
| analyze | dsa_agent graph (§36 full loop) | dataset/dataset_path, task (alias question), run_id (alias analysis_id) |

## Implementation
- `packages/mcp/src/dsa_mcp/adapter.py` — stateless registry bridging MCP JSON → BaseTool.run
- `packages/mcp/src/dsa_mcp/server.py` — FastMCP-like HTTP server on /mcp (JSON-RPC 2.0), plus STDIO mode for Claude Desktop
- No global mutation of core; bootstrap idempotent.

## Out of Scope (V0.1)
- OAuth / remote registry
- Streaming tool outputs (deferred to SSE in analysis router)
- Client SDK generation
