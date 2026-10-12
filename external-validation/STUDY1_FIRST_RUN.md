# STUDY1 — Unmoderated First Run (Web Product Plan §12, Study 1)

> **Spec:** `WEB_PRODUCT_MASTER_PROMPT.md` §12 Study 1 — validates R-01 / R-02 / R-03 / R-10 / R-11.
> **Frozen:** 2026-10-12 at revision `ff3217a`. The success rubric, the time-box and the abandonment rule
> below are fixed *before* the first session, because §12 requires that and because a rubric written after
> seeing the data is not a measurement.
> **Status:** `NOT CONDUCTED`. No participant has run this. Nothing in this file is a result. No
> participant count, completion rate, time, quote or score may be written anywhere in this repository
> until a real session has happened and its raw record is archived (`external-validation/README.md` §80:
> no fake reviewers; plan §19.8: no invented users).

## 1. What this study decides, and what it cannot

It decides one question: **can a person who has never heard of this project get a defensible analysis out
of a URL, alone, in one sitting?** §18 names "building for an audience that never arrives" as the most
likely failure mode and makes this study its test: if five people cannot be recruited, or five arrive and
none complete, the plan says to stop feature work — the blocker is then not the UI.

It cannot decide whether the analysis is *good*. That is Study 2 (paired blind review) and Study 3
(reviewer usability). Reporting a completion rate as product validation would be a category error: this
measures comprehensibility of the path, not correctness of the result.

Every figure in §16 of the plan is a **TARGET**. The corresponding measured value only exists once
§4 of this file has been filled for real participants, with its denominator.

## 2. Participants

- **n = 5.** Not more, not fewer, for the first round: the plan's metric is expressed as `k of 5`, and a
  larger first round makes the qualitative reading (what each person said and where each stopped) unmanageable.
- **Recruiting is the maintainer's action, never the agent's** (plan §19.1 item 6). This file specifies who
  counts as eligible; it does not contact anyone.
- **Eligibility — persona P** (plan §5): currently produces a data analysis that another human will judge
  (take-home assignment, case competition, thesis or a report a manager will read), and can open a browser
  and drag a CSV. Must *not* be able to install a Python environment comfortably — that is the audience the
  CLI already serves and it is not who this study is about.
- **Screen, asked before scheduling (three questions, recorded):**
  1. Do you currently produce analyses that someone else evaluates or acts on? (yes / no)
  2. How do you do that today? (free text — expect spreadsheet or notebook)
  3. Have you ever installed a Python package from a terminal for your own work? (yes / no)
- **Disqualifying:** anyone who has contributed to this repository, read its audit ledger, or works on it.
  `is_project_author` must be `false` for a session to count (same rule as `RESULTS_SCHEMA.json`).
- **One session per person.** No repeats after a failure: a second attempt measures the tutorial effect of
  the first.

## 3. Coordinator procedure

The whole point is that nobody helps. The coordinator is present, silent, and writes down what happens.

1. Have ready: the trial URL, a timer, this file's §4 record sheet, and a consent note covering recording
   of the participant's own words (§6).
2. Say the task script in §5 **once**, verbatim. Do not answer questions about the task; if the participant
   asks what to do, the answer is "whatever you'd do on your own" and the request is recorded as a help
   event.
3. Think-aloud instruction, said once before the timer starts: *"Please keep talking — say what you're
   looking at, what you expect to happen, and what you're confused by. There is no correct thing to say."*
