"use client";

import { cn } from "@/lib/utils";
import { describeReasoningMode, useBuildProvenance } from "@/lib/buildProvenance";

/**
 * Persistent provenance, beside the API status dot in the header and in the footer.
 *
 * Renders nothing until `/version` answers: a placeholder would read as a claim about the build, and the
 * whole point of the two figures here is that they come from the process that produced the result.
 */
export function ProvenanceStatus({
  className,
  showVersion = false,
}: {
  className?: string;
  showVersion?: boolean;
}) {
  const provenance = useBuildProvenance();
  if (provenance.state !== "ready") return null;

  const mode = provenance.reasoningMode ? describeReasoningMode(provenance.reasoningMode) : null;
  if (!mode && !provenance.version) return null;

  const label = mode ? `${mode.label}. ${mode.detail}` : undefined;
  return (
    <span
      role="status"
      title={label}
      aria-label={label ?? `Build ${provenance.version}`}
      className={cn(
        "inline-flex max-w-[15rem] items-center gap-1.5 truncate rounded-full border border-zinc-200 bg-white px-2.5 py-1 text-xs text-zinc-600",
        className
      )}
    >
      {mode ? <span className="truncate">{mode.short}</span> : null}
      {showVersion && provenance.version ? (
        <span className="shrink-0 font-mono text-zinc-500">build {provenance.version}</span>
      ) : null}
    </span>
  );
}
