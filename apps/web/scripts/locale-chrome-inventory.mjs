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

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = join(here, "..", "..", "..");
const require = createRequire(join(here, "noop.js"));
const ts = require("typescript");

const APP = join(repoRoot, "apps/web/app");
const LOCALE_TS = join(repoRoot, "apps/web/lib/locale.ts");

function* walk(dir) {
  for (const name of readdirSync(dir)) {
    const p = `${dir}/${name}`;
    if (statSync(p).isDirectory()) yield* walk(p);
    else if (p.endsWith(".tsx")) yield p;
  }
}

// Attributes that carry a string a visitor or a screen reader is handed. Anything not listed here whose value is
// a bare string is an implementation detail (className, href, variant, ...), so it is skipped. `error` and
// `success` are deliberately absent: in this app they are the keys of a variant-to-stylesheet map, and counting
// them reported Tailwind class strings as copy.
const READER_ATTRS = new Set([
  "title", "description", "eyebrow", "label", "placeholder", "caption", "message", "hint",
  "alt", "aria-label", "header", "body", "text", "emptyText", "summary",
  "subtitle", "heading", "tooltip",
]);
const SKIP_ATTRS = new Set(["className", "key", "href", "id", "type", "variant", "size", "color", "aria-hidden"]);

// The dictionary is the closure test: a value that already exists as a dictionary string is not an orphan.
const dictValues = new Set();
const dictKeys = new Set();
const src = readFileSync(LOCALE_TS, "utf8");
for (const m of src.matchAll(/"([^"]+)": "((?:[^"\\]|\\.)*)"/g)) { dictValues.add(m[2]); dictKeys.add(m[1]); }

const findings = [];
for (const file of walk(APP)) {
  const text = readFileSync(file, "utf8");
  const sf = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
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
    } else if (ts.isStringLiteral(node) && contextOf(stack, sf) === "reader") {
      push(line, "attr", node.text, mono);
    } else if (ts.isTemplateHead(node) || ts.isTemplateMiddle(node) || ts.isTemplateTail(node) || ts.isNoSubstitutionTemplateLiteral(node)) {
      const kind = contextOf(stack, sf);
      const raw = node.text.trim();
      // A template chunk in a `cn(...)` call or a className attribute is styling, not copy; the previous
      // version of this scan counted those as reader-facing text and reported 89 when the real number was lower.
      if (raw && (kind === "reader" || kind === "text")) push(line, kind === "text" ? "tpl-jsx" : "tpl", raw, mono);
    }
    ts.forEachChild(node, visit);
    stack.pop();
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

function contextOf(stack, sf) {
  for (let i = stack.length - 2; i >= 0; i--) {
    const n = stack[i];
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

const dups = findings.filter((f) => f.kind === "dup");
const wordy = findings.filter((f) => f.kind !== "dup" && (f.text.match(/[A-Za-z]{2,}/g) ?? []).length >= 2 && !f.mono);
const single = findings.filter((f) => f.kind !== "dup" && !wordy.includes(f) && !f.mono);
const monospace = findings.filter((f) => f.mono);

const byFile = new Map();
for (const f of wordy) {
  if (!byFile.has(f.file)) byFile.set(f.file, []);
  byFile.get(f.file).push(f);
}
console.log("=== multi-word, non-monospace: reader-facing candidates ===");
for (const [file, list] of [...byFile.entries()].sort()) {
  console.log(`\n${file}  (${list.length})`);
  for (const f of list) console.log(`   ${f.line} [${f.kind}] ${JSON.stringify(f.text.slice(0, 120))}`);
}
console.log(`\n=== second-owner duplicates (page keeps a copy the dictionary owns) ===`);
for (const f of dups) console.log(`   ${f.file}:${f.line} ${JSON.stringify(f.text.slice(0, 90))}`);
console.log(`duplicates=${dups.length}`);
console.log(`\ntotals: wordy=${wordy.length} in ${byFile.size} files, single-token=${single.length}, monospace/data=${monospace.length}, all=${findings.length}`);

if (process.env.R13J_SINGLE) {
  const tokens = new Map();
  for (const f of single) tokens.set(f.text, (tokens.get(f.text) ?? 0) + 1);
  console.log("\n=== single-token, non-monospace (grouped by text, count) ===");
  for (const [t, n] of [...tokens.entries()].sort((a, b) => b[1] - a[1])) console.log(`  ${n}x ${JSON.stringify(t)}`);
}
