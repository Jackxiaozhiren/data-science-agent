# Security

File gatekeepers: `packages/datasets/src/dsa_datasets/validate.py` + `packages/execution/mime_sniff.py` — allowlist ext/MIME, `head` magic peek, `..` traversal block, 100MB limit, archive block.

SQL: `packages/execution/sql_guard.py` — read-only allowlist `SELECT/WITH`, deny `DROP/DELETE/UPDATE/INSERT/ALTER/ATTACH/COPY/PRAGMA`, single-statement, row-limit enforcement.

Python: `packages/execution/python_sandbox.py` — AST guard deny `os/subprocess/socket/requests/eval/exec/open`, safe globals, `df` injection, stdout/stderr capture + wall-clock timeout.

Prompt injection: **detector present, not wired.** `packages/execution/guardrails.py` (`contains_prompt_injection`, `sanitize_untrusted_text`) and `dsa_agent.critic.detect_prompt_injection` are implemented and unit-tested, but no shipped code path calls them, so dataset cell text is currently neither scanned nor tagged. Do not treat this as a control until a caller exists.

Claim discipline: enforced. `check_unsupported_claims` (`packages/agent/src/dsa_agent/critic.py:90`) emits the `unsupported_claim` validation, which is in `HARD_FAIL_CHECKS` (`packages/agent/src/dsa_agent/graph.py:51`, applied at `:631`), so an unsupported causal claim fails the run. The textual helper `rewrite_unsupported_claim` (in `guardrails.py` and `critic.py`) is not applied to any output — claims are failed, not reworded.

Resource budgets: `check_resource_limits` (tool calls / tokens / execution time) → `WAITING_FOR_APPROVAL / HUMAN_REVIEW`.

Tests: `tests/security/test_security_phase8.py` (prompt injection / path traversal / code injection / malicious file / SQL injection / output guard / budget / HITL).
