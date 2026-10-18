# Data Science Agent v4.6.0

> Evidence-grounded autonomous data science, from natural-language questions to reproducible analysis.

## Install or upgrade

```bash
pip install -U jack-data-science-agent
```

## Highlights

### Added (post-4.5.0) — the interface speaks two languages, and the keyboard reaches the evidence (R-13)

- **A language switch in the header**, choosing between English and 中文 from a first-party `dsa_locale` cookie.
  The cookie rather than a URL segment or `Accept-Language`: the pages are server-rendered, and a language the
  server cannot see before render would produce English markup that immediately re-paints -- a hydration
  mismatch and a flash on every navigation. `<html lang>` and the tab title follow the choice too, because a
  reader who switches the page but not the voice is being told the translation is a decoration.
- **Every string lives in one dictionary** (`apps/web/lib/locale.ts`), and a missing key renders as a visible
  `⟨key⟩` rather than falling back quietly. That is what turned up the first omission during this very change:
  a key a page asked for that no locale defined, caught on the screen instead of in a review.
- **The starter questions are published in both languages, and the funnel knows both.** A Chinese interface that
  sent the English question behind a Chinese button would be a label over different content, so the Chinese
  wording is what gets sent. `starter_questions_zh.json` sits beside the seeder keyed by **catalog task id**,
  not by the English sentence, so rewording a question cannot silently unmatch it. `is_starter_question` accepts
  every published spelling -- the guard that matters is `test_the_chinese_wording_of_a_starter_records_the_same_link`:
  a matcher that only knew English would keep counting the half that stayed English, so the funnel would read as
  a smaller product rather than as a broken measurement.

Full entries: `CHANGELOG.md` and the release notes.

…

## Verify the release

- [GitHub Release](https://github.com/Jackxiaozhiren/data-science-agent/releases/tag/v4.6.0)
- [PyPI](https://pypi.org/project/jack-data-science-agent/)
- Inspect the attached wheel/sdist and publishing attestations on the release page.

## Share-ready summary

> Data Science Agent v4.6.0 is available: evidence-grounded autonomous data science with reproducible reports, claim-level provenance, benchmarks, and multiple interfaces. Release: https://github.com/Jackxiaozhiren/data-science-agent/releases/tag/v4.6.0

---

This announcement is rendered by `scripts/generate_release_announcement.py` from the repository's release record -- the CHANGELOG section for the version, or the published GitHub Release. The release page remains the source of truth for artifacts and full notes.
