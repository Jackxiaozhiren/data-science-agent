#!/usr/bin/env node
// R-13 closure acceptance, by DOM region rather than by dictionary membership.
//
// The first version asked "does this page show a string the dictionary owns", which cannot see a sentence the
// page still writes itself -- and it did not see /research's "Research · Step 3" for exactly that reason. This
// one asks the structural question instead: on a 中文 route, every region the *interface* owns (a column head,
// an option, a form label, a summary, a heading, the shell) must speak Chinese or declare itself an identifier.
// Regions that carry the run's own product -- table cells, code, the report body -- are not examined, because a
// statistician's finding is not translated (the plan's rule) and a page-wide scan cannot tell the two apart.
//
// The identifier list is explicit. An unlisted Latin-only string in chrome is a failure, which is what makes
// "closed" a measurement rather than a claim.
import { mkdirSync, readFileSync } from "node:fs";
import { chromium } from "playwright";
import { CHROME_SELECTOR, classifyChromeRegions } from "./locale-chrome-rules.mjs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "..");

const WEB = process.env.R13I_WEB || "http://127.0.0.1:3221";
const API = process.env.R13I_API || "http://127.0.0.1:8000";
const OUT = process.env.R13I_OUT ?? join(repoRoot, "output", "r13i");
mkdirSync(OUT, { recursive: true });
const STATIC = [
  "/", "/mcp", "/evaluations", "/benchmarks", "/research", "/settings", "/failures",
  "/runs", "/runs/compare", "/reports", "/datasets", "/datasets/compare", "/analysis",
];

const ONLY = process.env.R13I_ROUTES ? process.env.R13I_ROUTES.split(",") : null;

async function firstId(path) {
  const res = await fetch(`${API}${path}`, { headers: { "X-DSA-Owner": "web-acceptance" } });
  if (!res.ok) throw new Error(`${path} answered ${res.status}`);
  const body = await res.json();
  const items = body.items ?? body.datasets ?? body.analyses ?? body.runs ?? [];
  const first = items[0]?.id ?? items[0]?.run_id;
  if (!first) throw new Error(`${path} returned no rows -- the seed did not run, so the dynamic routes go untested`);
  return first;
}

const datasetId = ONLY ? "planted" : await firstId("/api/v1/datasets/");
const runId = ONLY ? "planted" : await firstId("/api/v1/analysis/");
const ROUTES = [...(ONLY ? STATIC.filter((r) => ONLY.includes(r)) : STATIC), `/runs/${runId}`, `/runs/${runId}/replay`, ONLY ? null : `/datasets/${datasetId}`, ONLY ? null : `/analysis/${runId}`].filter(Boolean);

const browser = await chromium.launch();

/**
 * The `chk.*` vocabulary, read from `lib/locale.ts` per locale.
 *
 * Why the dictionary and not a list: `<strong>` inside a list item is data-adjacent markup, so it is deliberately
 * outside CHROME_SELECTOR -- a report body's bold text is the run's, not the interface's. That leaves the
 * validation card's check names unexamined on the page that shows them, which is the same blind spot as the
 * inactive tab (§238 found the identifiers there). The narrow question this answers instead: *the product already
 * has a word for this check -- is the page showing the word, or the engine's key?* A label with no dictionary
 * entry (a tool name, `correlation_analysis`) is exempt by construction rather than by an allowlist, which is the
 * adjudication written down as code.
 */
function chkVocabulary(locale) {
  const folded = readFileSync(join(repoRoot, "apps/web/lib/locale.ts"), "utf8").replace(/:\s+/g, ": ");
  const parts = folded.split(`${locale}: {`, 2);
  if (parts.length !== 2) throw new Error(`UI_STRINGS has no ${locale} block the reader understands`);
  const body = parts[1].split("\n  },", 1)[0];
  const keys = new Set();
  const values = new Set();
  for (const [, key, value] of body.matchAll(/"chk\.([a-z_]+)": "([^"]*)",/g)) {
    keys.add(key);
    values.add(value);
  }
  if (keys.size < 8) throw new Error(`parsed only ${keys.size} chk.* keys for ${locale} -- the reader broke`);
  return { keys, values };
}
const CHK = { zh: chkVocabulary("zh"), en: chkVocabulary("en") };

