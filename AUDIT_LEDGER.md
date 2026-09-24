# DSA Audit Ledger

Executed against `REPO_DIAGNOSIS_AND_IMPROVEMENT_PROMPT.md` Sections 1–31.
Lane for this session: **L1 — Verification integrity** (§10). No source file has
been edited; §18 approval gate has not been passed.

## Baseline

- session: 1   date: 2026-09-24T13:04Z   commit: `150b54f`   lane: L1
- uv sync --dev / uv lock --check: exit 0 / exit 0
- pytest: **397 passed, 0 failed**   coverage: **80.24%**   (gate fail_under = 79)
- ruff check: **0 errors** ("All checks passed!")   ruff format --check: **0 would reformat** (179 files already formatted)
- mypy: **0 issues** ("Success: no issues found in 108 source files")   files checked: **108**
- sync_vendor --check: exit **0** ("OK: vendored dsa_* is in sync")   render_leaderboard --check: exit **127 as written** / exit **0** via `uv run python` ("Leaderboard is valid and synchronized (1 entries).")
- check_npm_workspace_lock: exit **0**   check_public_claims: exit **0** (findings listed: **0**, stdout "✓ No stale claims detected — 0 issues")
- git status --short: **2 lines** (`?? REPO_DIAGNOSIS_AND_IMPROVEMENT_PROMPT.md`, `?? data-science-agent/`)   git ls-files \| wc -l: **730**   git describe --tags: **v4.4.0-26-g150b54f**
- du -sh artifacts benchmarks data-science-agent node_modules: **4.3G / 2.8G / 1.1G / 484M**
- tracked pytest skip/xfail: **0**   TODO/FIXME markers: **0**

### Baseline measurement methods (§N12 — every count states its method)

| Count | Method |
|---|---|
| 397 passed / 0 failed | Character count of the `-q` progress rows in the §0 step-2 log: `head -6 log \| grep -o '^\.\+' \| awk '{s+=length($0)}'` = 397 dots; a separate scan for `s/S/x/X/w/u/I` status characters in the same rows returned 0. **The suite's own output contains no `passed` summary line** — see D-L1-04. |
| 80.24% | `Total coverage: 80.24%` emitted by `uv run pytest -q --cov --cov-report=term-missing`; TOTAL row = 7643 stmts / 1267 miss / 2166 brpart 439 / 80%. |
| 0 issues (claims) | `uv run python scripts/check_public_claims.py` stdout line 1, exit 0. |
| 730 tracked files | `git ls-files \| wc -l` (not a filesystem walk). |
| 2 untracked lines | `git status --short` exit 0. Both accounted for: `data-science-agent/` per §3.2, and `REPO_DIAGNOSIS_AND_IMPROVEMENT_PROMPT.md`, which §24 R1 names as expected ("the tree is otherwise clean apart from this document and your ledger"). §4's "at most two untracked lines" enumerates `data-science-agent/` + `AUDIT_LEDGER.md` and omits the prompt document itself — a self-inconsistency in the instructions, not a dirty tree. |
| pytest mark.skip/xfail = 0 | `grep -rnE "pytest\.mark\.(skip|xfail)\|xfail" packages apps/api src tests scripts docs --include='*.py' \| grep -v _vendor` → 0 hits. A broader pattern including `skip\(` returns 2 hits, both `pytest.importorskip` at `tests/unit/test_data_engine.py:5-6` — a different mechanism, see D-L1-05. |
| TODO/FIXME/HACK/XXX = 0 | `grep -rnE "TODO\|FIXME\|HACK\|XXX" packages apps/api src tests scripts docs --include='*.py' \| grep -v _vendor` → 0 hits. Scoped to `.py` in those directories; not a whole-repo or markdown scan. |
| mypy 108 files | The `Success:` line's own file count from `uv run mypy packages apps/api src --ignore-missing-imports`. |

### Baseline verdict — GREEN, with one explained exception

§0 steps 1 and 2 (the gates §4 makes stop-conditions) exit 0. Coverage 80.24%
is inside the predicted 79–81% band. Step 3's vendor and npm-lock gates exit 0.
Step 4 matches §4's expectation once the prompt document is accounted for.
Step 5 behaves exactly as §4 predicts: exit 0 **and** no CI wiring.

Two anomalies, both explained, neither a baseline failure:

1. `python scripts/render_leaderboard.py --check` as written exits **127** —
   `command not found: python`. Only `python3` (`/opt/homebrew/bin/python3`) and
   `uv` are on PATH. The gate itself **passes** when run through the interpreter
   that exists. §33's rule for this case is explicit: record it as a finding and
   carry on. Filed as **D-L1-01**.
2. The documented §0/§23 pytest command emits **no test-count line**. §28 stop
   criterion 1 ("not green and you cannot explain why") is not triggered because
   the cause is understood; filed as **D-L1-04**.

## Lane L1 — Verification integrity

**Question (§10):** *Which of this repository's checks cannot fail?*

### Independent enumeration

_(Written before opening §32, per §17.1 and §N9. Appendix A's L1 seeds have not
been read at the time of writing this block; the diff appears further below and
is appended only after this section is committed.)_

_Status: in progress._

### Findings

_Status: pending._

### Lead-register diff

_Status: pending — Appendix A §32.1/§32.2/§32.3 not yet opened._

### Fixes applied

_None. §18 approval gate not passed; no file edited._

### Deliberate non-actions

_None yet._

## Session log

- 2026-09-24T13:04Z — §0 First Ten Commands executed; exit codes captured to
  `/tmp/audit0/`. Baseline block written from measured output. Ledger committed
  before any source edit (§N10).
