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
import { mkdirSync, readFileSync, existsSync, statSync, readdirSync } from "node:fs";
import { dirname, join, resolve, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import { CHROME_SELECTOR, classifyChromeRegions } from "./locale-chrome-rules.mjs";
import { originsIn, verdict } from "./api-origin-verdict.mjs";

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
  "/settings",
];

// Every entry the navigation can send a visitor to must be walked here, so the list is checked against the
// declaration rather than maintained beside it: a copied route table goes stale the day someone adds a nav
// link, and the new route then ships without ever having been rendered once. Read from source because plain
// node cannot import a .tsx module.
function assertNavRoutesWalked() {
  const sidebar = readFileSync(join(webDir, "app/components/layout/Sidebar.tsx"), "utf8");
  const declared = [...sidebar.matchAll(/href: "([^"]+)"/g)].map((m) => m[1]);
  if (declared.length === 0) {
    throw new Error("no nav hrefs parsed from Sidebar.tsx -- the declaration changed shape and this check went blind");
  }
  const missing = declared.filter((href) => !ROUTES.includes(href));
  if (missing.length > 0) {
    throw new Error(`navigation links to routes the tour never walks: ${missing.join(", ")}`);
  }
}
assertNavRoutesWalked();
const LOCALES = readLocales();

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
// a request that hangs is what a sleeping free instance actually does (44.5 s and 92.8 s on the hosted demo),
// and a request that gets a 503 is something answering without the API answering. The timings are printed
// because "it looked like it was waking up for 5 seconds then said unreachable" is the acceptance criterion.
const PROBE_SCENARIOS = [
  {
    label: "a hanging health check reads as waking up, not as broken",
    mode: "hang",
    wantState: "warming",
    wantWithinS: 6,
    wantDot: /Waking… \d\/\d/,
    wantPage: /Attempt \d+ of \d+/,
    forbid: ["No datasets yet", "Uploaded — profiled"],
  },
  {
    label: "a waking backend is not reported as an empty account on the Ask page",
    mode: "hang",
    route: "/analysis",
    wantState: "warming",
    wantWithinS: 6,
    wantPage: /waking up/i,
    forbid: ["No datasets loaded", "No datasets yet"],
  },
  {
    label: "an answering proxy is unreachable, never 'waking'",
    mode: "503",
    wantState: "unreachable",
    wantWithinS: 6,
    wantDot: /API unreachable/,
    wantPage: /nothing answered/,
    forbid: ["No datasets yet", "Uploaded — profiled"],
  },
];

// R-13 (access floor): the three things the requirement names -- a drill-down a keyboard can reach, a focus
// state a keyboard can see, and status carried by text -- asserted against real DOM in the browser the tour
// already boots. axe-core is deliberately NOT used: adding it would be a new devDependency, and the
// permission contract reserves dependency changes for the user, so each rule below is implemented here and
// names the axe rule it reproduces (html-has-lang, valid-lang, document-title, landmark-one-main,
// link-name, button-name, label, image-alt).
//
// The routes are the analyst loop R-10 declares -- Ask, Runs, Reports, Datasets -- plus the landing, which
// is where a starter question and the language toggle actually live. The tour is backend-independent, so
// these pages render their empty and error states: that is enough for document rules, accessible names and
// focus, and `/datasets` carries a real `<details>` drill-down that needs no API to be walked.
const A11Y_PAGES = ["/", "/analysis", "/runs", "/reports", "/datasets"];
const A11Y_CHECKS_PER_PAGE = 3;

// The legal values of `<html lang>` come from the locale owner rather than a list typed here: a third
// language added to the toggle must be accepted by the check on the same commit that adds it.
function readLocales() {
  const src = readFileSync(join(webDir, "lib", "locale.ts"), "utf8");
  const block = src.match(/export const LOCALES[^=]*=\s*\[([^\]]*)\]/);
  if (!block) {
    throw new Error(
      "LOCALES is no longer a bracketed array in apps/web/lib/locale.ts -- the lang check cannot know which " +
        "values are legal, and a check that cannot fail is not a check"
    );
  }
  const values = [...block[1].matchAll(/["']([^"']+)["']/g)].map((m) => m[1]);
  if (values.length === 0) throw new Error(`LOCALES parsed empty from apps/web/lib/locale.ts`);
  return values;
}

