// Server-side API reads, with this visitor's owner id attached.
//
// Half of this app renders on the Next server, where the browser's storage is not available: the id has to come
// off the incoming request's cookie and go onto the outgoing call as a header, or every page below would be read
// as the local owner and show the published sample instead of the person's own runs.
//
// `next/headers` makes this module server-only. Client components use `clientFetch` from `@/lib/api` instead --
// mixing the two is a build error, and tests/contract/test_web_owner_identity.py names the file that did it.
import { cookies } from "next/headers";

import { apiUrl } from "./api";
import { OWNER_COOKIE, cookieValue, withOwner } from "./owner";

/** The owner id this browser sent with the current navigation, or null before the proxy has set one. */
export async function ownerFromRequest(): Promise<string | null> {
  const store = await cookies();
  return cookieValue(store.get(OWNER_COOKIE)?.value);
}

export async function serverFetch(path: string, init?: RequestInit): Promise<Response> {
  return fetch(apiUrl(path), withOwner({ cache: "no-store", ...init }, await ownerFromRequest()));
}
