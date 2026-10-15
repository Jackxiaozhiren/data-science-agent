# STUDY3 — Reviewer Usability of the Shared Report (Web Product Plan §12, Study 3)

> **Spec:** `WEB_PRODUCT_MASTER_PROMPT.md` §12 Study 3 — validates R-07, the report a stranger opens.
> **Frozen:** 2026-10-15 at the revision that introduced the offline report. The time-box, the per-claim
> outcomes and the mandatory "name the claim" field are fixed before the first session.
> **Status:** `NOT CONDUCTED`. No reviewer has taken part. Nothing here is a result, and no claim-traceability
> percentage may appear anywhere in the repository until real sessions have happened and their raw records are
> archived (`external-validation/README.md` §80).

## 1. What this study decides, and what it cannot

It decides one question: **handing a reviewer only the shared report file, can they verify each claim — or
name, per claim, why they could not?** §16's target (`≥ 90% of flagged claims traceable in ≤ 5 min`) becomes a
measured value only here, with its denominator: the claims the reviewer actually flagged, per this protocol,
in n sessions.

It cannot decide whether the analysis is good, and it cannot decide whether the reviewer *likes* the file —
that is Study 2's question, on the pair. This study is about the mechanics of verification: does the
drill-down reach the tool call behind a claim inside the time-box, and when it does not, does the file make
the failure nameable rather than silent?

## 2. Participants

- **n ≥ 3 reviewers**, the plan's own floor. There is no upper bound; every additional session is appended.
- **Recruiting is the maintainer's action** (plan §19.1 item 6). Eligibility is persona R, as in Study 2:
  someone who grades or acts on others' analyses. `is_project_author` must be `false` for a session to count.
- **One session per person.**

## 3. Materials

- One analysis, the same for every reviewer in a round: a `COMPLETED` run on a committed sample, chosen
  before the round starts and recorded in the results.
- The deliverable is exactly what the product hands a stranger: the **offline report file** (`Download
  offline HTML`), opened however the reviewer opens it — recorded as browser and local file vs. hosted URL,
  because "how did you open it" is part of what R-07 claims to have solved.
- No accompanying explanation. The file is the entire product. A question is answered with "the report is
  the documentation" and recorded as a help event.
- Before the round: the coordinator verifies the file's own claim on itself — zero network requests when
  opened offline — using the acceptance script the repository already ships, so a broken file never reaches a
  reviewer and wastes a session.

## 4. Procedure

1. Say once: *"This report makes claims. For each one, either verify it from the report or tell me you
   couldn't. Five minutes per claim."*
2. The reviewer lists the claims as they see them (the coordinator writes the list down verbatim; the
   reviewer's segmentation is data, not noise — which claims a reader perceives is part of the finding).
3. For each listed claim, one timed attempt:
   - **outcome:** `verified` / `not_verified_within_5m` / `unable_to_attempt`;
   - **minutes** spent on the attempt;
   - **drill_down_used:** whether an in-page expansion or anchor was followed (yes/no);
   - for `not_verified_within_5m`, the **reason** in the reviewer's words, verbatim.
4. At the end, the mandatory question, asked exactly as the plan words it: *"Which claim could you not
   verify?"* — the answer is recorded verbatim and must name at least one claim or state that every claim
   verified.
5. Total session minutes recorded. No score is assigned to the analysis, and the coordinator never says
   whether an attempt was "right" — verification against the file's own evidence chain is the task, not
   agreement with the conclusion.

## 5. What gets reported

- Per reviewer: the claims they listed, each with its outcome, minutes, drill-down flag and verbatim reason;
  the mandatory "could not verify" answer; total minutes; how the file was opened.
- Across the round: the count and fraction `verified within 5 minutes / claims flagged`, with n and the
  per-session values shown — never a bare percentage. The denominator is this protocol's flagged-claims list,
  and saying so is part of the sentence.
- Help events per session. A session with many help events is a finding about the file, recorded as such.

## 6. Consent and archiving

Same rules as Studies 1 and 2: words are recorded only with consent, recorded in the schema record; raw
responses are archived verbatim in a dated file under `external-validation/`; identifiers stay pseudonyms;
results are appended, never overwritten.