const TAB_LIMIT = 120;

// Everything the keyboard can stop on, in document order, plus what it looks like *before* focus reaches it.
// The baseline matters: an input with a resting `shadow-sm` already has a non-none box-shadow, so comparing
// the shadow to `none` would certify a control whose ring never appears.
//
// `page.evaluate` ships a function's body to the browser and carries no closure over module scope, so every
// helper that runs in the page takes what it needs as an argument instead of reading these constants.
//
// The visibility test is `checkVisibility()`, not client rects: Chromium still lays out and measures the
// links inside a *closed* `<details>`, and those are not in the tab order. Measured on `/datasets` -- with
// rects alone the sweep reported 33 of 36 and the three missing stops were the diagnostics links under the
// collapsed disclosure, which made a clean run read like a focus trap.
const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), input:not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), summary, [role="button"], [role="tab"], [role="checkbox"], [role="switch"], [tabindex]:not([tabindex="-1"])';

const collectStops = (selector) => {
  const visible = (el) =>
    typeof el.checkVisibility === "function"
      ? el.checkVisibility({ checkOpacity: false })
      : el.getClientRects().length > 0 && getComputedStyle(el).visibility !== "hidden";
  return [...document.querySelectorAll(selector)]
    .filter(visible)
    .map((el, i) => {
      el.setAttribute("data-a11y-stop", String(i));
      const s = getComputedStyle(el);
      return {
        i,
        outlineStyle: s.outlineStyle,
        outlineWidth: s.outlineWidth,
        outlineColor: s.outlineColor,
        boxShadow: s.boxShadow,
        borderColor: s.borderTopColor,
        tag: el.tagName.toLowerCase(),
      };
    });
};

// A focus indicator is something a reader can see, so the outline's colour is part of the test and not an
// afterthought: this Tailwind builds `outline-none` as `outline: rgba(0,0,0,0) solid 2px`, which leaves the
// style and width looking present while painting nothing. Measured on a planted control -- a check that read
// only outline-style and outline-width called that transparent ring visible and stayed green.
const READ_FOCUS = () => {
  const el = document.activeElement;
  if (!el || el === document.body || el === document.documentElement) return null;
  const s = getComputedStyle(el);
  return {
    stop: el.getAttribute("data-a11y-stop"),
    outlineStyle: s.outlineStyle,
    outlineWidth: s.outlineWidth,
    outlineColor: s.outlineColor,
    boxShadow: s.boxShadow,
    borderColor: s.borderTopColor,
    focusVisible: el.matches(":focus-visible"),
    aria: el.getAttribute("aria-label"),
    text: (el.textContent ?? "").replace(/\s+/g, " ").trim().slice(0, 32),
  };
};

// `rgb(r g b / 0)` and `rgba(r, g, b, 0)` are both things Chromium reports for a transparent colour.
const isTransparent = (color) => {
  const m = /rgba?\(([^)]*)\)/.exec(color ?? "");
  if (!m) return false;
  const parts = m[1].split(/[\s,/]+/).filter(Boolean);
  if (parts.length < 4) return false;
  return Number(parts[3]) === 0;
};

