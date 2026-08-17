# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 2.0.x   | Yes       |
| < 2.0   | Best-effort only |

## Reporting a Vulnerability

Report privately via GitHub Security Advisories (preferred) or open a private GitHub Issue titled `[SECURITY]`. Do not disclose publicly before a fix is coordinated. Expect an initial response within 3 business days.

## Sandbox Model

- **File**: MIME sniff + extension allowlist, 100 MB cap, archive-bomb guard, path traversal block (`packages/execution/file_validator.py`).
- **SQL**: Read-only allowlist (`SELECT/WITH/SHOW/DESCRIBE/EXPLAIN`), row limit `10k`, no `INSERT/UPDATE/DELETE` (`sql_validator.py` + `run_sql`).
- **Python**: AST allowlist, `_safe_import` deny `os/subprocess/socket/requests/eval/exec/open/__import__`, allowed `{polars, numpy, math, statistics, json, re, datetime, collections, itertools}`, 5s wall-clock (`python_sandbox.py`).
- **Prompt injection**: Dataset is `UNTRUSTED DATA`, pattern detection `PROMPT_INJECTION_PATTERNS`, output causal-claim rewrite (`guardrails.py` + `dsa_agent/critic.py`).
- **Resource limits**: Tool budgets `max_steps 20 / max_tool_calls 40 / max_retries 3` (`packages/agent/graph.py`) + evidence coverage gating.

## Known Limitations

- Python sandbox is in-process AST scope (no kernel cgroups); not a full container boundary for adversarial payloads. Wide-table `S311` path is bounded by size checks, not by cgroup memory/CPU.
- Global `_TOOL_CACHE` is per-process memoization (see `docs/v3/V2_FINAL_BASELINE.md` TD-10); per-run scoping is V3 W9 follow-up.

## Out-of-Scope Threats

- Physical host compromise, upstream dependency supply-chain outside `uv.lock`, social engineering of reviewers, denial-of-wallet on paid LLM providers (local-first `stub` avoids this; see `docs/v3/CROSS_MODEL.md`).

Security boundary details: `ARCHITECTURE_FREEZE_V0.1.md` §10 and `docs/v2/security.md` / `docs/v3/V2_FINAL_BASELINE.md` §9.
