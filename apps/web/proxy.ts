// R-08: give every browser an owner id before the first render happens.
//
// The id has to exist *before* a page is rendered, not after hydration: a server component cannot write a
// cookie, and a visitor whose first navigation arrives with no id would be shown the published sample and
// nothing else -- which is the same page a stranger sees. So this runs ahead of rendering, hands the cookie to
// the browser, and leaves every later request alone.
//
// First-party and `sameSite: lax`, which is the whole point: the browser sends it to this app's own server on a
// normal navigation. The API is a different origin, so it never sees the cookie -- the pages read it and put it
// in the `X-DSA-Owner` header, which is also why it is not `HttpOnly`: the client-rendered pages have to read
// it themselves. What that costs is written down in `docs/hosted-demo.md`.
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { OWNER_COOKIE, cookieValue, newOwnerId } from "./lib/owner";

// Roughly a year, and long enough that a returning visitor keeps the same view of their own data.
const OWNER_LIFETIME_SECONDS = 60 * 60 * 24 * 400;

export function proxy(request: NextRequest): NextResponse {
  if (cookieValue(request.cookies.get(OWNER_COOKIE)?.value)) return NextResponse.next();

  const response = NextResponse.next();
  response.cookies.set(OWNER_COOKIE, newOwnerId(), {
    path: "/",
    maxAge: OWNER_LIFETIME_SECONDS,
    sameSite: "lax",
    secure: request.nextUrl.protocol === "https:",
  });
  return response;
}

export const config = {
  // Pages only. Static chunks and public files need no identity, and running here would put a `Set-Cookie` on
  // every asset request.
  matcher: ["/((?!_next/static|_next/image|favicon.ico|robots.txt|sitemap.xml).*)"],
};
