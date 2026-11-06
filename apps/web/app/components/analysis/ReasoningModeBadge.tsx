"use client";

import { Badge } from "@/app/components/ui/badge";
import { describeRunReasoning, type RunReasoning } from "@/lib/buildProvenance";
import { useLocale } from "@/app/lib/LocaleProvider";

/**
 * What did the thinking for *this run*, beside its status badge, plus the plain statement of what that excludes.
 *
 * The mode comes from the run's own `ReasoningRecord`, captured when the graph started, not from `/version`.
 * The distinction is the point of R-02: a page that labelled a run with the mode of the process now serving
 * it would describe a model-produced run as heuristic after an operator flipped `DSA_LLM_MODE`, and the
 * report body below the badge would say the opposite on the same screen. A finished run that recorded
 * nothing says so; a run still in flight says nothing at all, because its record is written a moment after
 * the row and "not recorded" would be a claim about a run that is about to record it.
 *
 * Split into two exports because the header's action row is a shrinking flex line: a paragraph in there
 * is how a 390 px viewport gets a horizontal scrollbar.
 */
type RunProvenanceProps = {
  /** The run's own record, from `state.reasoning`; absent on rows written before the field existed. */
  reasoning?: RunReasoning | null;
  /** The run's status, so a missing record can be told apart from one that has not been written yet. */
  status: string;
  className?: string;
};

export function ReasoningModeBadge({ reasoning, status, className }: RunProvenanceProps) {
  const locale = useLocale();
  const described = describeRunReasoning(reasoning, status, locale);
  if (!described) return null;
  return (
    <Badge
      variant={described.variant}
      title={`${described.label}. ${described.detail}`}
      aria-label={`${described.label}. ${described.detail}`}
      className={className}
    >
      {described.label}
    </Badge>
  );
}

/** The exclusion stated in body text, at the same weight as the findings it qualifies. */
export function ReasoningModeNotice({ reasoning, status }: RunProvenanceProps) {
  const locale = useLocale();
  const described = describeRunReasoning(reasoning, status, locale);
  if (!described || described.modelPlanned) return null;
  return (
    <p className="max-w-2xl text-xs leading-5 text-zinc-600" role="note">
      {described.detail}
    </p>
  );
}
