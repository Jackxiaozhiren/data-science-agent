# Community Status — Measured Facts Only (V4.3 W10 §71-77)

> **Spec:** V4.3 W10 §71-77. Only real observations, never fabricated (§73). No vanity
> optimization, no fake stars/downloads/contributors.
> **Date:** 2026-08-31 · **Data source:** `gh api` live query of
> `Jackxiaozhiren/data-science-agent` (the GitHub repo); local PyPI check via pypistats.
> **Caveat:** these are the **published lineage** numbers (what `gh api` sees on GitHub).
> The local Spec branch contribution (DataSciBench track) is not yet pushed/merged, so it is
> intentionally not counted here.

---

## 1. Repository metrics (live 2026-08-31, `gh api repos/...`)

| Metric | Value | Source |
|--------|-------|--------|
| Stars | **2** | `gh api repos/… --jq .stargazers_count` |
| Forks | **0** | `gh api repos/… --jq .forks_count` |
| Watchers/subscribers | **0** | `gh api repos/… --jq .subscribers_count` |
| Open issues | **7** | `gh api repos/… --jq .open_issues_count` |
| Created | 2026-08-21 | `gh api` `created_at` |
| Last push | 2026-08-31 | `gh api` `pushed_at` |

## 2. Contributors (live)

| Login | Contributions | Note |
|-------|---------------|------|
| `Jackxiaozhiren` | 123 | maintainer |
| `CommandCodeBot` | 107 | automated coding agent (honest — not a separate human) |
| `github-actions[bot]` | 3 | CI automation |

**Honest interpretation:** there are **zero external human contributors** so far. The
"two contributors" an uninformed reader might infer are maintainer + automation. §76 target
("first genuine external issue/PR") has **not** been met yet — that is a goal, not claimed.

## 3. Issues (sample, live; recent 2026-08-30)

| # | Title | State |
|---|-------|-------|
| 64 | infra: GitHub Actions startup_failure across all workflows | open |
| 63 | deploy: make Render health checks lightweight | open |
| 57 | infra: GitHub Actions startup_failure with zero jobs across workflows | open |
| 65 | Fix release action pinning and artifact runtime | closed |
| 52 | docs: record v4.3.0 final release verification | closed |

These are **real issues** on the published lineage (mostly CI/deploy/docs). No issue exists
yet on the DataSciBench external-benchmark track (not pushed).

## 4. Not measured (honestly left blank, §73)

- **PyPI downloads:** pypistats API returned `429 RATE LIMIT EXCEEDED` on 2026-08-31 →
  recorded as **NOT MEASURED** rather than guessed. (Re-check with `pypistats` when quota allows.)
- **Clones:** not exposed via public API → not claimed.
- **Adoption anecdotes / testimonials:** none collected → none reported.
- **Community dashboard** goal (§77): this file is that dashboard; it stays empty until the
  rows above have real numbers.

## 5. Feed-forward (Phase L / V5, not fabricated here)

- First genuine external issue/PR/star remains an **unmet soft target** (§76) — recorded as
  such, not as success.
- `docs/v4_3/EARLY_ADOPTER_GUIDE.md` is the §74 onboarding deliverable for prospective first
  users (see that file).
- Any future stars/issues shown here must come from `gh api`, never hand-entered.