#!/usr/bin/env node
/**
 * Web regression tour: boots `next start`, then asserts every static route
 * returns 200 with zero console errors and zero horizontal overflow at
 * desktop (1280) and mobile (390) widths, and finally drives the upload
 * controls on `/datasets` so a click or keypress that reaches no handler
 * fails here rather than shipping green. Screenshots land in
 * output/playwright/regression/ for visual review.
 *
 * Intentionally backend-independent: with no API running, pages render
 * their EmptyState/ErrorState (all HTTP 200) — the tour guards layout,
 * console hygiene, and "old bundle" regressions, not live data.
 *
 * Usage: node apps/web/scripts/regression.mjs [--port 3210] [--out <dir>]
 */
import { spawn } from "node:child_process";
import { mkdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const webDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = resolve(webDir, "..", "..");

const args = process.argv.slice(2);
const portFlag = args.indexOf("--port");
const outFlag = args.indexOf("--out");
const PORT = process.env.REGRESSION_PORT || (portFlag >= 0 ? args[portFlag + 1] : "3000");
const OUT = resolve(process.env.REGRESSION_OUT || (outFlag >= 0 ? args[outFlag + 1] : join(repoRoot, "output", "playwright", "regression")));

const ROUTES = [
  "/",
  "/datasets",
  "/datasets/compare",
  "/analysis",
  "/benchmarks",
  "/research",
  "/reports",
  "/runs",
  "/runs/compare",
  "/evaluations",
  "/failures",
  "/mcp",
];

const VIEWPORTS = [
  { name: "desktop", width: 1280, height: 900 },
  { name: "mobile", width: 390, height: 844 },
];

// The tour above proves a route renders cold. It never proved an event reaches a
// handler, so a control whose click does nothing, or one only the mouse can drive,
// shipped green (audit §156, §164 item 3). These controls are client-side, so the
// pass needs no API and stays backend-independent like the tour.
const INTERACTIONS = [
  {
    label: "drop zone click opens the file chooser",
    selector: '[role="button"][aria-label^="Upload dataset"]',
    action: "click",
    want: 1,
  },
  {
    // The control's own aria-label promises "or press Enter to browse"; a keyboard
    // user finding nothing happens is invisible to axe and invisible to goto.
    label: "drop zone Enter opens the file chooser",
    selector: '[role="button"][aria-label^="Upload dataset"]',
    action: "press",
    key: "Enter",
    want: 1,
  },
  {
    // The nested button calls stopPropagation; if that ever goes missing the parent
    // handler fires too and the browser is asked for a file twice for one click.
    label: "Browse files opens exactly one chooser",
    selector: 'button:has-text("Browse files")',
    action: "click",
    want: 1,
  },
];

const UPLOAD_INPUT_ARIA = "Dataset files";

async function expectFileChooser(page, act, want, timeoutMs = 5000) {
  let count = 0;
  let last = null;
  const onChooser = (chooser) => {
    count += 1;
    last = chooser;
  };
  page.on("filechooser", onChooser);
  try {
    await act();
    const deadline = Date.now() + timeoutMs;
    while (count < want && Date.now() < deadline) await page.waitForTimeout(50);
    // Settle window so a duplicate fire (a missing stopPropagation) is counted too.
    await page.waitForTimeout(250);
    if (count !== want) {
      throw new Error(`file chooser fired ${count} time(s), expected ${want}`);
    }
    return last;
  } finally {
    page.off("filechooser", onChooser);
  }
}

const slug = (r) => (r === "/" ? "home" : r.replaceAll("/", "-").replace(/^-/, ""));

function waitForServer(url, timeoutMs = 90000) {
  const start = Date.now();
  return new Promise((resolvePromise, reject) => {
    const tick = async () => {
      try {
        const res = await fetch(url);
        if (res.ok) return resolvePromise();
      } catch {
        // not up yet
      }
      if (Date.now() - start > timeoutMs) return reject(new Error(`server not ready: ${url}`));
      setTimeout(tick, 1000);
    };
    tick();
  });
}

const server = spawn("npx", ["next", "start", "--port", PORT], {
  cwd: webDir,
  stdio: ["ignore", "pipe", "pipe"],
  // Own process group so cleanup can SIGKILL the whole tree (npx wrapper
  // alone may leave next-server orphaned, hanging CI until timeout).
  detached: process.platform !== "win32",
});
server.unref();
function killServer() {
  try {
    if (server.pid && process.platform !== "win32") process.kill(-server.pid, "SIGKILL");
    else server.kill("SIGKILL");
  } catch {
    try { server.kill("SIGKILL"); } catch { /* already gone */ }
  }
}
let serverLog = "";
server.stdout?.on("data", (d) => { serverLog += d.toString().slice(-2000); });
server.stderr?.on("data", (d) => { serverLog += d.toString().slice(-2000); });

const failures = [];
let browser;
try {
  await waitForServer(`http://localhost:${PORT}/`);
  mkdirSync(OUT, { recursive: true });
  browser = await chromium.launch();

  for (const vp of VIEWPORTS) {
    const context = await browser.newContext({ viewport: { width: vp.width, height: vp.height } });
    const page = await context.newPage();
    const consoleErrors = [];
    page.on("console", (msg) => {
      if (msg.type() !== "error") return;
      const text = msg.text();
      // Expected environmental noise, not app bugs: the tour is
      // backend-independent, so failed API fetches are filtered —
      // refused (backend down, message carries no URL) and CORS
      // failures naming the API origin. Same-origin asset failures
      // always include a URL and still count.
      if (/Failed to load resource: net::ERR_CONNECTION_REFUSED/i.test(text) && !/https?:\/\//.test(text)) return;
      if (/Failed to load resource/i.test(text) && /localhost:8000|127\.0\.0\.1:8000/.test(text)) return;
      if (/CORS policy/i.test(text) && /localhost:8000|127\.0\.0\.1:8000/.test(text)) return;
      consoleErrors.push(text.slice(0, 200));
    });
    page.on("pageerror", (err) => consoleErrors.push(String(err).slice(0, 200)));

    for (const route of ROUTES) {
      const label = `${vp.name} ${route}`;
      try {
        const res = await page.goto(`http://localhost:${PORT}${route}`, { waitUntil: "networkidle", timeout: 45000 });
        if (!res || res.status() !== 200) throw new Error(`HTTP ${res?.status()}`);
        // Let client fetches settle (empty states render after API attempts fail fast).
        await page.waitForTimeout(2500);
        const overflow = await page.evaluate(
          () => document.documentElement.scrollWidth - document.documentElement.clientWidth
        );
        if (overflow > 0) throw new Error(`horizontal overflow ${overflow}px`);
        await page.screenshot({ path: join(OUT, `${vp.name}-${slug(route)}.png`), fullPage: true });
      } catch (e) {
        failures.push(`${label}: ${e instanceof Error ? e.message : String(e)}`);
      }
    }
    if (consoleErrors.length > 0) {
      failures.push(`${vp.name}: ${consoleErrors.length} console error(s): ${[...new Set(consoleErrors)].slice(0, 3).join(" | ")}`);
    }
    await context.close();
  }

  const interContext = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const interPage = await interContext.newPage();
  try {
    await interPage.goto(`http://localhost:${PORT}/datasets`, { waitUntil: "networkidle", timeout: 45000 });
    for (const item of INTERACTIONS) {
      try {
        const control = interPage.locator(item.selector).first();
        await control.waitFor({ state: "visible", timeout: 15000 });
        const act =
          item.action === "click"
            ? () => control.click()
            : async () => {
                await control.focus();
                await interPage.keyboard.press(item.key);
              };
        const chooser = await expectFileChooser(interPage, act, item.want);
        const aria = await (await chooser.element()).getAttribute("aria-label");
        if (aria !== UPLOAD_INPUT_ARIA) {
          throw new Error(`chooser opened ${JSON.stringify(aria)}, wanted the ${JSON.stringify(UPLOAD_INPUT_ARIA)} input`);
        }
      } catch (e) {
        failures.push(`interaction ${item.label}: ${e instanceof Error ? e.message : String(e)}`);
      }
    }
  } catch (e) {
    failures.push(`interaction harness: ${e instanceof Error ? e.message : String(e)}`);
  } finally {
    await interContext.close();
  }
} catch (e) {
  failures.push(`harness: ${e instanceof Error ? e.message : String(e)}\n${serverLog.slice(-1500)}`);
} finally {
  await browser?.close();
  killServer();
}

const ROUTE_CHECKS = ROUTES.length * VIEWPORTS.length;
const TOTAL_CHECKS = ROUTE_CHECKS + INTERACTIONS.length;
console.log(
  `\nregression: ${TOTAL_CHECKS - failures.length}/${TOTAL_CHECKS} checks passed ` +
    `(${ROUTE_CHECKS} route/viewport + ${INTERACTIONS.length} interaction), screenshots in ${OUT}`,
);
if (failures.length > 0) {
  console.error("FAILURES:\n- " + failures.join("\n- "));
}
// Force-exit: lingering child handles must never hang CI.
process.exit(failures.length > 0 ? 1 : 0);
