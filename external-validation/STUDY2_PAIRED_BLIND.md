# STUDY2 — Paired Blind Review (Web Product Plan §12, Study 2)

> **Spec:** `WEB_PRODUCT_MASTER_PROMPT.md` §12 Study 2 — validates R-06 (the findings/audited pair) and,
> through it, the product's central bet that provenance helps rather than decorates.
> **Frozen:** 2026-10-15 at the revision that introduced the offline report (R-07). The measures, the order
> rule and the reporting rule below are fixed *before* the first session, for the same reason Study 1's are:
> a rubric written after seeing the data is not a measurement.
> **Status:** `NOT CONDUCTED`. No reviewer has taken part. Nothing here is a result, and no number derived
> from this study may appear anywhere in the repository until real sessions have happened and their raw
> records are archived (`external-validation/README.md` §80: no fake reviewers).

## 1. What this study decides, and what it cannot

It decides one question: **on the same analysis, does per-claim provenance change how a reviewer trusts and
checks the document?** The plan names the finding it must be able to hear: provenance may *bother* reviewers
rather than reassure them, and the product must be able to act on that (§20's failure table) instead of
defending the current design.

It cannot decide whether the analysis itself is correct — the reviewer sees one analysis, and no ground
truth is offered. A trust score is a report about the *document*, not about the data.

The result is reported as a **paired difference with n** — per-participant values, their median and range —
and never as a headline percentage. With the frozen n below, no parametric significance test is claimed; a
p-value would be decoration on six points.

## 2. Participants

- **n = 6**, the smallest n at which a paired difference is reported with per-participant values rather than
  as anecdote. A larger round is a second round, run after this one reports.
- **Recruiting is the maintainer's action** (plan §19.1 item 6). This file specifies who counts; it contacts
  no one.
- **Eligibility — persona R:** currently grades, judges or acts on analyses produced by someone else
  (manager, instructor, case-competition judge, reviewer). Must not have contributed to this repository or
  read its audit ledger; `is_project_author` must be `false` for a session to count.
- **One session per person.** Both documents in one sitting, nothing repeated.

## 3. Materials — the blindness rules are the protocol

The treatment is the *provenance dimension alone*, so the two documents must be identical in every other
respect and their labels must never reach the participant.

1. One `COMPLETED` run on a committed sample (the catalog's `eda-01` sales task), the same run for every
   participant in a round.
2. Both documents are rendered the same day, from the same run, through the report endpoint's two modes:
   `GET /api/v1/analysis/{id}/report?format=markdown&mode=findings` and `...&mode=audited`.
3. Both are converted to the delivery medium by the **same converter in the same session** (the same
   browser print-to-PDF flow, same paper size and margins), so typography cannot leak the condition. The
   converter actually used is recorded in the round's dated results file.
4. Files are named `report_A` / `report_B`. The A/B-to-mode mapping lives in a `pairing_key` file kept by
   the coordinator, is recorded once in the results, and is never shown to a participant.
5. The audited document's extra sections (Plan, Tool Calls, Evidence, Validation) **are** the treatment and
   stay exactly as the product renders them. Nothing is added to make provenance look better; the study
   measures the product, not a brochure.
6. The coordinator sees both documents by necessity and is not blind; the *participant* is. This is recorded
   as a limitation of the design, not hidden.

## 4. Procedure

1. Say once: *"Here are two reports of the same analysis. Please read both, then answer for each."* Nothing
   more. A question about the task is answered with "whatever you'd do on your own" and recorded as a help
   event.
2. The document order follows the participant's index in the round: odd-numbered participants read A first,
   even-numbered B first. Order is recorded per participant; the analysis cannot separate order effects from
   document effects at this n, and says so.
3. For **each** document, collect, in this order and before any discussion:
   - trust rating, 1–7, the participant's own meaning of the scale stated aloud once by them;
   - how many of the document's claims they would verify before acting on it (0 to all);
   - minutes spent with that document (coordinator's timer);
   - one verbatim sentence about the document.
4. After both: *"Did anything in either report help you trust it, or get in the way?"* — recorded verbatim,
   then classified by the coordinator into the verdict field of the schema.
5. The mode names ("findings", "audited") are never said. If a participant asks what the ids in document B
   are, the answer is "part of the report" — the ids are the treatment.

## 5. What gets reported

- Per participant: both trust ratings, both claim-verification counts, both times, order, and the paired
  difference `trust(audited) − trust(findings)`.
- Across the round: the median and range of the paired differences, with every per-participant value shown.
  No percentage, no significance claim, no averaging of the two documents' scores across participants.
- The verdict field (`helped` / `hindered` / `neutral` / `mixed`) with one verbatim quote per participant.
- The possibility the plan names is an expected outcome, not a failure: a round in which reviewers report
  the provenance as friction is a finding the product must be able to act on, and §20 pre-commits the
  response (fewer receipts on the surface, deeper drill-down) rather than a defense.

## 6. Consent and archiving

Same rules as Study 1: recording a participant's own words requires their consent, recorded in the session's
schema record; raw responses are archived verbatim in a dated file; identifiers stay pseudonyms. Results
land appended under `external-validation/`, never by overwriting an earlier dated record.