// axe's name computation, in the order it resolves one: labelledby, label, a button input's value, the
// element's own text, then title. A placeholder counts as a name here -- axe accepts it too, while flagging
// placeholder-only labels as a separate, lower-severity rule -- so a control named only by placeholder
// passes and one named by nothing fails. Takes the interactive selector as an argument for the same reason
// `collectStops` does.
const accessibleNames = (selector) => {
  const describe = (el) => {
    const label = el.getAttribute("aria-label");
    const text = (el.textContent ?? "").replace(/\s+/g, " ").trim().slice(0, 32);
    return `${el.tagName.toLowerCase()}${label ? `[aria-label=${JSON.stringify(label)}]` : ""}${text ? ` "${text}"` : ""}`;
  };
  const visible = (el) =>
    typeof el.checkVisibility === "function"
      ? el.checkVisibility({ checkOpacity: false })
      : el.getClientRects().length > 0 && getComputedStyle(el).visibility !== "hidden";
  const nameOf = (el) => {
    const by = el.getAttribute("aria-labelledby");
    if (by) {
      const joined = by
        .split(/\s+/)
        .map((id) => document.getElementById(id)?.textContent ?? "")
        .join(" ")
        .trim();
      if (joined) return joined;
    }
    const label = el.getAttribute("aria-label");
    if (label && label.trim()) return label.trim();
    if (el instanceof HTMLInputElement && (el.type === "submit" || el.type === "button") && el.value.trim()) return el.value.trim();
    if (el instanceof HTMLInputElement && el.labels?.length) {
      const fromLabel = el.labels[0].textContent?.trim();
      if (fromLabel) return fromLabel;
    }
    if (el instanceof HTMLInputElement && el.placeholder.trim()) return el.placeholder.trim();
    if (el.tagName === "IMG") return (el.getAttribute("alt") ?? "").trim();
    const inside = el.querySelector("img[alt]");
    if (inside && inside.getAttribute("alt").trim()) return inside.getAttribute("alt").trim();
    const text = (el.textContent ?? "").trim();
    if (text) return text;
    const title = el.getAttribute("title");
    if (title && title.trim()) return title.trim();
    return "";
  };
  const unnamed = [...document.querySelectorAll(selector)]
    .filter((el) => visible(el) && !nameOf(el))
    .map(describe);
  const imgsWithoutAlt = [...document.querySelectorAll("img")].filter((el) => !el.hasAttribute("alt")).map(describe);
  return { unnamed, imgsWithoutAlt };
};

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

