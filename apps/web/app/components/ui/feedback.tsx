import * as React from "react";
import { cn } from "@/lib/utils";

// shadcn/ui Skeleton — https://ui.shadcn.com/docs/components/skeleton
function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div aria-hidden className={cn("animate-pulse rounded-md bg-zinc-100", className)} {...props} />;
}

// shadcn/ui Progress — https://ui.shadcn.com/docs/components/progress
function Progress({
  value = 0,
  className,
  indicatorClassName,
}: {
  value?: number;
  className?: string;
  indicatorClassName?: string;
}) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(clamped)}
      className={cn("h-2 w-full overflow-hidden rounded-full bg-zinc-100", className)}
    >
      <div
        className={cn("h-full rounded-full bg-emerald-500 transition-all", indicatorClassName)}
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}

// shadcn/ui Separator — https://ui.shadcn.com/docs/components/separator
function Separator({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div role="separator" aria-orientation="horizontal" className={cn("h-px w-full bg-zinc-200", className)} {...props} />;
}

export { Skeleton, Progress, Separator };
