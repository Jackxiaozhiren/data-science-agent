"use client";

import * as React from "react";
import { apiUrl } from "@/lib/api";
import { cn } from "@/lib/utils";

// Live API status dot: green = reachable, amber = checking, red = down.
export function ApiStatusDot({ className }: { className?: string }) {
  const [state, setState] = React.useState<"checking" | "up" | "down">("checking");

  React.useEffect(() => {
    let cancelled = false;
    fetch(apiUrl("/health"), { cache: "no-store" })
      .then((r) => {
        if (!cancelled) setState(r.ok ? "up" : "down");
      })
      .catch(() => {
        if (!cancelled) setState("down");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const label = state === "up" ? "API connected" : state === "down" ? "API unreachable" : "Checking API";
  return (
    <span
      title={label}
      aria-label={label}
      role="status"
      className={cn("inline-flex items-center gap-1.5 rounded-full border border-zinc-200 bg-white px-2.5 py-1 text-xs text-zinc-600", className)}
    >
      <span
        aria-hidden
        className={cn(
          "size-2 rounded-full",
          state === "up" ? "bg-emerald-500" : state === "down" ? "bg-red-500" : "animate-pulse bg-amber-400"
        )}
      />
      <span className="hidden sm:inline">API</span>
    </span>
  );
}
