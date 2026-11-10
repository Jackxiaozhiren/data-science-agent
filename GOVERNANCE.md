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

## Decision authority for externally consequential actions

The classes below come from `docs/measurement-basis.md#authorization-coverage` (S1). That page defines
and scores the checklist; this table is the named authority the checklist asks for. Each row says who
authorizes the action and where the decision is written down. Contributors may open issues and
discussions in their own name; rows AC3 and AC4 concern statements or state changes made **on the
project's behalf**, including by an agent acting for the project.

| # | Action class | Authorizer | Where the decision is recorded | Precondition before acting |
|---|---|---|---|---|
| AC1 | Publishing a release (tag, package artifact, changelog entry) | Maintainer | The `vX.Y.Z` tag with its `CHANGELOG.md` entry; the pull request carries the canonical gate output | Canonical gates pass (`dsa verify-release`, full pytest, SBOM regen) |
| AC2 | Promoting a real-model result to a public leaderboard row or comparison claim | Maintainer | The pull request publishing the row, carrying `matrix_validation.json` and naming the maintainer who approved promotion | Publication rule in `docs/real-model-evaluation.md` (14 conditions); `publication_ready=true` is a gate, not the authorization |
| AC3 | Commenting on a public issue on the project's behalf | Maintainer | The issue thread: a named account and the comment body; a comment written by an agent names the authorizing maintainer in the same comment | No undisclosed automated statement |
| AC4 | Closing a public issue | Maintainer | The close event and a closing comment in the issue thread stating the reason and who decided | Triage state resolved (see Security response below) |
| AC5 | Changing this document or a comparable policy file | Maintainer | The pull request and its merge commit; an `AUDIT_LEDGER.md` entry when the change moves authority | Green CI |
| AC6 | Changing branch protection or repository settings | Maintainer, acting as repository admin | A dated `AUDIT_LEDGER.md` entry quoting the before/after setting and the API response or run that made it | None configured. A settings change is not a merge, so the `ci` requirement does not cover it; the ledger entry is the record |
| AC7 | Spending money or enabling a credentialed paid model lane | Maintainer | A dated `AUDIT_LEDGER.md` entry naming the budget cap, duration and credential; absent that entry, "No billing" below stands | Explicit prior decision, `DSA_MAX_COST_USD` set, and a project-level spend limit |
| AC8 | Adding, rotating or using a repository credential | Maintainer | A dated `AUDIT_LEDGER.md` entry naming the secret, the workflow and the run id; secrets stay in repository secrets, never in source or artifacts | Secret scanning and push protection remain enabled |
| AC9 | Stating an external conclusion (capability, security, currency or compatibility) | Maintainer | The pull request carrying the claim, with its evidence link and a named approval | Claim guards green; guards are necessary, not sufficient |

**This table records accountability, not enforcement.** Branch protection currently requires the `ci`
status check and no pull-request review, and `CODEOWNERS` names an owner without requiring one. Naming
a decider here adds no technical gate, and a record is only as good as its author. Where a class needs
enforcement, that is a separate settings change and must itself be recorded under AC6. The zero-billing
constraint below is unchanged: AC7 names who would have to decide before an exception, it does not
create one.

**A reading is not a policy and a policy is not a reading.** Changing this table changes the tree, not
the measurement basis. Any later score is a new dated record under the same nine classes, never an edit
to an earlier reading.

## Security response

- Private reports via GitHub Security Advisories (see SECURITY.md); maintainer
  acknowledges within 3 business days; fixes ship as patch releases.
- General issues: triage SLA — labeled within 7 days (`needs-triage` cleared);
  no fix-commitment SLA is promised (stated, not implied).

## Money / data

- No billing, no telemetry, no hosted user data. Local-first; optional LLM keys
  stay in the user's environment and never enter artifacts.
