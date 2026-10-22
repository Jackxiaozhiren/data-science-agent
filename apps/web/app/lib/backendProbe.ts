// The one owner of "what is the backend doing right now".
//
// Three places used to answer that question alone: the header dot fetched `/health` once and had two
// colours, each page inferred "down" from its own rejected request, and an empty list could mean either a
// new account or a dead API (web plan B3/B4). The case none of them described is the common one on a free
// instance: the first request hangs for tens of seconds while the machine wakes. Measured on the hosted
// demo on 2026-10-13 -- `GET /health` answered 200 after **44.5 s** (output/lane-c capture log) -- and
// re-measured on 2026-10-22 on the same service at **92.8 s** (`curl -w` timing, connection held open the
// whole time, no bytes first). So "nothing has answered yet" is a real third state, it is what a first-time
// visitor actually sees, and calling it "unreachable" loses the visitor.
//
// The budget below is those measurements, not a guess, and it has to *exceed* the slowest one: a sequence
// that gives up before the instance wakes reports a sleeping machine as a dead one, which is the exact
// defect R-11 exists to remove. That is what happened to the first budget -- sized to clear 44.5 s with
// margin -- on a 92.8 s wake. The silence hint, not the attempt length, is what makes the waiting state
// appear at once; PROBE_BUDGET_MS is what the guard compares against the measurements.

import { useEffect, useMemo, useSyncExternalStore } from "react";

import { apiUrl } from "@/lib/api";
import { t, type Locale } from "@/lib/locale";
import { useLocale } from "@/app/lib/LocaleProvider";

export type BackendPhase = "probing" | "warming" | "ready" | "unreachable";

/** Per-attempt ceiling. A sleeping instance hangs rather than refusing, so this is what detects it. */
export const PROBE_TIMEOUT_MS = 18000;
/** Attempts are bounded on purpose: an unbounded retry is indistinguishable from a hang. */
export const PROBE_ATTEMPTS = 6;
/** Waits between attempts. */
export const PROBE_BACKOFF_MS = [2000, 4000, 6000] as const;

/**
 * How long an outstanding request may go unanswered before the page says it is waiting. Deliberately much
 * shorter than PROBE_TIMEOUT_MS: this names the experience, that one names the coverage.
 */
export const PROBE_SILENCE_HINT_MS = 1500;

/**
 * How long the probe keeps saying "waking up" before it concludes "nothing answered", derived from the three
 * constants above rather than restated: coverage = one timeout per attempt plus one backoff per gap.
 */
export const PROBE_BUDGET_MS =
  PROBE_ATTEMPTS * PROBE_TIMEOUT_MS +
  Array.from({ length: Math.max(0, PROBE_ATTEMPTS - 1) }, (_, gap) =>
    PROBE_BACKOFF_MS[Math.min(gap, PROBE_BACKOFF_MS.length - 1)]
  ).reduce((total, ms) => total + ms, 0);

export type ProbeOutcome = "ok" | "answered" | "no-answer";

/**
 * The phase machine, pure so the transition can be asserted without a browser.
 *
 * `answered` means something replied at all -- including a 4xx/5xx or a proxy error page. That is not a
 * machine waking up, so it must not be described as one; only silence that could still become an answer is
 * `warming`, and only after the bound is it `unreachable`.
 */
export function nextPhase(current: BackendPhase, outcome: ProbeOutcome, attempt: number): BackendPhase {
  if (outcome === "ok") return "ready";
  if (outcome === "answered") return "unreachable";
  void current;
  return attempt < PROBE_ATTEMPTS ? "warming" : "unreachable";
}

/**
 * The full sentence, for the place that has room for it.
 *
 * The words belong to the locale owner like every other reader-facing line; this module owns the *phase*, and
 * passes the attempt count and its bound in as arguments. A sentence kept here would render English under the
 * 中文 switch, which is the defect R-13 exists to remove.
 */
export function probeCopy(phase: BackendPhase, attempt: number, locale: Locale): string {
  if (phase === "ready") return t(locale, "probe.ready");
  if (phase === "probing") return t(locale, "probe.probing");
  if (phase === "warming")
    return t(locale, "probe.warming")
      .replace("{attempt}", String(attempt))
      .replace("{total}", String(PROBE_ATTEMPTS));
  return t(locale, "probe.unreachable");
}