let failures = 0;
for (const locale of ["zh", "en"]) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 1400 } });
  await ctx.addCookies([{ name: "dsa_locale", value: locale, domain: "127.0.0.1", path: "/" }]);
  for (const route of ROUTES) {
    const page = await ctx.newPage();
    const errors = [];
    page.on("console", (m) => {
      if (m.type() === "error") errors.push(m.text().slice(0, 90));
    });
    const resp = await page.goto(`${WEB}${route}`, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForTimeout(1300);
    const text = await page.evaluate(() => document.body.innerText);
    const readChrome = () =>
      page.evaluate(
        ({ sel }) =>
          [...document.querySelectorAll(sel)]
            .filter((el) => !el.closest("[data-run-document]"))
            .filter((el) => el.offsetParent !== null || el.tagName === "OPTION")
            .map((el) => ({ tag: el.tagName.toLowerCase(), text: (el.textContent || "").replace(/\s+/g, " ").trim() }))
            .filter((x) => x.text),
        { sel: CHROME_SELECTOR }
      );
    // An inactive tab is not mounted, so the default tab alone is not the page. Walk every tab the way a
    // keyboard user reaches one -- focus, then Enter -- and union what each reveals. `inspector-a11y.mjs`
    // learned this the same way: a check that sees only the first tab passes on a page whose other tabs are
    // still English, which is the blind spot, not the result.
    const seenRegions = new Map();
    const collect = (list) => {
      for (const r of list) seenRegions.set(`${r.tag}|${r.text}`, r);
    };
    // The validation card's labels, collected the same way -- union across tabs, because an inactive tab is not
    // mounted and a page-wide `li strong` scan would also read the report body's bold text, which is the run's.
    const readLabels = () =>
      page.evaluate(() =>
        [...document.querySelectorAll("main li strong")]
          // Same boundary as the chrome read: the rendered report is the run's own bytes (Markdown.tsx marks them
          // `data-run-document`), so its bold text must not stand in for the card's labels -- without this filter
          // the "was the card read at all" floor was satisfied by the report body and proved nothing.
          .filter((el) => !el.closest("[data-run-document]"))
          .map((el) => (el.textContent || "").replace(/\s+/g, " ").trim().replace(/:$/, ""))
          .filter(Boolean)
      );
    const labelSet = new Set();
    const collectLabels = (list) => {
      for (const l of list) labelSet.add(l);
    };
    collect(await readChrome());
    collectLabels(await readLabels());
    const tabCount = await page.locator('[role="tab"]').count();
    for (let i = 0; i < tabCount; i += 1) {
      const tab = page.locator('[role="tab"]').nth(i);
      try {
        await tab.focus();
        await page.keyboard.press("Enter");
        await page.waitForTimeout(400);
        collect(await readChrome());
        collectLabels(await readLabels());
      } catch {
        // A tab that cannot be reached is reported by inspector-a11y.mjs, which owns that claim.
      }
    }
    const chrome = [...seenRegions.values()];
    if (chrome.length < 8) {
      console.log(`${locale} ${route} FAIL chromeRegions=${chrome.length} (the selector matched almost nothing)`);
      failures += 1;
      await page.close();
      continue;
    }
    const problems = [];
    const seen = classifyChromeRegions(chrome);
    if (process.env.R13I_STATS && locale === "zh") {
      console.log(
        `STATS ${route} chrome=${seen.total} cjk=${seen.cjk} (${Math.round((100 * seen.cjk) / seen.total)}%) ` +
          `exempt=${seen.exempt.length} ${JSON.stringify(seen.exempt.map((c) => c.text.slice(0, 30)).slice(0, 6))}`
      );
      if (seen.cjk < 4) problems.push(`chineseRouteHasAlmostNoChineseChrome cjk=${seen.cjk} of ${seen.total}`);
    }
    if (locale === "zh" && seen.leaks.length) {
      problems.push(
        `chineseRouteShowsEnglish[${seen.leaks.length}]: ` +
          seen.leaks.slice(0, 6).map((c) => `${c.tag}:"${c.text.slice(0, 60)}"`).join(" | ")
      );
    }
    if (text.includes("⟨")) problems.push("missingKeyMarker");
    // On a run page, the validation card is the surface `<strong>`-in-a-list-item and therefore outside
    // CHROME_SELECTOR. Assert only what is unambiguous there: a label the dictionary has a word for must not be
    // shown as the engine's key, and the card must have been reached at all -- an empty label set would make the
    // first half vacuously true, which is how §238's heading check kept passing.
    if (/^\/analysis\/.+/.test(route)) {
      const shownAsKey = [...labelSet].filter((l) => CHK[locale].keys.has(l));
      if (shownAsKey.length) {
        problems.push(`checkKeysShownAsLabels[${shownAsKey.length}]: ${shownAsKey.slice(0, 5).join(", ")}`);
      }
      const named = [...labelSet].filter((l) => CHK[locale].values.has(l));
      if (named.length === 0) {
        problems.push(`validationCardNotRead labels=${labelSet.size} (no label the dictionary owns was on the page)`);
      }
    }
    if ((resp?.status() ?? 0) !== 200) problems.push(`http=${resp.status()}`);
    if (errors.length) problems.push(`consoleErrors=${errors.length} ${JSON.stringify(errors.slice(0, 2))}`);
    const ok = problems.length === 0;
    if (!ok) failures += 1;
    for (const p of problems) console.log(`${locale} ${route} ${ok ? "PASS" : "FAIL"} ${p}`);
    if (ok) console.log(`${locale} ${route} PASS chromeRegions=${chrome.length}`);
    await page.screenshot({ path: `${OUT}/${locale}${route.replace(/\//g, "-")}.png` });
    await page.close();
  }
  await ctx.close();
}
await browser.close();
console.log(`R13I_CHROME_ACCEPTANCE_${failures === 0 ? "PASS" : "FAIL"} (${ROUTES.length * 2} route/locale checks)`);
process.exit(failures === 0 ? 0 : 1);
