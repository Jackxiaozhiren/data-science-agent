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
 * console hygiene, and "old bundle" regressions, not live data. A *live*
 * server on the API port breaks that premise, so the tour refuses it up
 * front (see assertApiPortQuiet) instead of blaming the app for its CORS refusals.
 *
 * Usage: node apps/web/scripts/regression.mjs [--port 3210] [--api-port 8000] [--out <dir>]
 */
import { spawn, execFileSync } from "node:child_process";
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

// The API port the *build* was baked against (lib/api.ts defaults to localhost:8000). It is validated as an
// integer because it reaches `lsof`/`ps` and a console-error filter: a value like `8000; rm -rf` must not be
// interpolable anywhere, and a non-numeric port would silently make the preflight and the filter disagree.
function readApiPort() {
  const flag = args.indexOf("--api-port");
  const raw = process.env.REGRESSION_API_PORT ?? (flag >= 0 ? args[flag + 1] : undefined) ?? "8000";
  if (!/^\d{1,5}$/.test(String(raw))) {
    console.error(`invalid --api-port ${JSON.stringify(raw)}: expected a bare integer port (1-65535)`);
    process.exit(2);
  }
  const port = Number(raw);
  if (port < 1 || port > 65535) {
    console.error(`invalid --api-port ${port}: expected 1-65535`);
    process.exit(2);
  }
  return port;
}
const API_PORT = readApiPort();
const API_ORIGIN = new RegExp(`(localhost|127\\.0\\.0\\.1):${API_PORT}`);

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

// R-11: the wait and the failure have to be distinguishable *in the browser*, not just in the phase
// machine. Two scenarios, both driven by intercepting the health check rather than by starting a backend:
// a request that hangs is what a sleeping free instance actually does (measured 44.5 s on the hosted demo),
// and a request that gets a 503 is something answering without the API answering. The timings are printed
// because "it looked like it was waking up for 5 seconds then said unreachable" is the acceptance criterion.
const PROBE_SCENARIOS = [
  {
    label: "a hanging health check reads as waking up, not as broken",
    mode: "hang",
    wantState: "warming",
    wantDot: /Waking… \d\/\d/,
    wantPage: /Attempt \d+ of \d+/,
    forbid: ["No datasets yet", "Uploaded — profiled"],
  },
  {
    label: "a waking backend is not reported as an empty account on the Ask page",
    mode: "hang",
    route: "/analysis",
    wantState: "warming",
    wantPage: /waking up/i,
    forbid: ["No datasets loaded", "No datasets yet"],
  },
  {
    label: "an answering proxy is unreachable, never 'waking'",
    mode: "503",
    wantState: "unreachable",
    wantDot: /API unreachable/,
    wantPage: /nothing answered/,
    forbid: ["No datasets yet", "Uploaded — profiled"],
  },
];

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

// The tour is deliberately backend-independent: with nothing listening, every page renders its empty or
// error state and the only console noise is a refused connection, which the filter below accepts. A
// *live* server on the API port breaks that premise silently -- it answers without an
// Access-Control-Allow-Origin header unless whoever started it set DSA_CORS_ORIGINS, and Chrome then reports
// `net::ERR_FAILED` with no URL in the message, so the filter cannot see it and the tour blames the app for
// 51 phantom errors (audit §165 measured exactly this). So: look before leaping, and name the holder.
// Override with --api-port <n> to point the check at a port this run owns.
async function assertApiPortQuiet(apiPort) {
  const url = `http://127.0.0.1:${apiPort}/health`;
  let answer = null;
  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(2500) });
    answer = `HTTP ${res.status}`;
  } catch {
    return null;
  }
  let holder = "unknown";
  try {
    // -sTCP:LISTEN, not a bare port match: the probe's own fetch leaves a connection that `lsof -ti tcp:N`
    // reports, so the unfiltered lookup names this script instead of the server occupying the port.
    const pid = execFileSync("lsof", ["-nP", `-iTCP:${apiPort}`, "-sTCP:LISTEN", "-t"], { encoding: "utf8" })
      .trim()
      .split("\n")[0];
    if (pid && /^\d+$/.test(pid)) holder = execFileSync("ps", ["-o", "pid=,command=", "-p", pid], { encoding: "utf8" }).trim();
  } catch {
    // lsof/ps unavailable: the answer line alone is still actionable.
  }
  return `the tour needs ${url} to be quiet (it is backend-independent); ${answer} from: ${holder}. ` +
    "Stop that server, or run the tour against a port this run owns — build with " +
    `NEXT_PUBLIC_API_URL=http://127.0.0.1:<port> and pass --api-port <port> — because every route check ` +
    "below would otherwise be counting that server's CORS refusals as app errors.";
}

