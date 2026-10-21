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

/** Words that name a defect in the analysis itself, rather than a standing limit of the method.
 *
 * The list is bilingual because the run is: a question asked in Chinese produces caveats in Chinese, and the
 * severity of a caveat is decided here. R-13.
 *
 * Each Chinese word is deliberately narrower than its English counterpart. `偏` alone would match 偏好
 * ("preference") and 偏离 ("deviation"), and `混淆` alone matches 混淆矩阵 ("confusion matrix") -- a keyword
 * list that over-matches reproduces the bug this file records above, where the loud tier fired on every
 * report and so taught the reader to skip it.
 */
export const SEVERE_LIMITATIONS = [
  "bias",
  "leak",
  "overfit",
  "confound",
  "spurious",
  "偏见",
  "偏差",
  "泄漏",
  "泄露",
  "过拟合",
  "混杂",
  "伪相关",
];

/**
 * Sentences the product itself writes into a run, in the other language it offers.
 *
 * The graph attaches a fixed caveat to every insight derived from a correlation or a test, and the run page
 * reads that stored value rather than the rendered report -- so without this map a 中文 run shows an English
 * warning in its own panel while its downloaded report says the same thing in Chinese. Matching is on the whole
 * value, never a substring: nothing an analyst or a model wrote is ever rewritten here.
 *
 * `packages/agent/src/dsa_agent/report_export.py` carries the same table for the renderer, and
 * `test_the_limitation_prose_maps_agree` compares the two, because a mapping maintained in two languages and
 * written twice is exactly how the two surfaces start disagreeing.
 */
export const PRODUCT_LIMITATION_TEXT: Record<string, string> = {
  "Association does not imply causation.": "关联不等于因果。",
  "Correlation does not imply causation.": "相关不等于因果。",
  "Check assumptions; association does not imply causation.": "请核对假设；关联不等于因果。",
};

/** The stored caveat, in the language this reader chose. Anything not in the map is already theirs. */
export function limitationText(value: string, locale: "en" | "zh"): string {
  if (locale !== "zh") return value;
  return PRODUCT_LIMITATION_TEXT[value.trim()] ?? value;
}

export type LimitationSeverity = "error" | "warning";

export function limitationSeverity(text: string): LimitationSeverity {
  const lower = text.toLowerCase();
  return SEVERE_LIMITATIONS.some((keyword) => lower.includes(keyword)) ? "error" : "warning";
}
