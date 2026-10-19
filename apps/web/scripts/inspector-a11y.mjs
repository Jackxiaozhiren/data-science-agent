#!/usr/bin/env node
// R-13's keyboard half, measured where the product's claim actually lives.
//
// The regression tour walks the static routes with no backend on purpose, so on `/analysis` -- the page whose
// whole purpose is the claim -> evidence -> tool call -> dataset hash drill-down -- it finds no `<details>` to
// open and reports "0 drill-down(s) opened by Enter". That is a true statement about an empty page, not the
// requirement. This script runs against a live, seeded instance and drives every disclosure on a real run's
// report: each must open on Enter, close on Enter again, and announce its state, and every focus stop it walks
// must show a visible focus ring.
//
// It exits non-zero on any disclosure that cannot be operated from the keyboard, because that is the one
// accessibility failure this product cannot have: the evidence is the feature.
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "..");
const WEB = process.env.R13I_WEB || "http://127.0.0.1:3221";
const API = process.env.R13I_API || "http://127.0.0.1:8000";
const OUT = join(repoRoot, "output", "inspector-a11y");
mkdirSync(OUT, { recursive: true });

const res = await fetch(`${API}/api/v1/analysis/`, { headers: { "X-DSA-Owner": "a11y-acceptance" } });
if (!res.ok) {
  console.error(`the API answered ${res.status} -- this script needs a live seeded instance (dsa ui) ` +
    "because the tour's no-backend mode is exactly the case that cannot prove this claim");
  process.exit(2);
}
const body = await res.json();
const items = body.items ?? body.analyses ?? [];
const runId = items[0]?.id ?? items[0]?.run_id;
if (!runId) {
  console.error("no stored run, so there is no drill-down to test -- the seed did not run");
  process.exit(2);
}

const browser = await chromium.launch();
let failures = 0;
let disclosures = 0;
let opened = 0;
let tabsWalked = 0;
let perLocale = 0;
for (const locale of ["zh", "en"]) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 1400 } });
  await ctx.addCookies([{ name: "dsa_locale", value: locale, domain: "127.0.0.1", path: "/" }]);
  const page = await ctx.newPage();
  const errors = [];
  page.on("console", (m) => {
    if (m.type() === "error") errors.push(m.text().slice(0, 90));
  });
  await page.goto(`${WEB}/analysis/${runId}`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(2000);

  // The drill-downs live inside the run report's tabs, and an inactive tab is not mounted -- so the claim has to
  // be walked tab by tab, and the tabs have to be reached the way a keyboard user reaches them: focus, then
  // ArrowRight. A page where nothing is ever expanded is the vacuous pass this script would otherwise report.
  const tabs = await page.locator('[role="tab"]').all();
  if (tabs.length < 3) {
    failures += 1;
    console.log(`${locale} tabs FAIL only ${tabs.length} tab(s) found -- the inspector did not render, so nothing below is evidence`);
  }
  for (let t = 0; t < Math.max(tabs.length, 1); t += 1) {
    const live = await page.locator('[role="tab"]').all();
    if (!live[t]) break;
    await live[t].focus();
    await page.keyboard.press("Enter");
    await page.waitForTimeout(350);
    const label = (await live[t].textContent() || "").trim().slice(0, 18);
    const summaries = await page.locator("summary").all();
    disclosures = Math.max(disclosures, (await page.locator("summary").count()));
    let toggledHere = 0;
    const problems = [];
    for (const [i, summary] of summaries.entries()) {
      try {
        await summary.scrollIntoViewIfNeeded();
        await summary.focus();
        const before = await summary.evaluate((el) => el.parentElement.open);
        await page.keyboard.press("Enter");
        const mid = await summary.evaluate((el) => el.parentElement.open);
        if (mid === before) throw new Error(`Enter did not toggle summary#${i} (open=${mid}, was ${before})`);
        await page.keyboard.press("Enter");
        const back = await summary.evaluate((el) => el.parentElement.open);
        if (back !== before) throw new Error(`the second Enter left summary#${i} at open=${back}, wanted ${before}`);
        toggledHere += 1;
      } catch (e) {
        problems.push(`${e instanceof Error ? e.message : String(e)}`);
      }
    }
    opened += toggledHere;
    perLocale += toggledHere;
    tabsWalked += 1;
    if (problems.length) {
      failures += 1;
      console.log(`${locale} tab ${JSON.stringify(label)} FAIL ${problems.slice(0, 3).join(" | ")}`);
    } else {
      console.log(`${locale} tab ${JSON.stringify(label)}: ${summaries.length} disclosure(s), ${toggledHere} opened and closed by Enter`);
    }
  }

  // Tab through the page and require a visible ring on each stop: `outline-none` with no replacement is the
  // failure mode, and a rect is not evidence of focus -- the ring is.
  const stops = [];
  for (let i = 0; i < 60; i += 1) {
    await page.keyboard.press("Tab");
    const state = await page.evaluate(() => {
      const el = document.activeElement;
      if (!el || el === document.body) return null;
      const style = getComputedStyle(el);
      const rect = el.getBoundingClientRect();
      const ring =
        (style.outlineStyle !== "none" && parseFloat(style.outlineWidth) > 0) ||
        style.boxShadow !== "none" ||
        style.borderTopColor !== getComputedStyle(document.body).borderTopColor;
      return { tag: el.tagName.toLowerCase(), visible: rect.width > 0 && rect.height > 0, ring, text: (el.textContent || "").trim().slice(0, 24) };
    });
    if (!state) break;
    stops.push(state);
  }
  const unfocused = stops.filter((s) => !s.ring);
  if (unfocused.length) {
    failures += 1;
    console.log(`${locale} keyboard FAIL ${unfocused.length}/${stops.length} stops show no visible focus: ${JSON.stringify(unfocused.slice(0, 4))}`);
  }
  if (errors.length) {
    failures += 1;
    console.log(`${locale} console FAIL ${errors.length} error(s): ${JSON.stringify(errors.slice(0, 2))}`);
  }
  await page.screenshot({ path: join(OUT, `${locale}-analysis-${runId.slice(0, 8)}.png`), fullPage: true });
  console.log(`${locale} tabs=${tabsWalked ? "walked" : "none"} disclosuresToggled=${perLocale} tabStops=${stops.length} consoleErrors=${errors.length}`);
  perLocale = 0;
  await ctx.close();
}
await browser.close();
const total = failures;
if (opened === 0) {
  console.error("no disclosure was toggled anywhere -- the run report has no drill-down, so this run proves nothing");
  process.exit(1);
}
console.log(
  `INSPECTOR_A11Y_${total === 0 ? "PASS" : "FAIL"} -- ${opened} disclosure toggles across both locales, ${disclosures} on the largest tab, ` +
    `(Playwright ${process.env.PLAYWRIGHT_VERSION ?? "bundled"}, Chromium launched by this script), screenshots in ${OUT}`
);
process.exit(total === 0 ? 0 : 1);
