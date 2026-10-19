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
import { mkdirSync } from "node:fs";
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
    const chrome = await page.evaluate(
      ({ sel }) =>
        [...document.querySelectorAll(sel)]
          .filter((el) => el.offsetParent !== null || el.tagName === "OPTION")
          .map((el) => ({ tag: el.tagName.toLowerCase(), text: (el.textContent || "").replace(/\s+/g, " ").trim() }))
          .filter((x) => x.text),
      { sel: CHROME_SELECTOR }
    );
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
