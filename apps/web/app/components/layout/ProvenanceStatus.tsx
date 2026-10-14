"use client";

import { cn } from "@/lib/utils";
import { describeReasoningMode, describeStorage, useBuildProvenance } from "@/lib/buildProvenance";

/**
 * Persistent provenance, beside the API status dot in the header and in the footer.
 *
 * Renders nothing until `/version` answers: a placeholder would read as a claim about the build, and the
 * whole point of the figures here is that they come from the process that produced the result. The storage
 * marker appears only when the API says the instance writes to throwaway storage, so a durable deployment
 * is not shown a warning about durability.
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
  const storage = provenance.storage ? describeStorage(provenance.storage) : null;
  if (!mode && !provenance.version && !storage) return null;

  // The marker's own word leads the accessible name: `aria-label` replaces the visible text, so a name that
  // carried only the long explanation would leave the short label -- the one thing a sighted reader sees --
  // unspoken. `title` keeps the same string so hover and screen reader agree.
  const label = [
    storage ? `${storage.short}. ${storage.detail}` : null,
    mode ? `${mode.label}. ${mode.detail}` : null,
  ]
    .filter((part): part is string => part !== null)
    .join(" ");
  const fallback = `Build ${provenance.version ?? "unknown"}`;
  return (
    <span
      role="status"
      title={label || fallback}
      aria-label={label || fallback}
      className={cn(
        "inline-flex max-w-[15rem] items-center gap-1.5 truncate rounded-full border border-zinc-200 bg-white px-2.5 py-1 text-xs text-zinc-600",
        className
      )}
    >
      {mode ? <span className="truncate">{mode.short}</span> : null}
      {storage ? <span className="shrink-0 text-amber-700">{storage.short}</span> : null}
      {showVersion && provenance.version ? (
        <span className="shrink-0 font-mono text-zinc-500">build {provenance.version}</span>
      ) : null}
    </span>
  );
}
