/**
 * The bundle-freshness decision, kept free of filesystem and browser work so it can be exercised on
 * forged inputs. `apps/web/scripts/regression.mjs` reads the chunks and the sources and calls `verdict`.
 *
 * This started as a one-sided test: refuse any origin in the bundle whose port differs from `--api-port`.
 * That is wrong, because `apps/web/lib/api.ts` compiles `(configuredApiUrl || "http://localhost:8000")` and
 * minification keeps the fallback even when NEXT_PUBLIC_API_URL is set. Building for :8010 therefore leaves
 * BOTH `127.0.0.1:8010` and `localhost:8000` in a chunk, and the one-sided rule refused the rebuild its own
 * error message told the operator to run -- measured: `--api-port 8010` on such a build exited 1.
 *
 * The rule is now two-sided, and the second half is what keeps the first from becoming a no-op: the port
 * under test must be *present*, and no other origin may appear unless the current source names it.
 */

// An origin, not any URL. `API_BASE_URL` compiles to a bare `http://localhost:PORT`, while an endpoint
// written in interface text carries a path (`http://localhost:11434/v1` is the Ollama placeholder on the
// settings page). Without the lookahead the tour reads a placeholder as a configured origin and refuses.
// A factory rather than one shared `/g` literal, so a caller cannot inherit another's `lastIndex`.
export function bareOriginPattern() {
  return /https?:\/\/(?:localhost|127\.0\.0\.1):\d{2,5}(?![\d./-])/g;
}

export function originsIn(text) {
  return [...String(text).matchAll(bareOriginPattern())].map((m) => m[0]);
}

const HOSTS = ["localhost", "127.0.0.1"];
const SCHEMES = ["http", "https"];

/** The four spellings of "this port, on loopback". Both edges of the rule read this one list: the presence
 *  check and the allow-list have to accept exactly the same set, or a bundle can satisfy the first and be
 *  refused by the second for the same origin. */
export function loopbackOrigins(port) {
  return SCHEMES.flatMap((s) => HOSTS.map((h) => `${s}://${h}:${port}`));
}

const isLoopbackOriginFor = (origin, port) => loopbackOrigins(port).includes(origin);

/**
 * @param chunkOrigins origins found in the built bundle
 * @param sourceOrigins origins found in this tree's `apps/web/{app,lib}` and configs
 * @param apiPort the port the tour is guarding
 * @returns {{ok: true}} or {{ok: false, code, detail}} -- never a thrown string, so the caller writes the
 *          operator-facing sentence and this stays about the rule.
 */
export function verdict({ chunkOrigins, sourceOrigins, apiPort }) {
  const chunk = new Set(chunkOrigins);
  const allowed = new Set([...sourceOrigins, ...loopbackOrigins(apiPort)]);
  if (![...chunk].some((o) => isLoopbackOriginFor(o, apiPort))) {
    return { ok: false, code: 'no-baked-origin', detail: { chunk: [...chunk], apiPort } };
  }
  const foreign = [...chunk].filter((o) => !allowed.has(o));
  if (foreign.length > 0) {
    return { ok: false, code: 'origin-not-in-source', detail: { foreign, apiPort } };
  }
  return { ok: true };
}