// Refuse before booting anything: a tour that spends 90 s starting a server only to report 51 phantom
// errors blames the app for someone else's listener.
const portConflict = await assertApiPortQuiet(API_PORT);
if (portConflict) {
  console.error(`FAILURES:\n- preflight (API port ${API_PORT}): ${portConflict}`);
  process.exit(1);
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
      if (/Failed to load resource/i.test(text) && API_ORIGIN.test(text)) return;
      if (/CORS policy/i.test(text) && API_ORIGIN.test(text)) return;
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

  // R-11: the two states a first visit actually passes through, asserted where they are observable. The
  // health check is intercepted rather than backed by a real server, because "hangs for tens of seconds"
  // is the measured behaviour of a sleeping free instance (44.5 s to first byte on the hosted demo) and no
  // test harness should wait for that. Timings are printed: a state that appears after 40 s is a different
  // product than one that appears after 4.
  for (const scenario of PROBE_SCENARIOS) {
    const probeContext = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const probePage = await probeContext.newPage();
    const label = `probe ${scenario.label}`;
    const startedAt = Date.now();
    try {
      await probePage.route("**/health", (route) => {
        if (scenario.mode === "503") {
          void route.fulfill({ status: 503, contentType: "text/plain", body: "answered by a proxy" });
          return;
        }
        // Deliberately never answered.
      });
      await probePage.goto(`http://localhost:${PORT}${scenario.route ?? "/datasets"}`, {
        waitUntil: "domcontentloaded",
        timeout: 45000,
      });
      const dot = probePage.locator(`[data-api-state="${scenario.wantState}"]`).first();
      await dot.waitFor({ state: "visible", timeout: 25000 });
      const elapsed = ((Date.now() - startedAt) / 1000).toFixed(1);
      const dotText = (await dot.innerText()).trim();
      if (scenario.wantDot && !scenario.wantDot.test(dotText)) {
        throw new Error(`dot read ${JSON.stringify(dotText)}, wanted ${scenario.wantDot}`);
      }
      const body = await probePage.locator("body").innerText();
      if (!scenario.wantPage.test(body)) {
        throw new Error(`the page never stated the wait in its own words; wanted ${scenario.wantPage}`);
      }
      // One frame, two renderings of the same counter: a base off-by-one between them is invisible to every
      // text-matching assertion above, because each is individually plausible.
      const dotCount = scenario.wantState === "warming" ? dotText.match(/(\d+)\/(\d+)/) : null;
      const pageCount = scenario.wantState === "warming" ? body.match(/Attempt (\d+) of (\d+)/) : null;
      if (scenario.wantState === "warming" && (!dotCount || !pageCount)) {
        throw new Error(`attempt counter unreadable: dot=${JSON.stringify(dotText)} page=${JSON.stringify(pageCount)}`);
      }
      if (dotCount && pageCount && (dotCount[1] !== pageCount[1] || dotCount[2] !== pageCount[2])) {
        throw new Error(
          `the header and the page disagree about the same attempt: ${JSON.stringify(dotText)} vs attempt ${pageCount[1]} of ${pageCount[2]}`
        );
      }
      for (const claim of scenario.forbid) {
        if (body.includes(claim)) {
          throw new Error(`the page claimed ${JSON.stringify(claim)} while the backend was ${scenario.wantState}`);
        }
      }
      console.log(`probe: ${scenario.wantState} reached after ${elapsed}s; dot=${JSON.stringify(dotText)}`);
      await probePage.screenshot({ path: join(OUT, `probe-${scenario.wantState}.png`) });
    } catch (e) {
      failures.push(`${label}: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      await probeContext.close();
    }
  }
} catch (e) {
  failures.push(`harness: ${e instanceof Error ? e.message : String(e)}\n${serverLog.slice(-1500)}`);
} finally {
  await browser?.close();
  killServer();
}

const ROUTE_CHECKS = ROUTES.length * VIEWPORTS.length;
const TOTAL_CHECKS = ROUTE_CHECKS + INTERACTIONS.length + PROBE_SCENARIOS.length;
console.log(
  `\nregression: ${TOTAL_CHECKS - failures.length}/${TOTAL_CHECKS} checks passed ` +
    `(${ROUTE_CHECKS} route/viewport + ${INTERACTIONS.length} interaction + ${PROBE_SCENARIOS.length} backend-probe), screenshots in ${OUT}`,
);
if (failures.length > 0) {
  console.error("FAILURES:\n- " + failures.join("\n- "));
}
// Force-exit: lingering child handles must never hang CI.
process.exit(failures.length > 0 ? 1 : 0);
