#!/usr/bin/env node
// The MCP App page has never been opened by an instrument, so nothing checked that it boots at all.
//
// `tests/mcp/test_app_page_escaping.py` calls the two renderers out of the shipped page script and proves they
// escape. It cannot prove the page reaches them: `loadDatasets()` runs `resources/list`, maps the result into
// `<option>` elements, and wraps all of it in a `try` whose `catch` replaces the whole dropdown with one hard-coded
// fallback option. Before the escaping fix, a single resource missing its `description` threw on
// `x.description.slice(0,60)` and every dataset on the instance disappeared behind that fallback -- no error, no
// log, one option left. A guard that only reads the renderer is blind to exactly that, because the renderer was
// never called.
//
// So this asks the browser the question the probe cannot: does the live page list the datasets the live server
// publishes? It compares the page's `<option>` set against `resources/list` fetched over HTTP, which is the same
// call the page makes. Equal counts and matching values mean the script ran end to end on this instance.
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const API = process.env.R13I_API || "http://127.0.0.1:8000";

const rpc = async (method, params) => {
  const r = await fetch(`${API}/mcp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: Date.now(), method, params }),
  });
  if (!r.ok) throw new Error(`${method} answered HTTP ${r.status}`);
  return r.json();
};

let published;
try {
  published = await rpc("resources/list", {});
} catch (e) {
  console.error(
    `no MCP endpoint at ${API}/mcp (${e.message}) -- this instrument needs the API this repo's own ` +
      "`run_web_live_gates.sh` boots; it never runs against a static build",
  );
  process.exit(2);
}
const ds = ((published.result && published.result.resources) || []).filter((x) =>
  String(x.uri).startsWith("dataset://"),
);
if (ds.length === 0) {
  console.error("the instance publishes no dataset:// resource, so the option list would prove nothing");
  process.exit(2);
}

const browser = await chromium.launch();
let failures = 0;
let readFrame = null;
const fail = (claim, detail) => {
  failures += 1;
  console.error(`FAIL ${claim}${detail ? ` -- ${detail}` : ""}`);
};

try {
  const page = await browser.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e.message || e)));
  page.on("console", (m) => {
    if (m.type() === "error") errors.push(m.text());
  });
  page.on("dialog", (d) => {
    void d.dismiss();
  });
  const response = await page.goto(`${API}/mcp-app/`, { waitUntil: "domcontentloaded" });
  if (!response || !response.ok()) {
    fail("mcpAppRouteAnswers", `${API}/mcp-app/ -> ${response && response.status()}`);
  } else {
    const csp = response.headers()["content-security-policy"] || "(absent)";
    await page
      .waitForFunction(() => document.querySelectorAll("#dataset option").length > 0, null, {
        timeout: 15_000,
      })
      .catch(() => {
        fail(
          "pageScriptRanAtAll",
          `no <option> after 15s; CSP was "${csp}"; first errors: ${errors.slice(0, 2).join(" | ") || "(none logged)"}`,
        );
      });
    const shown = await page.$$eval("#dataset option", (els) =>
      els.map((el) => ({ value: el.value, text: el.textContent.trim() })),
    );
    if (shown.length !== ds.length) {
      fail(
        "everyPublishedDatasetIsOffered",
        `server publishes ${ds.length}, the page offers ${shown.length} (${JSON.stringify(shown.slice(0, 3))})`,
      );
    }
    for (const [i, res] of ds.entries()) {
      const opt = shown[i];
      if (!opt) break;
      if (opt.value !== res.uri) fail("optionValueIsTheResourceUri", `want ${res.uri}, got ${opt.value}`);
      const expected = `${res.name} — ${String(res.description ?? "").slice(0, 60)}`;
      if (opt.text !== expected) {
        fail("optionTextIsNameDashDescription", `want ${JSON.stringify(expected)}, got ${JSON.stringify(opt.text)}`);
      }
    }
    // The report card is the other half of the page, and it is the half R-14c claimed worked: the App embeds
    // /mcp-app/report/{id} in an iframe, which needs both a frame-src the host allows and a framed document whose
    // own policy admits its inline CSS. Only TestClient had ever looked, so only a browser could say whether the
    // frame is empty. A stored run is asked for the way the product's own instruments ask: as the shared owner.
    let storedRun = null;
    try {
      const listed = await fetch(`${API}/api/v1/analysis/`, { headers: { "X-DSA-Owner": "shared" } });
      const rows = listed.ok ? await listed.json() : {};
      const items = rows.items ?? rows.analyses ?? [];
      storedRun = items[0]?.id ?? items[0]?.run_id ?? null;
    } catch {
      storedRun = null;
    }
    if (storedRun) {
      const framed = await page.goto(`${API}/mcp-app/?run_id=${encodeURIComponent(storedRun)}`, {
        waitUntil: "domcontentloaded",
      });
      if (!framed || !framed.ok()) {
        fail("mcpAppRouteAnswersForAStoredRun", `${API}/mcp-app/?run_id=${storedRun} -> ${framed && framed.status()}`);
      } else {
        await page
          .waitForSelector("#reportFrame:not([hidden])", { timeout: 15_000 })
          .catch(() => fail("reportFrameIsRevealed", `run ${storedRun}`));
        const heading = await page
          .locator("#reportFrame")
          .evaluate((el) => {
            const doc = el.contentDocument;
            if (!doc) return null;
            const h1 = doc.querySelector("h1");
            return {
              h1: h1 ? h1.textContent.trim() : null,
              disclosures: doc.querySelectorAll("details").length,
              stylesApplied: h1 ? getComputedStyle(h1).fontSize : null,
            };
          })
          .catch(() => null);
        if (!heading || !heading.h1) {
          fail("reportFrameHoldsTheRenderedDocument", `run ${storedRun}, read ${JSON.stringify(heading)}`);
        } else if (heading.disclosures === 0) {
          fail("reportFrameCarriesItsDrillDowns", `run ${storedRun} rendered "${heading.h1}" with 0 <details>`);
        } else if (heading.stylesApplied !== "24px") {
          // The report's own stylesheet sets h1 to 1.5rem; a blocked <style> leaves the UA default of 32px, so this
          // reads the applied value rather than trusting that a <style> tag in the bytes means the browser used it.
          fail("reportFrameStyleWasApplied", `h1 computed ${heading.stylesApplied}, the report's CSS says 24px`);
        } else {
          readFrame = `${heading.h1.slice(0, 44)} | ${heading.disclosures} disclosure(s) | h1 ${heading.stylesApplied}`;
        }
      }
    } else {
      console.log("note: no stored run on this instance, so the report frame was not read");
    }
    // The escaping boundary, read as DOM rather than as a string: nothing inside the option list may be an
    // element, because every field in it came from a file's own header row or name.
    const injected = await page.$$eval("#dataset", (els) =>
      els.reduce((n, el) => n + el.querySelectorAll("img,script,svg,iframe,onerror").length, 0),
    );
    if (injected !== 0) fail("optionListCarriesNoElements", `${injected} element(s) inside #dataset`);
    if (errors.length) fail("pageScriptThrewNoErrors", errors.slice(0, 3).join(" | "));
  }
} catch (e) {
  fail("mcpAppPageLoaded", String(e.message || e));
} finally {
  await browser.close();
}

if (failures) {
  console.error(`MCP_APP_PAGE_FAIL (${failures} check(s))`);
  process.exit(1);
}
console.log(
  `MCP_APP_PAGE_PASS (${ds.length} dataset(s) offered by the live page, values and labels matched)` +
    (readFrame ? `; report frame read in place: ${readFrame}` : "; no stored run, report frame not read"),
);