// `next start` serves whatever `.next` already holds -- it never builds. That is fine in CI, which builds
// first, and quietly wrong on a workstation: a bundle compiled from older source, or from a different
// `NEXT_PUBLIC_API_URL`, passes or fails for reasons that have nothing to do with this tree. Both cases were
// hit for real while capturing Lane D's evidence -- the acceptance build baked :8124, and the tour then
// reported the shared probe's page copy as missing because the page was talking to a dead origin.
function assertBundleMatchesThisTree() {
  const marker = join(webDir, ".next", "BUILD_ID");
  if (!existsSync(marker)) {
    throw new Error(`no build at ${marker}: run \`npm --prefix apps/web run build\` first`);
  }
  const builtAt = statSync(marker).mtimeMs;
  const sources = [];
  const walk = (dir) => {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const full = join(dir, entry.name);
      if (entry.isDirectory()) walk(full);
      else sources.push(full);
    }
  };
  for (const root of [join(webDir, "app"), join(webDir, "lib")]) if (existsSync(root)) walk(root);
  for (const extra of ["next.config.ts", "next.config.mjs", "package.json"]) {
    const full = join(webDir, extra);
    if (existsSync(full)) sources.push(full);
  }
  const stale = sources
    .filter((f) => statSync(f).mtimeMs > builtAt)
    .map((f) => `${relative(webDir, f)} (${((statSync(f).mtimeMs - builtAt) / 1000).toFixed(0)}s newer)`);
  if (stale.length > 0) {
    throw new Error(
      `the bundle predates the source it would be used to represent: ${stale.slice(0, 4).join(", ")}` +
        (stale.length > 4 ? ` and ${stale.length - 4} more` : "") +
        " -- run `npm --prefix apps/web run build`"
    );
  }
  const chunks = [];
  const staticDir = join(webDir, ".next", "static");
  if (existsSync(staticDir)) {
    const walkChunks = (dir) => {
      for (const entry of readdirSync(dir, { withFileTypes: true })) {
        const full = join(dir, entry.name);
        if (entry.isDirectory()) walkChunks(full);
        else if (full.endsWith(".js")) chunks.push(full);
      }
    };
    walkChunks(staticDir);
  }
  // The rule itself lives in `api-origin-verdict.mjs` so it can be exercised on forged inputs; this half is
  // only the reading. The source is the allow-list because `lib/api.ts` compiles
  // `(configuredApiUrl || "http://localhost:8000")` and minification keeps the fallback even when
  // NEXT_PUBLIC_API_URL is set, so a bundle built for another port legitimately carries two origins.
  const chunkOrigins = [];
  for (const chunk of chunks) chunkOrigins.push(...originsIn(readFileSync(chunk, "utf8")));
  const sourceOrigins = [];
  for (const file of sources) sourceOrigins.push(...originsIn(readFileSync(file, "utf8")));
  const call = verdict({ chunkOrigins, sourceOrigins, apiPort: API_PORT });
  if (!call.ok) {
    if (call.code === "no-baked-origin") {
      throw new Error(
        `no built chunk carries an origin on port ${call.detail.apiPort}, so this bundle was not compiled for ` +
          `the port the tour is guarding (the chunks hold: ${call.detail.chunk.slice(0, 3).join(", ") || "no loopback origin at all"}) ` +
          `-- build with NEXT_PUBLIC_API_URL=http://127.0.0.1:${API_PORT} and pass --api-port ${API_PORT}. ` +
          "A bundle aimed at a non-loopback API is not what this tour can verify, because its console-error " +
          "filter and its quiet-port preflight are both written against loopback."
      );
    }
    throw new Error(
      `the built bundle points at an API origin that this tree's source never names: ${call.detail.foreign.slice(0, 3).join(", ")}` +
        ` -- the tour is guarding port ${call.detail.apiPort} and \`apps/web/{app,lib}\` does not mention it, so ` +
        "the pages would be calling a different server than the console-error filter below is filtering"
    );
  }
}
try {
  assertBundleMatchesThisTree();
} catch (e) {
  console.error(`FAILURES:\n- preflight (bundle freshness): ${e instanceof Error ? e.message : e}`);
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
  // is the measured behaviour of a sleeping free instance (up to 92.8 s to first byte on the hosted demo) and no
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
      // The bound is the point: a state that appears after a whole attempt has timed out is a different
      // product than one that appears while the request is still in flight. 12.4 s was measured here once the
      // budget grew, and every assertion below would have passed at 12.4 s.
      if (scenario.wantWithinS !== undefined && Number(elapsed) > scenario.wantWithinS) {
        throw new Error(`${scenario.wantState} first appeared after ${elapsed}s, wanted within ${scenario.wantWithinS}s`);
      }
      const dotText = (await dot.innerText()).trim();
      if (scenario.wantDot && !scenario.wantDot.test(dotText)) {
        throw new Error(`dot read ${JSON.stringify(dotText)}, wanted ${scenario.wantDot}`);
      }
      // Next streams this route, and each page then waits on its own fetch: the shell paints first, the loading
      // skeleton replaces it, and the copy that names the backend's state only exists after that fetch has
      // failed. Reading the body at any earlier moment measures a page that has not decided yet -- which is how
      // this scenario came to fail at 0.1s with a body full of static text and no notice anywhere. So wait for
      // the page to be *decided*: real content, and no loading affordance left.
      try {
        await probePage.waitForFunction(
          () => {
            const main = document.querySelector("main");
            const text = (main?.innerText ?? "").trim();
            const loading = document.querySelector(
              '[aria-label="Loading table"], [aria-label="Loading page"], [aria-busy="true"]'
            );
            // A second, route-local sign that nothing has decided yet: this page's own first render says it is
            // checking the backend, and that text is longer than 20 characters and carries no aria-busy
            // attribute, so the predicate above let it through. Measured once under load: the header dot flipped
            // to "unreachable" at 0.1s while the main region still read "Checking API…", and the notice this
            // scenario asks for had not been rendered yet -- which is a passing-looking sample of a page that
            // had not made up its mind.
            const pending = text.includes("Checking API");
            return text.length > 20 && !loading && !pending;
          },
          null,
          { timeout: 15000, polling: 100 }
        );
      } catch {
        const still = await probePage
          .locator('[aria-label="Loading table"], [aria-label="Loading page"], [aria-busy="true"]')
          .count();
        throw new Error(
          `the page never reached a decided state within 15s: url=${probePage.url()} dot=${JSON.stringify(dotText)} ` +
            `loading affordances left=${still} main=${JSON.stringify(
              (await probePage.locator("main").first().innerText().catch(() => "")).slice(0, 120)
            )}`
        );
      }
      const body = await probePage.locator("body").innerText();
      if (!scenario.wantPage.test(body)) {
        // "the page never stated the wait" is not a diagnosis: this scenario passes standalone, so the
        // failure has to be captured with what the page did say, or the next reader is guessing too.
        await probePage.screenshot({ path: join(OUT, `probe-${scenario.wantState}-FAILED.png`) });
        throw new Error(
          `the page never stated the wait in its own words; wanted ${scenario.wantPage} after ${elapsed}s ` +
            `on ${probePage.url()} -- body said: ${JSON.stringify(body.replace(/\s+/g, " ").slice(0, 900))}`
        );
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

  // R-13: the access floor, one fresh context per route. A focus position or an open `<details>` left behind
  // by the previous page would change what the next page's tab sweep measures, so nothing is shared.
  for (const route of A11Y_PAGES) {
    const a11yContext = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const a11yPage = await a11yContext.newPage();
    try {
      await a11yPage.goto(`http://localhost:${PORT}${route}`, { waitUntil: "networkidle", timeout: 45000 });
      // Client components decide their own content a beat after the shell paints; the sweep needs the DOM
      // the reader actually gets, not the prerendered skeleton.
      await a11yPage.waitForTimeout(2000);

      // 1. Document rules. With the language toggle in place, `<html lang>` is no longer a constant -- it is
      // the one attribute that tells a screen reader which voice to use for the text under it.
      const doc = await a11yPage.evaluate(() => ({
        lang: document.documentElement.getAttribute("lang"),
        title: (document.title ?? "").trim(),
        mains: document.querySelectorAll("main").length,
      }));
      const docProblems = [];
      if (!doc.lang) docProblems.push(`no lang on <html> (the page is ${JSON.stringify(doc.title)})`);
      else if (!LOCALES.includes(doc.lang)) {
        docProblems.push(`lang=${JSON.stringify(doc.lang)} is not one of the locales apps/web/lib/locale.ts declares (${LOCALES.join(", ")})`);
      }
      if (!doc.title) docProblems.push("empty <title>");
      if (doc.mains !== 1) docProblems.push(`${doc.mains} <main> regions, wanted exactly 1`);
      if (docProblems.length > 0) {
        await a11yPage.screenshot({ path: join(OUT, `a11y-${slug(route)}-doc-FAILED.png`), fullPage: true });
        failures.push(`a11y ${route} document rules: ${docProblems.join("; ")}`);
      } else {
        console.log(`a11y ${route}: document rules -- lang=${doc.lang} title ok main=1`);
      }

      // 2. Accessible names. A control whose only label is a colour-coded icon is unreachable for a reader
      // who cannot see the colour, and axe rates it critical.
      const names = await a11yPage.evaluate(accessibleNames, FOCUSABLE_SELECTOR);
      if (names.unnamed.length > 0 || names.imgsWithoutAlt.length > 0) {
        await a11yPage.screenshot({ path: join(OUT, `a11y-${slug(route)}-names-FAILED.png`), fullPage: true });
        const parts = [];
        if (names.unnamed.length > 0) parts.push(`${names.unnamed.length} unnamed control(s) [${names.unnamed.slice(0, 5).join(", ")}]`);
        if (names.imgsWithoutAlt.length > 0) parts.push(`${names.imgsWithoutAlt.length} <img> without alt [${names.imgsWithoutAlt.slice(0, 5).join(", ")}]`);
        failures.push(`a11y ${route} accessible names: ${parts.join("; ")}`);
      } else {
        console.log(`a11y ${route}: accessible names -- every interactive element named, every img has alt`);
      }

      // 3. Keyboard: every tab stop must *show* that it has focus, and every drill-down must open on Enter.
      const stops = await a11yPage.evaluate(collectStops, FOCUSABLE_SELECTOR);
      const baseline = new Map(stops.map((s) => [s.i, s]));
      const focusProblems = [];
      let visited = 0;
      let lastStop = null;
      // How the walk ended decides whether the coverage line below is a finding or an artifact: "document"
      // is the normal end (the last stop handed focus to the browser), "repeat" and "budget" are not.
      let ended = "budget";
      for (let k = 0; k < TAB_LIMIT; k++) {
        await a11yPage.keyboard.press("Tab");
        const cur = await a11yPage.evaluate(READ_FOCUS);
        // Focus has left the document: the last stop handed it to the browser, so the sweep is complete.
        if (cur === null) {
          ended = "document";
          break;
        }
        const where = `${cur.stop === null ? "untracked " : `stop ${cur.stop} `}${cur.aria ? `[${cur.aria}]` : ""} ${cur.text}`.trim();
        if (lastStop !== null && cur.stop === lastStop) {
          focusProblems.push(`Tab did not move focus -- it stayed on ${where}`);
          ended = "repeat";
          break;
        }
        lastStop = cur.stop;
        visited += 1;
        const rest = cur.stop === null ? null : baseline.get(Number(cur.stop));
        const outlineShown =
          cur.outlineStyle !== "none" &&
          (cur.outlineStyle === "auto" || cur.outlineWidth !== "0px") &&
          !isTransparent(cur.outlineColor);
        const ringShown = rest
          ? cur.boxShadow !== rest.boxShadow || cur.borderColor !== rest.borderColor
          : cur.boxShadow !== "none";
        if (!outlineShown && !ringShown) {
          focusProblems.push(
            `${where}: no visible focus indicator (outline=${cur.outlineStyle} ${cur.outlineWidth} ` +
              `${cur.outlineColor}, box-shadow=${JSON.stringify(cur.boxShadow.slice(0, 48))}` +
              `${rest ? ` and border ${cur.borderColor} unchanged from resting` : ""}, :focus-visible=${cur.focusVisible})`
          );
        }
      }
      // Coverage, not a floor. The walk must account for every stop it marked: focus escaping the document
      // partway through looks identical to finishing, from the outside, and the "< 3" version this replaced
      // passed on a page where three stops were unreachable. `checkVisibility()` in the predicate is what
      // makes the two agree -- see the note above collectStops.
      if (ended === "budget") {
        focusProblems.push(`the sweep spent its ${TAB_LIMIT}-keypress budget after ${visited} of ${stops.length} stops -- the walk never finished`);
      } else if (ended === "document" && visited !== stops.length) {
        focusProblems.push(
          `the sweep reached ${visited} of ${stops.length} marked tab stops before focus left the document ` +
            "-- a control that moves focus on Tab, or one the keyboard cannot reach at all"
        );
      }
      if (stops.length < 3) {
        focusProblems.push(`only ${stops.length} keyboard stop(s) on the page -- a walk of nothing proves nothing`);
      }

      // The drill-down assertion is the R-13 user consequence stated literally: "a reviewer with a keyboard
      // must be able to reach the drill-down that is the whole product". Enter, not click.
      const summaries = a11yPage.locator("details > summary");
      const summaryCount = await summaries.count();
      let toggled = 0;
      for (let i = 0; i < summaryCount; i++) {
        const summary = summaries.nth(i);
        if (!(await summary.isVisible())) continue;
        const before = await summary.evaluate((el) => el.parentElement.open);
        await summary.focus();
        await a11yPage.keyboard.press("Enter");
        const after = await summary.evaluate((el) => el.parentElement.open);
        if (after === before) {
          focusProblems.push(
            `drill-down ${JSON.stringify((await summary.innerText()).trim().slice(0, 32))} did not toggle with Enter (open stayed ${after})`
          );
          continue;
        }
        toggled += 1;
        await a11yPage.keyboard.press("Enter");
        const restored = await summary.evaluate((el) => el.parentElement.open);
        if (restored !== before) {
          focusProblems.push(`drill-down toggled on the first Enter but not back on the second (open=${restored}, wanted ${before})`);
        }
      }

      if (focusProblems.length > 0) {
        await a11yPage.screenshot({ path: join(OUT, `a11y-${slug(route)}-keyboard-FAILED.png`) });
        failures.push(`a11y ${route} keyboard: ${focusProblems.join("; ")}`);
      } else {
        console.log(`a11y ${route}: keyboard -- ${visited}/${stops.length} tab stops visibly focussed, ${toggled} drill-down(s) opened by Enter`);
      }
    } catch (e) {
      failures.push(`a11y ${route} harness: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      await a11yContext.close();
    }
  }

  // R-13: every word the interface owns follows the visitor's language, on every static route, in both languages.
  //
  // The rule -- which DOM regions are the interface's, and which Latin-only strings are identifiers or the run's
  // own bytes -- lives in `locale-chrome-rules.mjs`, shared with `locale-chrome-acceptance.mjs`, because two
  // copies of a threshold are how a check starts meaning different things in CI and in a hand-run. This pass
  // runs with no backend (the tour refuses a live API port), so table column heads are not rendered and the
  // regions it can see are the shell, the headings, the labels, the tabs and the buttons; the seeded acceptance
  // covers the row-dependent ones. Each line prints the route's own appetite, because a check that exempted
  // everything would report this same green.
  for (const locale of ["zh", "en"]) {
    const localeContext = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    await localeContext.addCookies([{ name: "dsa_locale", value: locale, domain: "localhost", path: "/" }]);
    const localePage = await localeContext.newPage();
    for (const route of ROUTES) {
      const label = `locale ${locale} ${route}`;
      try {
        await localePage.goto(`http://localhost:${PORT}${route}`, { waitUntil: "domcontentloaded", timeout: 45000 });
        await localePage.waitForTimeout(1200);
        const text = await localePage.evaluate(() => document.body.innerText);
        if (text.includes("\u27e8")) throw new Error("a missing-key marker is on the page, so a string has no owner in this locale");
        const regions = await localePage.evaluate(
          ({ sel }) =>
            [...document.querySelectorAll(sel)]
              .filter((el) => el.offsetParent !== null || el.tagName === "OPTION")
              .map((el) => ({ tag: el.tagName.toLowerCase(), text: (el.textContent || "").replace(/\s+/g, " ").trim() }))
              .filter((x) => x.text),
          { sel: CHROME_SELECTOR }
        );
        const seen = classifyChromeRegions(regions);
        if (locale === "zh") {
          if (seen.total < 6) throw new Error(`only ${seen.total} chrome regions -- the selector matched nothing, so this proves nothing`);
          if (seen.leaks.length) {
            throw new Error(
              `English chrome on a 中文 page: ${seen.leaks.slice(0, 4).map((c) => `${c.tag}:"${c.text.slice(0, 48)}"`).join(" | ")}`
            );
          }
          if (seen.cjk < 3) throw new Error(`a 中文 page with almost no Chinese chrome (${seen.cjk} of ${seen.total} regions)`);
        }
        console.log(
          `locale ${locale} ${route}: ${seen.total} chrome regions, ${seen.cjk} CJK, ${seen.exempt.length} exempt` +
            (locale === "zh" ? `, ${seen.leaks.length} leak(s)` : "")
        );
      } catch (e) {
        failures.push(`${label}: ${e instanceof Error ? e.message : String(e)}`);
      }
    }
    await localeContext.close();
  }
} catch (e) {
  failures.push(`harness: ${e instanceof Error ? e.message : String(e)}\n${serverLog.slice(-1500)}`);
} finally {
  await browser?.close();
  killServer();
}

const ROUTE_CHECKS = ROUTES.length * VIEWPORTS.length;
const A11Y_CHECKS = A11Y_PAGES.length * A11Y_CHECKS_PER_PAGE;
const LOCALE_CHECKS = ROUTES.length * 2;
const TOTAL_CHECKS = ROUTE_CHECKS + INTERACTIONS.length + PROBE_SCENARIOS.length + A11Y_CHECKS + LOCALE_CHECKS;
console.log(
  `\nregression: ${TOTAL_CHECKS - failures.length}/${TOTAL_CHECKS} checks passed ` +
    `(${ROUTE_CHECKS} route/viewport + ${INTERACTIONS.length} interaction + ${PROBE_SCENARIOS.length} backend-probe ` +
    `+ ${A11Y_CHECKS} accessibility + ${LOCALE_CHECKS} locale), screenshots in ${OUT}`,
);
if (failures.length > 0) {
  console.error("FAILURES:\n- " + failures.join("\n- "));
}
// Force-exit: lingering child handles must never hang CI.
process.exit(failures.length > 0 ? 1 : 0);
