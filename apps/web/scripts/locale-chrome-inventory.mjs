#!/usr/bin/env node
// R-13 closure inventory, parsed rather than scanned.
//
// Every previous count in this lane came from a line-matching scan, and the scan is blind in two directions it
// did not advertise: a JSX text node wrapped over three lines never matches a per-line pattern, and a string
// attribute is not a text node at all. Both were hit for real -- "No runs match -- adjust the search or status
// filter." spans lines in RunsTable and no scan ever named it. So this walks the TypeScript AST: every JsxText,
// every string-literal attribute, and every chunk of a template literal, each classified by the element it sits
// in (monospace technical text is a different decision from chrome) and by how wordy it is.
//
// It reports; it does not decide. Triage is the human/lane's job, but the *denominator* is now structural.
import { readdirSync, readFileSync, statSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

import {
  DATA_IN_CHROME,
  IDENTIFIERS,
  LOOKS_LIKE_CODE,
  PROTOCOL_TOKENS,
} from "./locale-chrome-rules.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = join(here, "..", "..", "..");
const require = createRequire(join(here, "noop.js"));
const ts = require("typescript");

// Two roots, not one: the modules under `lib` word the persistent status area, the footer and the run badge, and
// a literal that reaches the page through `describeStorage()` is as reader-facing as one in a `.tsx`. The old
// single root was how four English strings in `buildProvenance.ts` stayed outside the measurement entirely. The
// dictionary itself is excluded -- it is the owner, not a page.
const APP_ROOTS = [join(repoRoot, "apps/web/app"), join(repoRoot, "apps/web/lib")];
const LOCALE_TS = join(repoRoot, "apps/web/lib/locale.ts");

function* walk(dir) {
  for (const name of readdirSync(dir)) {
    const p = `${dir}/${name}`;
    if (statSync(p).isDirectory()) yield* walk(p);
    else if ((p.endsWith(".tsx") || p.endsWith(".ts")) && p !== LOCALE_TS) yield p;
  }
}

// Attributes that carry a string a visitor or a screen reader is handed. Anything not listed here whose value is
// a bare string is an implementation detail (className, href, variant, ...), so it is skipped. `error` and
// `success` are deliberately absent: in this app they are the keys of a variant-to-stylesheet map, and counting
// them reported Tailwind class strings as copy.
const READER_ATTRS = new Set([
  "title", "description", "eyebrow", "label", "placeholder", "caption", "message", "hint",
  "alt", "aria-label", "header", "body", "text", "emptyText", "summary",
  "subtitle", "heading", "tooltip", "short", "detail",
]);
const SKIP_ATTRS = new Set(["className", "key", "href", "id", "type", "variant", "size", "color", "aria-hidden"]);

// The dictionary is the closure test: a value that already exists as a dictionary string is not an orphan.
const dictValues = new Set();
const dictKeys = new Set();
const src = readFileSync(LOCALE_TS, "utf8");
// `\s*` after the colon is load-bearing: the formatter puts a long value on the line after its key, and a
// pattern requiring `": "` on one line silently omits exactly the sentences the duplicate check most needs to
// recognise -- which is how `failures.descBody` and fifteen other owned strings read as "not in the dictionary".
for (const m of src.matchAll(/"([^"]+)"\s*:\s*"((?:[^"\\]|\\.)*)"/g)) { dictValues.add(m[2]); dictKeys.add(m[1]); }

const findings = [];
const keyRefs = [];
const assembledRefs = [];
const census = { developerThrow: 0, command: 0, classList: 0 };
for (const file of APP_ROOTS.flatMap((root) => [...walk(root)])) {
  const text = readFileSync(file, "utf8");
  const sf = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  // A page's own helper can take the reader slot by position -- `metric(a, b, "Status", pick)` hands its label
  // straight into a rendered row. Without the parameter names this file cannot tell that argument from any
  // other, and the whole row-label set of /runs/compare went unreported.
  const fnParams = new Map();
  for (const stmt of sf.statements) {
    if (ts.isFunctionDeclaration(stmt) && stmt.name) {
      fnParams.set(stmt.name.getText(sf), stmt.parameters.map((p) => p.name.getText(sf)));
    }
    if (ts.isVariableStatement(stmt)) {
      for (const d of stmt.declarationList.declarations) {
        const init = d.initializer;
        if (init && (ts.isArrowFunction(init) || ts.isFunctionExpression(init)) && ts.isIdentifier(d.name)) {
          fnParams.set(d.name.getText(sf), init.parameters.map((p) => p.name.getText(sf)));
        }
      }
    }
  }
  const stack = [];
  function visit(node) {
    stack.push(node);
    const line = sf.getLineAndCharacterOfPosition(node.getStart(sf)).line + 1;
    const mono = stack.some(
      (n) =>
        ts.isJsxElement(n) &&
        ["code", "pre", "kbd", "samp"].includes(n.openingElement.tagName.getText(sf))
    );
    if (ts.isJsxText(node)) {
      const raw = node.getText(sf).replace(/\{\/\*[\s\S]*?\*\//g, "").trim();
      if (raw) push(line, "jsx", raw, mono);
    } else if (ts.isStringLiteral(node)) {
      const slot = keySlotOf(stack, sf, fnParams);
      const ctx = slot ? null : contextOf(stack, sf, fnParams);
      if (slot) {
        keyRefs.push({ file: relative(join(repoRoot, "apps/web"), file), line, text: node.text, via: slot });
      } else if (ctx === "reader" || ctx === "text") {
        // `text` as well as `reader`: a literal in a JSX expression container -- `{notify ? "Notifying" :
        // "Notify me"}`, `{tc.error ?? "Unknown error"}` -- is handed to the reader exactly like an attribute
        // value is, and reading only attributes is how three strings on the run report went unreported.
        push(line, "attr", node.text, mono);
      } else if (ctx === "other") {
        // Only `other`: `skip` is how className and module specifiers arrive, and a bucket holding 720 Tailwind
        // strings is a bucket nobody reads.
        assembled(line, node.text);
      }
    } else if (ts.isTemplateHead(node) || ts.isTemplateMiddle(node) || ts.isTemplateTail(node) || ts.isNoSubstitutionTemplateLiteral(node)) {
      const kind = contextOf(stack, sf, fnParams);
      const raw = node.text.trim();
      // A template chunk in a `cn(...)` call or a className attribute is styling, not copy; the previous
      // version of this scan counted those as reader-facing text and reported 89 when the real number was lower.
      if (raw && (kind === "reader" || kind === "text")) push(line, kind === "text" ? "tpl-jsx" : "tpl", raw, mono);
      else if (raw && kind === "other") assembled(line, raw);
    }
    ts.forEachChild(node, visit);
    stack.pop();
  }
  // A sentence built somewhere the reader-slot rules cannot see -- assigned to a variable, thrown, passed to
  // setState -- still reaches the page (`setErr(\`Could not reach the DSA API at ${url}\`)` is rendered as the
  // failure notice), and three such sentences went unnoticed until a hand-written regex found them. So they are
  // reported, never silently dropped: this bucket is a census to adjudicate, not a verdict, and it prints its own
  // size so an empty list can be told apart from a broken predicate.
  function assembled(line, value) {
    const cleaned = value.replace(/\s+/g, " ").trim();
    // Three space-separated words carrying letters. A slash test would count `@/app/components/ui/button` as
    // three words and the census would be imports again.
    const words = cleaned.split(" ").filter((w) => /[A-Za-z]{2,}/.test(w));
    if (words.length < 3) return;
    if (dictValues.has(cleaned) || dictKeys.has(cleaned)) return;
    const rel = relative(join(repoRoot, "apps/web"), file);
    // Three shapes reach this bucket and none of them is copy: a command line a reviewer copies out (a command
    // is not a sentence), a utility class list, and a developer-facing error thrown by a component primitive.
    // They are counted, not dropped, so the census line still names what it excluded.
    if (stack.some((n) => ts.isThrowStatement(n))) {
      census.developerThrow += 1;
      return;
    }
    if (/(^|\s)(uv|npx|npm|pnpm|git|python3?|docker|curl|node)(\s|$)/.test(cleaned) || cleaned.includes(" --")) {
      census.command += 1;
      return;
    }
    if (words.every((w) => /^[a-z0-9\-.:/[\]%#()_&]+$/.test(w)) && words.filter((w) => w.includes("-")).length >= 3) {
      census.classList += 1;
      return;
    }
    assembledRefs.push({ file: rel, line, text: cleaned });
  }
  function push(line, kind, value, mono) {
    const cleaned = value.replace(/\s+/g, " ");
    if (!cleaned) return;
    if (dictKeys.has(cleaned)) return; // a key name carried in a data array, not copy
    // A value the dictionary already owns is NOT silently dropped: a page that keeps its own copy of a string
    // the dictionary carries is the second-owner drift R-13 exists to prevent, and the first version of this
    // scan exempted it -- which is how /failures went on rendering its own "Evaluation · Step 3" eyebrow.
    if (dictValues.has(cleaned)) { findings.push({ file: relative(join(repoRoot, "apps/web"), file), line, kind: "dup", mono, text: cleaned }); return; }
    findings.push({ file: relative(join(repoRoot, "apps/web"), file), line, kind, mono, text: cleaned });
  }
  visit(sf);
}

function contextOf(stack, sf, fnParams) {
  for (let i = stack.length - 2; i >= 0; i--) {
    const n = stack[i];
    if (ts.isBinaryExpression(n)) {
      // `"saved"` in `saving === "saved"` is a state machine's key, not a word the reader sees. Reading JSX
      // expression containers as prose (correct, and how `Notify me` was found) also sweeps up every compared
      // operand, so the operator decides rather than a list of words.
      const op = n.operatorToken.getText(sf);
      if (op === "===" || op === "!==" || op === "==" || op === "!=") return "code-token";
    }
    if (ts.isCaseClause(n) || ts.isDefaultClause(n)) return "code-token";
    if (ts.isAsExpression(n) && n.type.getText(sf).trim() === "const") return "code-token";
    // `["all", "ok", "error"] as const` is a closed set of state ids -- every `as const` in this app is one,
    // from the upload queue's statuses to the button variants. The words a reader sees for them come from the
    // dictionary, one line below.
    if (ts.isJsxAttribute(n)) {
      const name = n.name.getText(sf);
      if (SKIP_ATTRS.has(name)) return "skip";
      return READER_ATTRS.has(name) || name.startsWith("aria-") ? "reader" : "skip";
    }
    if (ts.isPropertyAssignment(n)) {
      const key = n.name.getText(sf).replace(/^["']|["']$/g, "");
      return READER_ATTRS.has(key) ? "reader" : "skip";
    }
    if (ts.isCallExpression(n)) {
      const callee = n.expression.getText(sf);
      if (/(^|\.)cn$|(^|\.)classNames$/.test(callee)) return "skip";
      // A string that is a `t(locale, "…")` argument is a dictionary key, not copy the page owns.
      if (/^t$/.test(callee)) return "skip";
      // `.replace("T", " ")`, `.split("/")`, `.includes(x)` -- an argument to a builtin method is an operand of
      // a computation, however it got there. Four `T`s came from timestamp formatting and read as English.
      // Directness matters: `stripHtml(String(x ?? "Unknown error")).slice(0, 500)` ends in a method call too,
      // and the literal inside it is the sentence a reader sees.
      const direct = n.arguments.includes(stack[i + 1]);
      if (direct && /\.(replace|split|join|includes|indexOf|lastIndexOf|startsWith|endsWith|padStart|padEnd|slice|at|some|every|find|findIndex|filter|map|push|add|set|get|has|test|match|search|concat|repeat|localeCompare)\s*$/.test(callee)) {
        return "code-token";
      }
      const params = fnParams?.get(callee);
      if (params) {
        const at = n.arguments.indexOf(stack[i + 1]);
        if (at >= 0 && READER_ATTRS.has(params[at])) return "reader";
      }
      continue;
    }
    if (ts.isJsxExpression(n)) {
      const parent = stack[i - 1];
      const inChildren =
        parent && (ts.isJsxElement(parent) ? parent.children.includes(n) : ts.isJsxSelfClosingElement(parent));
      if (inChildren) return "text";
      continue;
    }
  }
  return "other";
}

// Is this literal a *dictionary key* rather than a sentence? `t(locale, "x")` and a same-file helper whose
// parameter is named `key` (the compare page's `metric(a, b, "cmp.metricStatus", …)`) both mean "look this up".
// The point is not classification tidiness: when a key is absent, `t()` renders the loud marker `⟨key⟩` instead
// of words, and the tour only reads the static routes -- so a mistyped key that only surfaces on a run report
// would need a live seeded stack to notice. This notices without one.
function keySlotOf(stack, sf, fnParams) {
  for (let i = stack.length - 2; i >= 0; i--) {
    const n = stack[i];
    if (ts.isJsxAttribute(n) || ts.isJsxElement(n) || ts.isJsxSelfClosingElement(n)) return null;
    // `f === "ok" ? "insp.filterOk" : "insp.filterAll"` -- the compared value is a state id and the *branches*
    // are keys. Only a branch position keeps the walk alive.
    if (ts.isBinaryExpression(n)) return null;
    if (ts.isConditionalExpression(n) && n.whenTrue !== stack[i + 1] && n.whenFalse !== stack[i + 1]) return null;
    if (ts.isCallExpression(n)) {
      const at = n.arguments.indexOf(stack[i + 1]);
      const callee = n.expression.getText(sf);
      if (/^t$/.test(callee)) return at >= 1 ? "t(locale, …)" : null;
      const params = fnParams?.get(callee);
      if (at >= 0) return params && params[at] === "key" ? "key parameter" : null;
    }
  }
  return null;
}

const dups = findings.filter((f) => f.kind === "dup");
const wordy = findings.filter((f) => f.kind !== "dup" && (f.text.match(/[A-Za-z]{2,}/g) ?? []).length >= 2 && !f.mono);
const single = findings.filter((f) => f.kind !== "dup" && !wordy.includes(f) && !f.mono);
const monospace = findings.filter((f) => f.mono);

// The bucket that used to be a count is now a decision per entry. `single-token=118` told a reader nothing: it
// mixed `{id}` -- whitespace around an interpolation, no word in it -- with `aria-live="polite"`, with `/metrics`,
// and with `Saved.`, which is real English on a 中文 screen. Each literal gets exactly one class, and only
// `prose` asks for work. A class list that could not fail would be decoration, so the run exits non-zero while
// `prose` or a second-owner duplicate is still on the page.
function classify(f) {
  const bare = f.text.replace(/[·::()\s/|]+$/u, "").replace(/^[·:—()\s/|]+/u, "");
  const key = bare.toLowerCase();
  if (/^(\{[^{}]*\}\s*)+$/.test(f.text.trim())) return "interpolation";
  if (!/[A-Za-z]/.test(f.text)) return "punctuation";
  if (/[A-Z][A-Z0-9_]{2,}/.test(bare) && !/[a-z]/.test(bare)) return "api-vocabulary";
  if (/^[a-z]+[A-Z][A-Za-z]*$/.test(bare)) return "state-token";
  if (PROTOCOL_TOKENS.has(key) || PROTOCOL_TOKENS.has(f.text.toLowerCase())) return "protocol-token";
  if (IDENTIFIERS.has(key) || IDENTIFIERS.has(f.text.toLowerCase())) return "declared-identifier";
  if (LOOKS_LIKE_CODE.test(f.text) || DATA_IN_CHROME.test(f.text)) return "endpoint-or-data";
  return "prose";
}

const classes = new Map();
const prose = [];
for (const f of [...wordy, ...single]) {
  const cls = classify(f);
  classes.set(cls, (classes.get(cls) ?? 0) + 1);
  if (cls === "prose") prose.push(f);
}

const byFile = new Map();
for (const f of prose) {
  if (!byFile.has(f.file)) byFile.set(f.file, []);
  byFile.get(f.file).push(f);
}
console.log("=== prose the page owns and the dictionary does not (the actionable bucket) ===");
for (const [file, list] of [...byFile.entries()].sort()) {
  console.log(`\n${file}  (${list.length})`);
  for (const f of list) console.log(`   ${f.line} [${f.kind}] ${JSON.stringify(f.text.slice(0, 120))}`);
}
console.log(`\n=== second-owner duplicates (page keeps a copy the dictionary owns) ===`);
for (const f of dups) console.log(`   ${f.file}:${f.line} ${JSON.stringify(f.text.slice(0, 90))}`);
console.log(`duplicates=${dups.length}`);

const tally = [...classes.entries()].sort((a, b) => b[1] - a[1]).map(([c, n]) => `${c}=${n}`).join(" ");
console.log(`\ntotals: all=${findings.length} monospace/data=${monospace.length} | classes: ${tally}`);
console.log(`actionable: prose=${prose.length} duplicates=${dups.length}`);

if (process.env.R13J_SINGLE) {
  const tokens = new Map();
  for (const f of single) tokens.set(f.text, (tokens.get(f.text) ?? 0) + 1);
  console.log("\n=== single-token, non-monospace (grouped by text, count) ===");
  for (const [t, n] of [...tokens.entries()].sort((a, b) => b[1] - a[1])) console.log(`  ${n}x ${JSON.stringify(t)}`);
}

const unknownKeys = keyRefs.filter((k) => !dictKeys.has(k.text));
console.log(`\n=== sentences assembled outside any reader position (report only: adjudicate) ===`);
for (const a of assembledRefs) console.log(`   ${a.file}:${a.line} ${JSON.stringify(a.text.slice(0, 110))}`);
console.log(`assembled=${assembledRefs.length} excluded: developer-throw=${census.developerThrow} command=${census.command} class-list=${census.classList}`);
console.log(`\n=== dictionary keys the pages ask for ===`);
console.log(`keys referenced=${keyRefs.length} unknown=${unknownKeys.length}`);
for (const k of unknownKeys) console.log(`   ${k.file}:${k.line} ${JSON.stringify(k.text)} via ${k.via}`);

if (prose.length || dups.length || unknownKeys.length) {
  console.error(
    `\nlocale inventory is NOT closed: ${prose.length} prose literal(s), ${dups.length} duplicate(s), ` +
      `${unknownKeys.length} unknown key(s) still on the pages.`
  );
  process.exitCode = 1;
}
