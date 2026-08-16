# Security Hardening — W9 (Adversarial Suite)

- Date: 2026-08-16
- Baseline: `tests/security/test_security_phase8.py` 13 pass → expanded to **23** (adds `tests/security/test_adversarial_suite.py` 10)
- Boundaries verified live (see `docs/v2/Baseline Report.md §7`):

1. File (100 MB, allowlist ext, MIME sniff, `..`/`//` traversal block, archive bomb `zip/7z/rar/tar/gz/tgz`)
2. SQL read-only allowlist `SELECT/WITH`, deny `DROP/DELETE/UPDATE/INSERT/ALTER/ATTACH/COPY/PRAGMA`, single-statement, row limit
3. Python AST sandbox (deny `os/subprocess/socket/requests/eval/exec/open/__import__` + introspection, allowlist `polars/numpy/math/statistics/...`, `df` injection only, stdout/stderr capture + 5s wall timeout)
4. Prompt injection (dataset cells `UNTRUSTED DATA` + pattern scan `ignore previous instructions/send api key/disregard directives/system: you are now`)
5. Output guard (causal language `cause|effect|impact|leads to|results in|due to` → `is associated with`)
6. Resource budget (`max_tool_calls 40` / `max_tokens 50000` / `max_time`) → STOP / `HUMAN_REVIEW`
7. Sandbox limits extended: output-size/timeout bounded, wide table (80 cols), high-cardinality, symlink escape guarded, oversized payload blocked

Known gaps carried to ADR if subprocess jail + cgroup limits needed — blocked `exec` remains in-process (V2 §48 future).