4. Start the timer when the URL is opened. It does **not** stop for a cold start; the wait is part of what
   is being measured (plan §16's `≤ 60 s p90` target includes it).
5. Do not point at anything. Do not name any feature first. In particular, do **not** mention the
   reasoning-mode label — see §5 step 4 for why that is a measurement and not a hint.
6. When the session ends (completion, abandonment, or the time-box), run the three debrief questions in §5.

**What the participant will be looking at, verified rather than assumed.** As of 2026-10-12 the hosted
trial answers `GET /version` with `{"version":"4.5.0","distribution":"jack-data-science-agent",
"reasoning_mode":{"mode":"heuristic","stub":true,"provider":"stub","model":null,"error":null}}`, so every
session sees a deterministic-planner deployment and the page says so. Re-run that probe immediately before
each session and record the answer with the session; a study that reports what participants "saw" without
knowing which build answered is not re-derivable. The first screen is also, as of the same date, an empty
dataset list — R-01 has not shipped — so this study measures the bring-your-own-CSV path only.

## 4. Task script

> "Here's a link. Take a dataset you know well — anything you could check the answer to yourself — and ask
> it a question you care about. Then tell me what you'd show a person who's going to judge this work, and
> what you'd want them to know about its limits. I'm going to stay quiet and let you drive."

Three obligations, each recorded separately (a partial success is a result):

| # | Obligation | Recorded as |
|---|---|---|
| O1 | Complete one analysis of their own CSV | did a run reach a report showing at least one finding? |
| O2 | Find one limitation of it | did they name a limitation, and did the product surface one that they then read? |
| O3 | Produce something they would send a reviewer | which artifact they took, and what they said they'd do with it |

**Known gap in O3, stated rather than papered over.** The plan's §12 wording is "export something you
would send to a reviewer", and it expects a conclusion-only artifact. That export does not exist yet —
requirement R-06 (Lane C) is what ships it, and today the only export is the full evidence-bearing markdown
report (plan §3 B10). So: let the participant take whatever artifact the product offers, record which one,
and record whether they hesitated or asked for something plainer. **Do not tell them a plain version is
coming.** This does not block Study 1; it blocks Study 2, which needs both renderings of the same run to
blind-compare them.

## 5. What is recorded per participant

1. **Completion** — binary, and the definition is frozen here:
   - *complete* = O1 reached a report page showing at least one finding, **and** no help event occurred
     before that point. A run that errored, or a page that shows only an empty state, is not completion.
   - *incomplete* = anything else, with the reason from the abandonment list below or from a help event.
   - The reported figure is `k of 5`, never a percentage (plan §12: denominators are mandatory; a
     percentage on n=5 implies a precision the sample cannot carry).
2. **Time to first result** — seconds from opening the URL to the report page rendering, wristwatch-timed.
   There is no consented event instrumentation yet (R-15), so this is explicitly a coordinator measurement
   and not product telemetry; state it as such wherever it is quoted.
3. **Mode label noticed (R-02)** — two separate fields, because conflating them would be the easiest way to
   manufacture a positive result:
   - `mode_label_unprompted` — did the participant mention the top-right label during free play, before
     anyone asked? Record their words and the timestamp.
   - `mode_label_noticed` — asked once, in the debrief, non-leading: *"What did you make of the thing up in
     the top-right corner?"* If they needed a second prompt to find it, that is `false` with the exchange
     quoted. If they found it but read it as decoration, record that as the finding it is.
4. **Verbatim first sentence about the report** — the first thing they say after the report appears,
   transcribed word-for-word from the recording, not summarised. This is the plan's antidote to
   self-report: what a person says first is data; what they say when asked "was it good?" is politeness.
5. **Debrief questions (three, asked in this order, after the debrief probe above):**
   - What would you show the person judging this, and why that?
   - What made you least sure of anything on that page?
   - If you'd gotten no help at all, where would you have stopped?
6. **Rubric scores** — only the four dimensions of `RUBRIC.md` that a first-run session can honestly
   answer: *Clarity*, *Evidence Quality*, *Usefulness*, *Trust*, on the same 1-5 anchored scale, with
   `n/a` allowed and never imputed. The other three (Correctness, Statistical Validity, Uncertainty) need
   ground-truth checking of the analysis itself and belong to the reviewer studies, not to this one.
   Per-task scores stay per-task; do not average them away (`RUBRIC.md` aggregation rules).

Machine-readable record: one JSON per participant, validated against
[STUDY1_RESULTS_SCHEMA.json](STUDY1_RESULTS_SCHEMA.json).

## 6. Abandonment — what counts

Frozen before the first session, per §12. A session ends as **abandoned** on the first of these that
happens:

- The participant says they want to stop, or asks to be shown what to do and still cannot proceed.
- **90 seconds** with no input of any kind after the coordinator has stayed silent (this is the operational
  definition of "stuck"; a pause to read the page is not abandonment).
- The **20-minute** time-box expires. The box is generous on purpose: the plan's target is ≤ 60 s to a
  first result, so a session still running at 20 minutes has already told us what we needed to know.
- Three consecutive runs that fail or return nothing the participant recognises as an answer.

Not abandonment: pausing to read, scrolling the evidence panel, re-asking a question, uploading a second
CSV, or taking a break to fetch their own file.

When a session ends, record **where** it stopped in the participant's own words plus the last action
observed. §18's kill criterion is about *where each person stopped*, so a bare `abandoned` with no location
wastes the session.

## 7. Reporting

- Raw material — the recording, the verbatim quotes, the filled sheet — is archived **verbatim** under
  `research/external/study1/`, one directory per participant pseudonym, with the consent note and the date.
- The write-up lands in a **dated file** in that directory, appended; an earlier dated record is never
  overwritten (plan §12 reporting rule).
- Each reported number names its denominator and its method: `3 of 5 completed; time-box 20 min;
  coordinator-wristwatch timings; n=5, single site, heuristic-mode deployment, 2026-1x-xx`.
- No agreement statistic across participants. `RUBRIC.md` §79 forbids computing one from fewer than two
  genuine reviewers per dimension, and a first-run study is not a reliability study.
- If a participant's own words would identify them, publish the quote only with explicit consent
  (`may_publish_anonymized` in the record).

## 8. Honest limitations of this protocol

- **One deployment shape, one reasoning mode.** Sessions run against the hosted trial, which plans with
  deterministic heuristics. A completion therefore says the *path* is usable, not that a model-driven
  analysis is. R-02's label is what makes that visible to the participant — and whether it worked is exactly
  what field §5.3 measures.
- **Small n, single site.** `k of 5` is a screening signal, not an estimate. §16's `≥ 4 of 5` target is
  stated against this same n.
- **No telemetry.** Timings and completion are observed by a human (R-15 is not built), so they are
  reproducible only in the sense that the coordinator's notes are archived.
- **The upload path only.** Until R-01 seeds sample data, a participant with no CSV of their own cannot
  start; the screen in §2 is what keeps that from being confounded with failure.
- **Coordinator effect.** A silent coordinator is still a person in the room. The debrief question about
  "no help at all" is there to catch how much of that mattered, not to eliminate it.
