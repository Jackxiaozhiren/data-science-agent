import * as React from "react";
import { cn } from "@/lib/utils";

// Unified PageHeader: eyebrow (Step narrative) + H1 + description + actions.
export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  className,
}: {
  eyebrow: string;
  title: string;
  description?: string;
  actions?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-wrap items-end justify-between gap-3", className)}>
      <div className="min-w-0">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-zinc-500">{eyebrow}</p>
        <h1 className="mt-1 text-xl font-semibold tracking-tight text-zinc-900">{title}</h1>
        {description && <p className="mt-1 max-w-2xl text-sm leading-6 text-zinc-600">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}
