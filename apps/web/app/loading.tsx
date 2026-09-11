import { CardsSkeleton, TableSkeleton } from "@/app/components/data/States";

export default function Loading() {
  return (
    <div className="space-y-4" aria-label="Loading page" aria-busy="true">
      <div className="space-y-2">
        <div className="h-3 w-24 animate-pulse rounded bg-zinc-200" />
        <div className="h-6 w-64 animate-pulse rounded bg-zinc-200" />
        <div className="h-4 w-full max-w-xl animate-pulse rounded bg-zinc-100" />
      </div>
      <CardsSkeleton />
      <TableSkeleton rows={4} />
    </div>
  );
}
