"""R-08: the browser half of owner scoping -- one id, sent everywhere it is needed and nowhere it is not.

The API side is `test_owner_scoped_storage.py`: two visitors, one database, every route answered with the same
404. That half is worthless if the shipped client never sends an id, because then every visitor *is* the local
owner and the demo leaks exactly as before. The client half cannot be tested through pytest, so these guards
read the TypeScript corpus the way the other `test_web_*` files do -- and they are written to fail on the two
mistakes that would make R-08 look shipped while it was not:

1. **A page that reads scoped data without the id.** Census: no file may call the API by building a URL and
   passing it to `fetch` directly. Two modules do that on purpose, both named below with the reason, and a new
   one has to be argued into the list rather than added to it.
2. **The id travelling where it should not.** It goes in a header for everything the app fetches itself, and in
   a URL for exactly the three report links a browser opens as a navigation -- because a navigation cannot
   carry a header. A fourth place is how a bearer id ends up in browser history and access logs.

Then the parts that connect the two corpora: the header and query names are read from the Python module and
compared with the TypeScript constants, so the demo cannot be half-scoped by a rename; the proxy is shown to
own the cookie and to leave an existing one alone; and the disclosure line at the upload control is required to
say both what the id does and what it does not, which is the sentence a reader judges the whole feature by.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "apps/web"
OWNER_TS = WEB / "lib/owner.ts"
SERVER_API_TS = WEB / "lib/serverApi.ts"
API_TS = WEB / "lib/api.ts"
PROXY_TS = WEB / "proxy.ts"
UPLOAD_PAGE = WEB / "app/datasets/page.tsx"
RUN_PAGE = WEB / "app/analysis/[runId]/page.tsx"
PY_OWNERSHIP = ROOT / "apps/api/src/dsa_api/core/ownership.py"

#: Files allowed to call the API without an owner id, and the reason each one is allowed.
RAW_CALL_EXCEPTIONS = {
    # A reachability probe. Attaching an id would turn a health check into a data request, and /health answers
    # the same either way -- so a failure here would be reported as "the API is down" for the wrong reason.
    "apps/web/app/lib/backendProbe.ts": "/health, deliberately unscoped",
    # `dsa ui` and the Vercel build read /version at build time, where there is no request to take a cookie from.
    # Routing it through `serverFetch` would throw, because `next/headers` needs a request context.
    "apps/web/lib/buildProvenance.ts": "/version at build time, no request context",
    # The funnel's page-view event. It must not learn the owner id -- see `test_telemetry_never_carries_the_owner_id`
    # for the rule, and the vocabulary's prohibited key list for why a per-visitor id would be a session key.
    "apps/web/app/lib/productEvents.ts": "telemetry, deliberately unscoped",
}


def _sources() -> dict[str, str]:
    files: dict[str, str] = {}
    for path in list(WEB.glob("app/**/*.ts*")) + list(WEB.glob("lib/**/*.ts*")) + [PROXY_TS]:
        if path.is_file():
            files[str(path.relative_to(ROOT))] = path.read_text(encoding="utf-8")
    return files


def _raw_api_calls(text: str) -> int:
    """Every call that builds an API URL and hands it to `fetch` itself, bypassing both wrappers."""
    return len(re.findall(r"fetch\(\s*(?:apiUrl\(|`\$\{API_BASE_URL\})", text))


def test_the_owner_header_name_is_one_string_in_two_languages() -> None:
    """A rename on one side silently unscopes the other: the API would answer the local owner to everyone."""
    python = PY_OWNERSHIP.read_text(encoding="utf-8")

    def _constant(source: str, name: str, path: Path) -> str:
        match = re.search(rf'{name}\s*=\s*"([^"]+)"', source)
        assert match, (
            f"{name} is not a plain string literal in {path.name}, so this guard checks nothing"
        )
        return match.group(1)

    py_header = _constant(python, "OWNER_HEADER", PY_OWNERSHIP)
    py_query = _constant(python, "OWNER_QUERY", PY_OWNERSHIP)
    ts_header = _constant(OWNER_TS.read_text(encoding="utf-8"), "OWNER_HEADER", OWNER_TS)
    ts_query = _constant(OWNER_TS.read_text(encoding="utf-8"), "OWNER_QUERY", OWNER_TS)

    assert py_header == ts_header, (
        f"the API parses {py_header!r} and the client sends {ts_header!r}"
    )
    assert py_query == ts_query, f"the API parses {py_query!r} and the links carry {ts_query!r}"
    assert py_header != py_query, (
        "a header and a query parameter cannot share a name and stay distinguishable"
    )


def test_no_page_fetches_the_api_without_saying_who_it_is() -> None:
    """The census. `clientFetch` and `serverFetch` are the only doors, and a page that opens its own is a leak."""
    offenders: dict[str, str] = {}
    for name, text in _sources().items():
        count = _raw_api_calls(text)
        if count:
            offenders[name] = f"{count} raw call(s)"

    allowed = {
        "apps/web/lib/owner.ts",
        "apps/web/lib/serverApi.ts",
        "apps/web/lib/api.ts",
        "apps/web/proxy.ts",
    }  # the wrappers themselves own the single `fetch` each
    allowed |= set(RAW_CALL_EXCEPTIONS)
    assert set(offenders) <= allowed, (
        f"{sorted(offenders)} build API URLs and fetch them directly. Wrap the call in `clientFetch` (browser) "
        f"or `serverFetch` (server component) so it carries this visitor's owner id, or add the file to "
        f"RAW_CALL_EXCEPTIONS with the reason it genuinely must not: {offenders}"
    )
    # ...and every declared exception must still be one, so a file that no longer needs the exemption is noticed.
    for name, reason in RAW_CALL_EXCEPTIONS.items():
        assert name in offenders, (
            f"{name} is exempted for {reason}, but it no longer makes a raw call at all"
        )


def test_the_id_is_attached_on_both_sides_of_the_render_boundary() -> None:
    """Each wrapper has to add the header, and each must get the id from where its own runtime can see it."""
    client = API_TS.read_text(encoding="utf-8")
    server = SERVER_API_TS.read_text(encoding="utf-8")

    client_body = re.search(r"export function clientFetch\(.*?\n\}", client, re.S)
    server_body = re.search(r"export async function serverFetch\(.*?\n\}", server, re.S)
    assert client_body and server_body, "a wrapper stopped being a plain exported function"

    for name, body in (
        ("clientFetch", client_body.group(0)),
        ("serverFetch", server_body.group(0)),
    ):
        assert "withOwner(" in body, f"{name} no longer merges the owner header into the request"
        assert "fetch(" in body, f"{name} does not make a request, so it is not a wrapper"

    assert "browserOwnerId()" in client_body.group(0), (
        "the browser wrapper stopped reading the cookie the proxy set, so it would send no id"
    )
    assert "ownerFromRequest()" in server_body.group(0), (
        "the server wrapper stopped reading the incoming request's cookie"
    )
    assert 'from "next/headers"' in server, "serverFetch must take the cookie off the request"
    assert 'from "next/headers"' not in client, (
        "lib/api.ts is imported by client components, where next/headers cannot run"
    )


def test_a_client_component_never_uses_the_server_wrapper() -> None:
    """`cookies()` inside a Client Component is a build error -- caught here with the file that did it."""
    imported = re.compile(r'import \{([^}]*)\} from "@/lib/(api|serverApi)"')
    for name, text in _sources().items():
        if name in ("apps/web/lib/api.ts", "apps/web/lib/serverApi.ts", "apps/web/lib/owner.ts"):
            continue  # the modules that define the wrappers
        is_client = text.lstrip().startswith('"use client"')
        imported_names = {
            part.strip() for match in imported.finditer(text) for part in match.group(1).split(",")
        }
        if "serverFetch" in imported_names:
            assert not is_client, f"{name} is a Client Component and cannot read request cookies"
        if "clientFetch" in imported_names:
            assert is_client, f"{name} reads the browser's cookie but is not a Client Component"


def test_the_proxy_owns_the_cookie_and_only_creates_a_missing_one() -> None:
    """First paint has to already know the id, and a new id per request would scatter a visitor's rows."""
    proxy = PROXY_TS.read_text(encoding="utf-8")
    assert "OWNER_COOKIE" in proxy and "response.cookies.set(" in proxy, (
        "nothing sets the cookie, so no visitor ever has an id"
    )
    assert 'from "./lib/owner"' in proxy, (
        "the proxy declared its own cookie name instead of importing it -- the two would drift"
    )
    assert 'sameSite: "lax"' in proxy, (
        "without lax the cookie is not sent on the visitor's own navigation, which is the only way a server "
        "component can learn the id"
    )
    assert "httpOnly" not in proxy, (
        "the client-rendered pages read the cookie themselves, so HttpOnly would scope them out"
    )
    guards = [
        line
        for line in proxy.splitlines()
        if line.strip().startswith("if (cookieValue(") and "return NextResponse.next();" in line
    ]
    assert guards, (
        "the proxy no longer leaves an existing id alone, so every request would mint a new owner"
    )


