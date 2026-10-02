// The run-status vocabulary, owned here.
//
// The fact itself is `AnalysisStatus` in `packages/agent/src/dsa_agent/state.py`; this array is its
// rendering for the UI. `tests/contract/test_web_analysis_status_vocabulary.py` compares the two sets
// in both directions on every CI run, so adding a status to the enum without classifying it here turns
// the build red instead of quietly rendering the new state as a neutral badge.
//
// Names the backend never emits (`RUNNING`, `PENDING`, `QUEUED`, `STARTED`) are deliberately absent:
// audit §67.1 measured that branching on them made an in-flight run fall through to a grey badge and
// made the trace timeline's active-step branch unreachable.

export const ANALYSIS_STATUSES = [
  "UNDERSTANDING",
  "PLANNING",
  "DATA_PROFILING",
  "ANALYSIS",
  "MODELING",
  "VALIDATION",
  "SYNTHESIS",
  "REPORTING",
  "COMPLETED",
  "FAILED",
  "HUMAN_REVIEW",
] as const;

export type AnalysisStatusValue = (typeof ANALYSIS_STATUSES)[number];

// Terminal: the run has stopped and its report is final.
export const TERMINAL_STATUSES = ["COMPLETED", "FAILED"] as const satisfies readonly AnalysisStatusValue[];

// Still executing. These are the states that must read as "in flight" to a reader.
export const IN_FLIGHT_STATUSES = [
  "UNDERSTANDING",
  "PLANNING",
  "DATA_PROFILING",
  "ANALYSIS",
  "MODELING",
  "VALIDATION",
  "SYNTHESIS",
  "REPORTING",
] as const satisfies readonly AnalysisStatusValue[];

// Paused for a human decision: neither running nor finished, and actionable.
export const REVIEW_STATUS = "HUMAN_REVIEW" satisfies AnalysisStatusValue;

export function normalizeStatus(status: string): string {
  return status.trim().toUpperCase();
}

export function isTerminalStatus(status: string): boolean {
  return (TERMINAL_STATUSES as readonly string[]).includes(normalizeStatus(status));
}

export function isInFlightStatus(status: string): boolean {
  return (IN_FLIGHT_STATUSES as readonly string[]).includes(normalizeStatus(status));
}

export function isReviewStatus(status: string): boolean {
  return normalizeStatus(status) === REVIEW_STATUS;
}
