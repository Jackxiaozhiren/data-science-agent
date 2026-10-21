// The one owner of the rule "which words on a page belong to the interface".
//
// Two runners use it: `locale-chrome-acceptance.mjs` against a live, seeded instance (every route, including the
// ones that need a real run id, and every region including table column heads, which only exist once there are
// rows), and `regression.mjs` -- the CI web job -- against the static routes with no backend. Duplicating the
// lists is how the two would drift into disagreeing, which is the failure this whole lane exists to prevent, so
// the lists live here and a contract test requires both runners to import them.
//
// The rule is about *regions*, not about page text. A run's report, a dataset's column names and an uploaded
// file's title are bytes the product does not own: they render in whatever language the run produced, which is
// the plan's rule and the right one. So a leak is a Latin-only string inside a region the interface writes --
// a column head, an option label, a form label, a summary, a heading, a button, the shell's links -- and the
// data regions (`td`, `<code>`, the report body) are never examined.
export const CHROME_SELECTOR = [
  "th", "option", "summary", "label", "h1", "h2", "h3", "button", "[role=tab]", "nav a", "header a", "footer a",
].join(", ");

export const HAS_CJK = /[\u3400-\u9fff]/;

// Things the product shows in their own spelling: protocol and endpoint names, statistical method names, the
// field names a payload carries, and the language switch's endonyms ("English" is how English writes English).
export const IDENTIFIERS = new Set([
  "mcp", "sha-256", "sse", "api", "url", "id", "dsa", "github", "github ↗", "/health", "/version", "/metrics",
  "a–f", "10-dim", "ci / mcnemar", "+ wilcoxon", "f01–f15", "l0–l5", "w2–w10", "get", "post",
  "run_id", "dataset_id", "evidence_id", "sha256 ·", "provider", "mode", "model", "dsa ui", "http", "json-rpc",
  "tools/list", "tools/call", "session #", "v1", "v2", "ok", "—", "·", "×", "→", "%", "english",
  // Provider names arrive from the API's own list, so an option that says `ollama` is showing data.
  "ollama", "openai", "openai-compat",
  // Units and pane letters, written identically in both languages: a duration is `230ms` or `12s` on a 中文
  // page too, and the compare panes are named A and B there as they are here.
  "ms", "s", "kb", "mb", "vs", "a ·", "b ·", "a:", "b:", "a", "b",
  // The model name the settings field shows as its own example, and the risk classes the MCP tool list carries
  // as API vocabulary (`SAFE_READ` etc. are matched by shape, not listed here).
  "qwen3:8b",
  // The evaluation ladder is named L0-L5 in both languages, and a digest is labelled `sha256` either way.
  "l", "sha256",
]);

// Data that a chrome region can legitimately carry: an uploaded file name in an <option> or a heading, an
// entity id in parentheses, an endpoint path, a protocol version stamp.
export const DATA_IN_CHROME =
  /(^|\s)[\w.-]+\.(csv|xlsx|xls|parquet|json|md|tsv)(\s|$)|\([0-9a-f]{6,}\)|\/(mcp|api|health|version|metrics|evidence|analysis|datasets)\b|^\s*(GET|POST|PUT|DELETE)\s|20\d\d-\d\d-\d\d/;

export const LOOKS_LIKE_CODE = /[{};=]|\$\(|=>|__|\/api\/|\.py|\.json|\.md|localhost|https?:/;

// Attribute *values* that a browser or a component library defined, not words the product wrote. `aria-live`
// says `polite` in 中文 just as it does in English, and translating it would break the announcement rather than
// translate it. The inventory needs this list because an `aria-*` attribute is otherwise a reader attribute by
// this file's own rule, and every `aria-live="polite"` on every page would then read as an English leak.
export const PROTOCOL_TOKENS = new Set([
  "polite", "assertive", "off", "horizontal", "vertical", "true", "false", "dialog", "alertdialog", "status",
  "separator", "button", "submit", "reset", "none", "presentation", "ltr", "rtl", "grid", "list", "listbox",
  "option", "tab", "tabpanel", "region", "form", "search", "navigation", "contentinfo", "banner", "timer",
  "log", "marquee", "tooltip", "complementary", "main", "article", "img", "text", "password", "email", "tel",
  // aria-current's vocabulary -- which kind of thing is current, not a sentence about it.
  "page", "step", "location", "date", "time", "page-scroll",
]);

/**
 * Partition rendered chrome regions into leaks and exemptions for a 中文 page.
 *
 * Both halves are returned because a pass that only says "0 leaks" hides its own appetite: the exemption count
 * and the CJK share are what show the rule is still looking at real text.
 */
export function classifyChromeRegions(regions) {
  const latin = regions.filter((r) => r.text && !HAS_CJK.test(r.text));
  const leaks = latin
    .filter((r) => !IDENTIFIERS.has(r.text.toLowerCase()))
    .filter((r) => !DATA_IN_CHROME.test(r.text))
    .filter((r) => !LOOKS_LIKE_CODE.test(r.text))
    .filter((r) => r.text.split(/[^\w]+/).some((w) => /^[A-Za-z]{2,}$/.test(w)));
  const exempt = latin.filter((r) => !leaks.includes(r));
  const cjk = regions.filter((r) => HAS_CJK.test(r.text)).length;
  return { leaks, exempt, cjk, total: regions.length };
}
