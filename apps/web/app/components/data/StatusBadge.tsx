"use client";

import { Badge } from "@/app/components/ui/badge";
import { isInFlightStatus, isTerminalStatus, normalizeStatus } from "@/app/lib/analysisStatus";
import { useLocale } from "@/app/lib/LocaleProvider";
import { statusLabel } from "@/lib/locale";

// StatusBadge serves run statuses (the vocabulary in @/app/lib/analysisStatus) plus the short
// ok/error words used by tool-call and validation rows, which are a different domain. A declared
// status reads its label in the visitor's language; anything else -- an "ok" from a tool row, a
// status a future backend adds to the enum -- renders exactly the token it arrived with, because
// labelling a state nobody declared would invent one.
export function StatusBadge({ status, className }: { status: string; className?: string }) {
  const locale = useLocale();
  const label = statusLabel(locale, status);
  const n = normalizeStatus(status);
  if (n === "OK" || n === "PASSED" || n === "SUCCESS" || isTerminalStatus(status) && n === "COMPLETED") {
    return <Badge variant="success" className={className}>{label}</Badge>;
  }
  if (n === "FAIL" || n === "ERROR") {
    return <Badge variant="destructive" className={className}>{label}</Badge>;
  }
  if (n === "FAILED" || isInFlightStatus(status) || n === "HUMAN_REVIEW") {
    return (
      <Badge variant="warning" className={className}>
        <span className="size-1.5 animate-pulse rounded-full bg-amber-500" aria-hidden />
        {label}
      </Badge>
    );
  }
  return <Badge variant="secondary" className={className}>{label}</Badge>;
}
