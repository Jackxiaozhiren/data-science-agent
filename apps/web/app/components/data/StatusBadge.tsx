import { Badge } from "@/app/components/ui/badge";

function normalize(s: string): string {
  return s.trim().toUpperCase();
}

// Unified StatusBadge: COMPLETED/FAILED/RUNNING + ok/fail + generic states.
export function StatusBadge({ status, className }: { status: string; className?: string }) {
  const n = normalize(status);
  if (n === "COMPLETED" || n === "OK" || n === "PASSED" || n === "SUCCESS") {
    return <Badge variant="success" className={className}>{status}</Badge>;
  }
  if (n === "FAILED" || n === "FAIL" || n === "ERROR") {
    return <Badge variant="destructive" className={className}>{status}</Badge>;
  }
  if (n === "RUNNING" || n === "PENDING" || n === "QUEUED" || n === "STARTED") {
    return (
      <Badge variant="warning" className={className}>
        <span className="size-1.5 animate-pulse rounded-full bg-amber-500" aria-hidden />
        {status}
      </Badge>
    );
  }
  return <Badge variant="secondary" className={className}>{status}</Badge>;
}
