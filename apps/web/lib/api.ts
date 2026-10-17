import { browserOwnerId, withOwner } from "./owner";

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
export const FAILURE_PRESENTATION: Record<ApiFailure, string> = {
  unauthorized:
    "The API is reachable but rejected the request (401/403). This demo does not ask you to sign in, so a " +
    "rejection here means the instance is configured with an access token this page does not hold.",
  notFound: "The API answered 404 — the requested record or endpoint does not exist.",
  serverError: "The API failed while answering (5xx). This data may be temporarily unavailable.",
  clientError: "The API answered with a client error (4xx). The request was not accepted.",
  transport: "No response could be read from the API. Check that it is running and reachable from this origin.",
};
