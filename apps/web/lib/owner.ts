// R-08: the id this browser uses to keep its own datasets and runs apart from the next visitor's.
//
// There are no accounts on the hosted demo, and the plan says a half-account system is worse than honesty. So
// this is not a login: it is a random id, generated once per browser and stored in a first-party cookie, that
// the API uses as the owner column on every row it writes. It stops the next visitor from reading your upload.
// It does not stop someone who takes the cookie, and `docs/hosted-demo.md` says so in those words.
//
// One cookie rather than also a localStorage entry, because the pages disagree about where they run. Half of
// this app fetches from a Next server component -- during render, in a process that cannot see the browser's
// storage -- and a custom header cannot be attached to the browser's own navigation. A first-party cookie is
// the one value both halves can read: the proxy puts it there before any render, the server components take it
// from the request, and the client components take it from `document`. It is deliberately not `HttpOnly`, which
// is the part a reader should weigh: a script running on this origin could read the id. It is also deliberately
// absent from URLs, where it would live in history, in server logs, and in `Referer` headers.
export const OWNER_COOKIE = "dsa_owner";

// The name the API reads. Kept here so the header cannot drift from what `dsa_api.core.ownership` parses.
export const OWNER_HEADER = "X-DSA-Owner";

// The query-string name the API accepts for the links a browser opens by itself. Same value, same validation.
export const OWNER_QUERY = "owner";

// The same shape the server validates, so a value the API would ignore is never sent.
const OWNER_SHAPE = /^[A-Za-z0-9_-]{1,64}$/;

export function cookieValue(raw: string | null | undefined): string | null {
  return raw && OWNER_SHAPE.test(raw) ? raw : null;
}

/** A new owner id. `crypto.randomUUID` is the normal path; the fallback keeps a non-secure origin working. */
export function newOwnerId(): string {
  const buffer = new Uint8Array(16);
  if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
  if (typeof crypto !== "undefined" && crypto.getRandomValues) {
    crypto.getRandomValues(buffer);
  } else {
    for (let i = 0; i < buffer.length; i += 1) buffer[i] = Math.floor(Math.random() * 256);
  }
  return [...buffer].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

export function ownerHeaders(id: string | null): Record<string, string> {
  return id ? { [OWNER_HEADER]: id } : {};
}

/**
 * Put the id in the URL, for the handful of links a browser opens itself.
 *
 * A new tab is a plain navigation: no script runs first, so no header can be attached. That leaves the query --
 * and the query is where an id becomes visible in history, which is why only the three report links below use
 * it, why they carry `rel="noreferrer"`, and why `docs/hosted-demo.md` says the id in a URL is the weaker of the
 * two transports rather than pretending it is free.
 */
export function withOwnerParam(url: string, id: string | null): string {
  if (!id) return url;
  return `${url}${url.includes("?") ? "&" : "?"}${OWNER_QUERY}=${encodeURIComponent(id)}`;
}

/** The id this browser is already using, or null when the proxy has not had a chance to set one yet. */
export function browserOwnerId(): string | null {
  if (typeof document === "undefined") return null;
  const prefix = `${OWNER_COOKIE}=`;
  for (const part of document.cookie.split(";")) {
    const entry = part.trim();
    if (entry.startsWith(prefix)) return cookieValue(entry.slice(prefix.length));
  }
  return null;
}

/**
 * Headers for a request the browser makes itself, with the owner id merged in.
 *
 * Spread last so a caller that set its own `headers` object keeps it; the id is the only thing added here.
 */
export function withOwner(init: RequestInit | undefined, id: string | null): RequestInit {
  const base = init ?? {};
  const headers = new Headers(base.headers ?? {});
  const owner = ownerHeaders(id);
  for (const [name, value] of Object.entries(owner)) headers.set(name, value);
  return { ...base, headers };
}