def test_the_url_transport_is_limited_to_the_links_a_browser_opens() -> None:
    """An id in a URL survives in history and access logs; three report links are the whole reason it exists."""
    used = {
        name
        for name, text in _sources().items()
        if "withOwnerParam(" in text and name != "apps/web/lib/owner.ts"
    }
    assert used == {"apps/web/app/analysis/[runId]/page.tsx"}, (
        f"{sorted(used)} put the owner id in a URL. Anything the app fetches itself must use a header"
    )
    page = RUN_PAGE.read_text(encoding="utf-8")
    assert page.count("withOwnerParam(") == 3, (
        "the three report links (audited markdown, plain markdown, html) are the complete set; a different "
        "count means one stopped carrying the id or something else joined them"
    )


def test_the_upload_control_says_what_the_id_does_and_does_not_do() -> None:
    """The sentence a visitor judges this by, pinned so a later copy edit cannot turn it into a promise."""
    copy = " ".join(UPLOAD_PAGE.read_text(encoding="utf-8").split())
    for phrase in ("first-party cookie", "not an account", "anyone holding that id"):
        assert phrase in copy, (
            f"the disclosure at the upload control no longer says {phrase!r}: the line has to name both the "
            "mechanism and its limit, not just the reassuring half"
        )


def test_telemetry_never_carries_the_owner_id() -> None:
    """`arrival` counts page views across visitors; a per-visitor id would turn it into a session identifier."""
    events = (WEB / "app/lib/productEvents.ts").read_text(encoding="utf-8")
    assert "owner" not in events.lower(), (
        "the event client now knows about owner ids; the vocabulary forbids a user or session key"
    )
