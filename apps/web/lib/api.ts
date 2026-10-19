import { browserOwnerId, withOwner } from "./owner";
import { t, type Locale } from "./locale";

const configuredApiUrl = process.env.NEXT_PUBLIC_API_URL?.trim();

export const API_BASE_URL = (configuredApiUrl || "http://localhost:8000").replace(/\/$/, "");

export function apiUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
}

// R-08: a request the browser makes itself carries this visitor's owner id, so the API answers with their rows
// rather than with everyone's. Server-rendered pages cannot use this -- they are not running where the cookie
// lives, and call `serverFetch` from `@/lib/serverApi` instead.
export function clientFetch(path: string, init?: RequestInit): Promise<Response> {
  return fetch(apiUrl(path), withOwner(init, browserOwnerId()));
}

// Fetch outcomes, owned here. "no data" is a fact about the payload; a 401, a 500 and an unreachable
// API are facts about the request, and collapsing them into an empty list told an operator who followed
// docs/api.md's DSA_AUTH_TOKEN advice that the product contained nothing (audit §160 item 6). Pages keep
// their own local shapes; only this vocabulary is shared. tests/contract/test_web_fetch_outcome_vocabulary.py
// compares the kinds listed here against the classifier and the pages that consume them.
export const API_FAILURE_KINDS = ["unauthorized", "notFound", "serverError", "clientError", "transport"] as const;

export type ApiFailure = (typeof API_FAILURE_KINDS)[number];

/** null when the response is 2xx; otherwise the kind a reader should be told about. */
export function classifyResponse(res: Response): ApiFailure | null {
  if (res.ok) return null;
  if (res.status === 401 || res.status === 403) return "unauthorized";
  if (res.status === 404) return "notFound";
  if (res.status >= 500) return "serverError";
  return "clientError";
}

// One line per kind, rendered straight into ErrorState. Names stay generic -- no status code is dumped
// at a reader, and no raw response body is carried through.
//
// R-13: the words live in `lib/locale.ts`, so this is a derivation with no second copy of any sentence. The
// five keys are listed one per kind on purpose: the return type is checked against `ApiFailure` by the
// compiler, so a sixth kind added to `API_FAILURE_KINDS` breaks the build rather than rendering a blank line,
// and tests/contract/test_web_fetch_outcome_vocabulary.py checks the same five keys against both locales.
export function failurePresentation(locale: Locale): Record<ApiFailure, string> {
  return {
    unauthorized: t(locale, "fail.unauthorized"),
    notFound: t(locale, "fail.notFound"),
    serverError: t(locale, "fail.serverError"),
    clientError: t(locale, "fail.clientError"),
    transport: t(locale, "fail.transport"),
  };
}
