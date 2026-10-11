"use client";

import { Badge } from "@/app/components/ui/badge";
import { describeReasoningMode, useBuildProvenance, type ModeDescription } from "@/lib/buildProvenance";

/**
 * What did the thinking, beside a run's status badge, plus the plain statement of what that excludes.
 *
 * The mode is a property of the API instance this page reads from, not a field stored on the run -- no
 * run record carries its planner yet -- so both pieces are scoped to the instance. Saying "this run used
 * a heuristic" would be a claim the backend cannot support, which is the defect class R-02 removes.
 *
 * Split into two exports because the header's action row is a shrinking flex line: a paragraph in there
 * is how a 390 px viewport gets a horizontal scrollbar.
 */
export function ReasoningModeBadge({ className }: { className?: string }) {
  const mode = useReportedMode();
  if (!mode) return null;
  return (
    <Badge
      variant={mode.modelPlanned ? "secondary" : "warning"}
      title={`${mode.label}. ${mode.detail}`}
      aria-label={`${mode.label}. ${mode.detail}`}
      className={className}
    >
      {mode.label}
    </Badge>
  );
}

/** The exclusion stated in body text, at the same weight as the findings it qualifies. */
export function ReasoningModeNotice() {
  const mode = useReportedMode();
  if (!mode || mode.modelPlanned) return null;
  return (
    <p className="max-w-2xl text-xs leading-5 text-zinc-600" role="note">
      {mode.detail}
    </p>
  );
}

function useReportedMode(): ModeDescription | null {
  const provenance = useBuildProvenance();
  if (provenance.state !== "ready" || !provenance.reasoningMode) return null;
  return describeReasoningMode(provenance.reasoningMode);
}
