// The one owner of "what is the backend doing right now".
//
// Three places used to answer that question alone: the header dot fetched `/health` once and had two
// colours, each page inferred "down" from its own rejected request, and an empty list could mean either a
// new account or a dead API (web plan B3/B4). The case none of them described is the common one on a free
// instance: the first request hangs for tens of seconds while the machine wakes. Measured on the hosted
// demo on 2026-10-13 -- `GET /health` answered 200 after **44.5 s** (output/lane-c capture log). So
// "nothing has answered yet" is a real third state, it is what a first-time visitor actually sees, and
// calling it "unreachable" loses the visitor.
//
// The budget below is that measurement, not a guess: one short first attempt so the waiting state appears
// quickly, then growing waits that add up to roughly the observed wake-up time.

import { useEffect, useMemo, useSyncExternalStore } from "react";

import { apiUrl } from "@/lib/api";

export type BackendPhase = "probing" | "warming" | "ready" | "unreachable";

/** Per-attempt ceiling. A sleeping instance hangs rather than refusing, so this is what detects it. */
export const PROBE_TIMEOUT_MS = 4000;
/** Attempts are bounded on purpose: an unbounded retry is indistinguishable from a hang. */
export const PROBE_ATTEMPTS = 4;
/** Waits between attempts; the sum lands near the 44.5 s cold start measured above. */
export const PROBE_BACKOFF_MS = [3000, 6000, 12000] as const;

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

/** The full sentence, for the place that has room for it. */
export function probeCopy(phase: BackendPhase, attempt: number): string {
  if (phase === "ready") return "API connected";
  if (phase === "probing") return "Checking API…";
  if (phase === "warming") return (`Demo waking up — the free instance sleeps when idle, so the first request can take about a minute. Attempt ${attempt} of ${PROBE_ATTEMPTS}.`);
  return "API unreachable — nothing answered. Check that the API is running, or retry.";
}

/**
 * The same phase in header-width words.
 *
 * The dot lives in a bar that must not overflow at 390 px (the regression tour measures exactly that), so
 * the sentence above goes in `title` and the page-level notice, while the ambient indicator stays short --
 * short, but still text: a colour alone is not a status (web plan R-13).
 */
export function probeShortLabel(phase: BackendPhase, attempt: number): string {
  if (phase === "ready") return "API up";
  if (phase === "probing") return "Checking…";
  if (phase === "warming") return `Waking… ${attempt}/${PROBE_ATTEMPTS}`;
  return "API unreachable";
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

async function oneProbe(): Promise<ProbeOutcome> {
  try {
    const res = await fetch(apiUrl("/health"), { cache: "no-store", signal: AbortSignal.timeout(PROBE_TIMEOUT_MS) });
    return res.ok ? "ok" : "answered";
  } catch {
    return "no-answer";
  }
}

async function probeSequence(): Promise<void> {
  for (let attempt = 1; attempt <= PROBE_ATTEMPTS; attempt += 1) {
    const outcome = await oneProbe();
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
  const value = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  useEffect(() => {
    refreshBackendProbe();
  }, []);
  return useMemo(
    () => ({
      phase: value.phase,
      attempt: value.attempt,
      copy: probeCopy(value.phase, value.attempt),
      retry: () => {
        retryBackendProbe();
      },
    }),
    [value]
  );
}
