"use client";

import { RotateCcw } from "lucide-react";
import { Button } from "@/app/components/ui/button";
import { probeShortLabel, useBackendProbe } from "@/app/lib/backendProbe";
import { cn } from "@/lib/utils";

// The ambient backend indicator. It used to run its own one-shot fetch and had two colours, which left the
// most common first-visit state -- a sleeping instance that has not answered yet -- indistinguishable from
// a broken one. It now reads the shared probe (apps/web/app/lib/backendProbe.ts) and says the phase in
// words, because a dot alone is not a status.
export function ApiStatusDot({ className }: { className?: string }) {
  const { phase, attempt, copy, retry } = useBackendProbe();

  return (
    <span
      title={copy}
      data-api-state={phase}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border border-zinc-200 bg-white px-2.5 py-1 text-xs text-zinc-600",
        className
      )}
    >
      <span
        aria-hidden
        className={cn(
          "size-2 shrink-0 rounded-full",
          phase === "ready"
            ? "bg-emerald-500"
            : phase === "unreachable"
              ? "bg-red-500"
              : "animate-pulse bg-amber-400"
        )}
      />
      <span role="status" aria-live="polite" className="whitespace-nowrap">
        {probeShortLabel(phase, attempt)}
      </span>
      {phase === "unreachable" && (
        <Button
          variant="ghost"
          size="sm"
          className="h-5 gap-1 px-1 text-[11px]"
          onClick={retry}
          aria-label="Retry the API check"
        >
          <RotateCcw className="size-3" aria-hidden />
          Retry
        </Button>
      )}
    </span>
  );
}
