#!/usr/bin/env node
// The navigation is the one surface present on every route, so a visitor whose chrome is in the wrong language
// never sees it fail -- a single-page test reads one page. This walks the shell (header links, the sidebar's
// groups, the footer) in both languages against a live build and asserts the strings the dictionary owns.
//
// It reads the DOM, not the source: the defect it exists to catch was a provider that wrapped the route but not
// the sidebar, which made a 中文 page look half-translated while every source guard stayed green. Reading
// source text cannot see which provider a component actually rendered under.
//
//   NAVLANG_WEB=http://127.0.0.1:3221 node apps/web/scripts/nav-language-acceptance.mjs
//
// The locale is set by the same cookie the app writes, so the run exercises the real switch rather than a
// prop. Exit 0 means both locales showed their own chrome and no console error fired on the way.
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "..");
const WEB = process.env.NAVLANG_WEB || "http://127.0.0.1:3221";
const OUT = process.env.NAVLANG_OUT ?? join(repoRoot, "output", "navlang");
mkdirSync(OUT, { recursive: true });

// `want` is what the chrome must say; `forbid` is the other language's wording for the same slots, so a
// half-applied locale change cannot pass by showing both.
const CASES = [
  {
    locale: "zh",
    want: ["提问", "运行", "报告", "数据集", "对比运行", "基准评测", "失败分析", "模型设置", "先有证据，再谈结论"],
    forbid: ["Your work", "About this system", "Ask", "Reports", "Benchmarks", "Model settings"],
  },
  {
    locale: "en",
    want: ["Ask", "Runs", "Reports", "Datasets", "Compare runs", "Benchmarks", "Model settings", "Evidence before claim"],
    forbid: ["提问", "运行列表", "报告", "基准评测", "模型设置"],
  },
];

const browser = await chromium.launch();
let failures = 0;
for (const c of CASES) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  await ctx.addCookies([{ name: "dsa_locale", value: c.locale, domain: "127.0.0.1", path: "/" }]);
  const page = await ctx.newPage();
  const errors = [];
  page.on("console", (m) => {
    if (m.type() === "error") errors.push(m.text().slice(0, 90));
  });

  await page.goto(`${WEB}/runs`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(1500);

  const text = await page.evaluate(() =>
    ["header", "aside", "footer"]
      .map((sel) => document.querySelector(sel)?.innerText ?? "")
      .join("\n"),
  );
  const lines = text.split("\n").map((line) => line.trim()).filter(Boolean);

  const missing = c.want.filter((term) => !lines.some((line) => line.includes(term)));
  const leaked = c.forbid.filter((term) => lines.some((line) => line.includes(term)));
  const ok = missing.length === 0 && leaked.length === 0 && errors.length === 0;
  if (!ok) failures += 1;

  await page.screenshot({ path: join(OUT, `nav-${c.locale}.png`) });
  console.log(
    `locale=${c.locale} ${ok ? "PASS" : "FAIL"} missing=${JSON.stringify(missing)} ` +
      `leaked=${JSON.stringify(leaked)} consoleErrors=${errors.length}`,
  );
  console.log(`  chrome: ${JSON.stringify(lines.slice(0, 14))}`);
  await ctx.close();
}
await browser.close();

console.log(`NAVLANG_ACCEPTANCE_${failures === 0 ? "PASS" : "FAIL"}`);
process.exit(failures === 0 ? 0 : 1);
