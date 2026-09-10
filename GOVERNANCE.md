# Governance — Data Science Agent

> Minimal governance statement (closes OSPS baseline item DOC-6).
> Single-maintainer project; this file records who decides what, so contributors
> and reviewers know where authority sits. No authority is claimed beyond this.

## Roles

| Role | Who | Scope |
|------|-----|-------|
| Maintainer | Jackxiaozhiren | Final say on merges, releases, security response, roadmap |
| Contributors | Everyone (see CONTRIBUTORS.md) | PRs, issues, discussions, benchmark tasks, plugins |

## Decisions

- **Everyday changes:** PR with green CI (`ci`, `dependency-review`, `secret-scan`, `codeql`) → maintainer merges.
- **Releases:** maintainer tags `vX.Y.Z` only after the canonical gates pass
  (`dsa verify-release`, full pytest, SBOM regen). Version rules: patch = fixes /
  reconciliation; minor = new surfaces, no breaking SDK/CLI change.
- **Architecture changes:** require an ADR first (see `docs/ADR/`); frozen
  surfaces (runtime, evidence graph, evaluation framework) need explicit
  Problem/Evidence/Impact/Alternatives/Migration/Rollback.
- **Benchmarks:** frozen catalogs are never edited in place; new tasks go
  through proposal + ADR. No tuning on held-out tasks, no fabricated scores.

## Security response

- Private reports via GitHub Security Advisories (see SECURITY.md); maintainer
  acknowledges within 3 business days; fixes ship as patch releases.
- General issues: triage SLA — labeled within 7 days (`needs-triage` cleared);
  no fix-commitment SLA is promised (stated, not implied).

## Money / data

- No billing, no telemetry, no hosted user data. Local-first; optional LLM keys
  stay in the user's environment and never enter artifacts.
