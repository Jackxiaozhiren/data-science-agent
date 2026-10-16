import { API_BASE_URL } from "@/lib/api";

// R-15's client half of consent. `NEXT_PUBLIC_*` is inlined by the bundler, so a bundle that was not built
// with this value literally "on" compiles `COUNTING` to false and cannot reach the network at all -- which is
// the difference between a counter that asks and a counter that apologises afterwards. The API gates a second
// time on its own DSA_TELEMETRY, so both halves have to be chosen deliberately.
const COUNTING = process.env.NEXT_PUBLIC_TELEMETRY === "on";

// The labels the published vocabulary declares for `arrival`. A path outside this map is dropped here rather
// than posted and refused by the server, so adding a route cannot widen what the event means by accident --
// product_events.json stays the place a new label has to be declared first.
const ARRIVAL_LABELS: Record<string, "landing" | "datasets"> = {
  "/": "landing",
  "/datasets": "datasets",
};

export function arrivalLabel(pathname: string): "landing" | "datasets" | null {
  return ARRIVAL_LABELS[pathname] ?? null;
}

/** Report one page view, if this build was made to count them. Never awaited, never retried. */
export function recordArrival(pathname: string): void {
  if (!COUNTING) return;
  const page = arrivalLabel(pathname);
  if (!page) return;
  // A counter is not worth a broken page: no thrown error may reach a reader's console or a render, and no
  // failure is queued for later. The path itself never leaves the browser -- only the short label above.
  void fetch(`${API_BASE_URL}/api/v1/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ event: "arrival", payload: { page } }),
  }).catch(() => {});
}
