# Security

File gatekeepers: `packages/datasets/src/dsa_datasets/validate.py` + `packages/execution/mime_sniff.py` — allowlist ext/MIME, `head` magic peek, `..` traversal block, 100MB limit, archive block.

SQL: `packages/execution/sql_guard.py` — read-only allowlist `SELECT/WITH`, deny `DROP/DELETE/UPDATE/INSERT/ALTER/ATTACH/COPY/PRAGMA`, single-statement, row-limit enforcement.

Python: `packages/execution/python_sandbox.py` — AST guard deny `os/subprocess/socket/requests/eval/exec/open`, safe globals, `df` injection, stdout/stderr capture + wall-clock timeout.

Prompt injection: `packages/execution/guardrails.py` (`contains_prompt_injection`, `rewrite_unsupported_claim`) + `dsa_agent.critic.rewrite_unsupported_claim / detect_prompt_injection` (dataset cells tagged `UNTRUSTED DATA`).

Resource budgets: `check_resource_limits` (tool calls / tokens / execution time) → `WAITING_FOR_APPROVAL / HUMAN_REVIEW`.

Tests: `tests/security/test_security_phase8.py` (prompt injection / path traversal / code injection / malicious file / SQL injection / output guard / budget / HITL).