/**
 * The same phase in header-width words.
 *
 * The dot lives in a bar that must not overflow at 390 px (the regression tour measures exactly that), so the
 * sentence above goes in `title` and the page-level notice, while the ambient indicator stays short -- short,
 * but still text: a colour alone is not a status (web plan R-13).
 */
export function probeShortLabel(phase: BackendPhase, attempt: number, locale: Locale): string {
  if (phase === "ready") return t(locale, "probe.shortReady");
  if (phase === "probing") return t(locale, "probe.shortProbing");
  if (phase === "warming")
    return t(locale, "probe.shortWarming")
      .replace("{attempt}", String(attempt))
      .replace("{total}", String(PROBE_ATTEMPTS));
  return t(locale, "probe.shortUnreachable");
}

type Listener = () => void;

type Snapshot = { phase: BackendPhase; attempt: number };

let snapshot: Snapshot = { phase: "probing", attempt: 0 };
const listeners = new Set<Listener>();
let started = false;

function publish(next: Snapshot): void {
  snapshot = next;
  for (const listener of listeners) listener();
}

function subscribe(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function getSnapshot(): Snapshot {
  return snapshot;
}

function getServerSnapshot(): Snapshot {
  return { phase: "probing", attempt: 0 };
}

function delay(ms: number): Promise<void> {
  return new Promise((resolveDelay) => {
    setTimeout(resolveDelay, ms);
  });
}

async function oneProbe(onSilent: () => void): Promise<ProbeOutcome> {
  // The wait is explained while it is happening, not after a whole attempt has timed out: an 18 s per-attempt
  // ceiling buys the coverage a 92.8 s cold start needs, but publishing `warming` only when that attempt ends
  // would leave the visitor staring at "Checking API…" for 18 seconds. So the attempt stays in flight and a
  // short silence timer repaints it. A ready instance answers inside the hint window and never sees this fire.
  const hint = setTimeout(onSilent, PROBE_SILENCE_HINT_MS);
  try {
    const res = await fetch(apiUrl("/health"), { cache: "no-store", signal: AbortSignal.timeout(PROBE_TIMEOUT_MS) });
    return res.ok ? "ok" : "answered";
  } catch {
    return "no-answer";
  } finally {
    clearTimeout(hint);
  }
}

async function probeSequence(): Promise<void> {
  for (let attempt = 1; attempt <= PROBE_ATTEMPTS; attempt += 1) {
    const outcome = await oneProbe(() => {
      // Only a request that is genuinely outstanding may be described as a wake-up, and only the first time
      // through: once the reader has been told, re-publishing the same phase would churn every subscriber.
      if (snapshot.phase === "probing") publish({ phase: "warming", attempt });
    });
    const phase = nextPhase(snapshot.phase, outcome, attempt);
    publish({ phase, attempt });
    if (phase === "ready" || phase === "unreachable") return;
    await delay(PROBE_BACKOFF_MS[Math.min(attempt - 1, PROBE_BACKOFF_MS.length - 1)]);
  }
}

/** Start the bounded probe. Repeat calls are ignored: one page, one health request sequence. */
export function refreshBackendProbe(): void {
  if (started) return;
  started = true;
  void probeSequence();
}

/** Re-run the bounded sequence after a failure. Returns false when the probe is already running. */
export function retryBackendProbe(): boolean {
  if (started && (snapshot.phase === "warming" || snapshot.phase === "probing")) return false;
  publish({ phase: "probing", attempt: 0 });
  void probeSequence();
  return true;
}

/** Reactive read of the shared probe: every consumer sees one sequence, not one fetch each. */
export function useBackendProbe(): { phase: BackendPhase; attempt: number; copy: string; retry: () => void } {
  const locale = useLocale();
  const value = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  useEffect(() => {
    refreshBackendProbe();
  }, []);
  return useMemo(
    () => ({
      phase: value.phase,
      attempt: value.attempt,
      copy: probeCopy(value.phase, value.attempt, locale),
      retry: () => {
        retryBackendProbe();
      },
    }),
    [value, locale]
  );
}
