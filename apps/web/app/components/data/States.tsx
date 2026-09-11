import * as React from "react";
import { AlertTriangle, Inbox, RotateCcw } from "lucide-react";
import { Card, CardContent } from "@/app/components/ui/card";
import { Skeleton } from "@/app/components/ui/feedback";
import { Button } from "@/app/components/ui/button";
import { cn } from "@/lib/utils";

// Unified EmptyState — every list/table reuses this, never a bare sentence.
export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col items-center rounded-xl border border-dashed border-zinc-200 bg-zinc-50/60 px-6 py-10 text-center", className)}>
      <div className="flex size-10 items-center justify-center rounded-full bg-white shadow-sm" aria-hidden>
        {icon ?? <Inbox className="size-5 text-zinc-400" />}
      </div>
      <p className="mt-3 font-medium">{title}</p>
      {description && <p className="mt-1 max-w-sm text-sm leading-6 text-zinc-600">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

// Unified ErrorState — one human line, never dump raw HTML bodies.
export function ErrorState({
  message,
  retry,
  diagnostics,
  className,
}: {
  message: string;
  retry?: () => void;
  diagnostics?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("rounded-xl border border-red-200 bg-red-50/60 p-4", className)} role="alert">
      <div className="flex items-start gap-2">
        <AlertTriangle className="mt-0.5 size-4 shrink-0 text-red-600" aria-hidden />
        <div className="min-w-0">
          <p className="text-sm font-medium text-red-800">Something went wrong</p>
          <p className="mt-1 break-words text-sm leading-6 text-red-700">{message}</p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            {retry && (
              <Button variant="secondary" size="sm" onClick={retry}>
                <RotateCcw className="size-3" aria-hidden /> Retry
              </Button>
            )}
            {diagnostics}
          </div>
        </div>
      </div>
    </div>
  );
}

// Unified Skeleton blocks for loading.tsx + client loading states.
export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-2" aria-label="Loading table">
      <Skeleton className="h-8 w-full" />
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-10 w-full" />
      ))}
    </div>
  );
}

export function CardsSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="grid gap-4 md:grid-cols-3" aria-label="Loading">
      {Array.from({ length: count }).map((_, i) => (
        <Card key={i}>
          <CardContent className="space-y-2 p-4 pt-4">
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-6 w-2/3" />
            <Skeleton className="h-3 w-full" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
