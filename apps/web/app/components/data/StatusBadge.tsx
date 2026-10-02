import { Badge } from "@/app/components/ui/badge";
import { isInFlightStatus, isTerminalStatus, normalizeStatus } from "@/app/lib/analysisStatus";

// StatusBadge serves run statuses (the vocabulary in @/app/lib/analysisStatus) plus the short
// ok/error words used by tool-call and validation rows, which are a different domain.
export function StatusBadge({ status, className }: { status: string; className?: string }) {
  const n = normalizeStatus(status);
  if (n === "OK" || n === "PASSED" || n === "SUCCESS" || isTerminalStatus(status) && n === "COMPLETED") {
    return <Badge variant="success" className={className}>{status}</Badge>;
  }
  if (n === "FAIL" || n === "ERROR") {
    return <Badge variant="destructive" className={className}>{status}</Badge>;
  }
  if (n === "FAILED" || isInFlightStatus(status) || n === "HUMAN_REVIEW") {
    return (
      <Badge variant="warning" className={className}>
        <span className="size-1.5 animate-pulse rounded-full bg-amber-500" aria-hidden />
        {status}
      </Badge>
    );
  }
  return <Badge variant="secondary" className={className}>{status}</Badge>;
}
