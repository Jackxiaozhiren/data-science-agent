// One owner for "how loud should this caveat be" -- and the reason the loudest tier is not the causal words.
//
// This list used to live inside `RunInspector.tsx` and included "causal" and "causation". The agent attaches
// `limitation="Association does not imply causation."` to every insight it derives from a correlation or a
// hypothesis test (dsa_agent/graph.py:295, langgraph_graph.py:131), and the tools carry the same sentence as a
// default (`dsa_tools/tools/correlation.py:32`), so the keyword match made the routine disclaimer read as a
// critical finding: every EDA report opened with a red "1 caveat (1 critical)" banner, including the example
// the landing page points at. A warning that fires on every run carries no information, and the reader learns
// to skip it -- which costs the product exactly the attention it wants on a real problem.
//
// Saying "association is not causation" is the product behaving correctly. *Claiming* a causal conclusion is
// a different gate, and it already exists: the `unsupported_claim` validation check, which the run page shows
// in its own panel and which a failing run reports as a failed check, not as a caveat.

/** Words that name a defect in the analysis itself, rather than a standing limit of the method. */
export const SEVERE_LIMITATIONS = ["bias", "leak", "overfit", "confound", "spurious"];

export type LimitationSeverity = "error" | "warning";

export function limitationSeverity(text: string): LimitationSeverity {
  const lower = text.toLowerCase();
  return SEVERE_LIMITATIONS.some((keyword) => lower.includes(keyword)) ? "error" : "warning";
}
