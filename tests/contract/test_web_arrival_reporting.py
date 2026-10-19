"""Contract: the browser's `arrival` event is gated, label-exact against the vocabulary, and actually mounted.

R-15's funnel has four links a server observes itself and one it cannot: a page view. It travels over the
network from a page a stranger is reading, which makes it the only event whose plumbing has to be pinned from
both ends. Three properties, each checked in both directions, for the same reason
`test_web_fetch_outcome_vocabulary.py` pins the failure vocabulary -- the owner is one file, the counterpart is
another corpus, and nothing else connects them.

1. **Nothing leaves the browser unless this build was made to count.** `COUNTING` is one expression,
   `process.env.NEXT_PUBLIC_TELEMETRY === "on"`, and `recordArrival` returns before the single `fetch` when it
   is false. A later "send it anyway, the server gates it" edit is exactly the change this refuses: the
   default deployment must make zero requests, not zero *records*.
2. **The labels are the vocabulary's, exactly.** `ARRIVAL_LABELS`' values and `product_events.json`'s declared
   choices for `arrival.payload.page` are one set. A label the client invented would be refused at the
   endpoint (the emitter enforces declared choices), and a declared choice with no route is a funnel number
   that will read zero forever. The keys are checked against real page files too, so a label cannot point at a
   route that 404s.
3. **The beacon is mounted, and posts only what the browser owns.** An endpoint nobody calls is §182's silent
   no-op in a new costume, so `layout.tsx` must render `ArrivalBeacon`; and every event name the module may
   send has to be one the vocabulary says the web emits -- the client cannot reach `run_completed`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLIENT = ROOT / "apps/web/app/lib/productEvents.ts"
BEACON = ROOT / "apps/web/app/components/layout/ArrivalBeacon.tsx"
LAYOUT = ROOT / "apps/web/app/layout.tsx"
EVENTS_FILE = ROOT / "apps/api/src/dsa_api/services/product_events.json"


def _client_source() -> str:
    return CLIENT.read_text(encoding="utf-8")


def _arrival_declaration() -> str:
    """The `ARRIVAL_LABELS` literal, so a rename elsewhere in the file cannot satisfy the guard."""
    match = re.search(r"const ARRIVAL_LABELS[^=]*=\s*\{(.*?)\n\};", _client_source(), re.S)
    assert match, "ARRIVAL_LABELS is gone or no longer a literal map, so this guard checks nothing"
    return match.group(1)


def _vocabulary() -> dict:
    return json.loads(EVENTS_FILE.read_text(encoding="utf-8"))


def _arrival_declared_choices() -> set[str]:
    for event in _vocabulary()["events"]:
        if event["name"] == "arrival":
            described = event["payload"]["page"]
            assert "|" in described, (
                "arrival.payload.page no longer declares a choice list, so the client has nothing to agree with"
            )
            return {token.strip() for token in described.split("|")}
    raise AssertionError("product_events.json no longer declares arrival")


def test_counting_is_one_build_time_expression_and_gates_the_only_request() -> None:
    source = _client_source()
    assert re.search(r'const COUNTING = process\.env\.NEXT_PUBLIC_TELEMETRY === "on";', source), (
        "the client's consent is no longer the single build-time expression this guard pins"
    )
    calls = [m.start() for m in re.finditer(r"\bfetch\(", source)]
    assert len(calls) == 1, (
        f"the emitter has {len(calls)} request sites; one gated site is the contract"
    )
    gate = source.find("if (!COUNTING) return;")
    assert gate != -1 and gate < calls[0], (
        "the request is no longer behind the consent check: a default build must send nothing at all"
    )


def test_the_client_posts_only_events_the_vocabulary_gives_to_the_browser() -> None:
    web_owned = {event["name"] for event in _vocabulary()["events"] if event["emitter"] == "web"}
    sent = set(re.findall(r'event:\s*"([a-z_]+)"', _client_source()))
    assert sent, "the client module names no event, so it cannot report anything"
    assert sent <= web_owned, (
        f"the client would post server-owned events: {sorted(sent - web_owned)}"
    )


def test_the_labels_are_exactly_the_declared_choices_and_both_directions_agree() -> None:
    block = _arrival_declaration()
    labels = {match.group(1) for match in re.finditer(r':\s*"([a-z_]+)"', block)}
    declared = _arrival_declared_choices()
    assert labels == declared, (
        f"the client reports {sorted(labels)} while the vocabulary declares {sorted(declared)}; "
        "an invented label is refused at the endpoint and an undeclared one is a number that never arrives"
    )


def test_every_label_keys_a_route_that_actually_exists() -> None:
    block = _arrival_declaration()
    routes = {match.group(1) for match in re.finditer(r'"(/[^"]*)":', block)}
    assert routes, "ARRIVAL_LABELS maps nothing, so arrival would report zero for every page"
    for route in sorted(routes):
        # "/" is app/page.tsx; "/datasets" is app/datasets/page.tsx -- the App Router's own mapping.
        page = ROOT / "apps/web/app" / route.strip("/") / "page.tsx"
        assert page.is_file(), f"{route} is labelled but {page} does not exist"


def test_the_beacon_is_mounted_and_renders_nothing() -> None:
    layout = LAYOUT.read_text(encoding="utf-8")
    assert "<ArrivalBeacon" in layout, (
        "the relay has no caller: the endpoint exists, the page never uses it, and the funnel reads zero"
    )
    assert "@/app/components/layout/ArrivalBeacon" in layout, (
        "the beacon is used without being imported"
    )
    beacon = BEACON.read_text(encoding="utf-8")
    assert "use client" in beacon.splitlines()[0], (
        "the beacon must be a client component to see a pathname"
    )
    assert "usePathname" in beacon and re.search(r"recordArrival\(pathname\)", beacon), (
        "the beacon no longer reports the pathname it is watching"
    )
    assert re.search(r"\},\s*\[pathname\]\);", beacon), (
        "the effect must re-run on navigation, not mount once"
    )
    assert "return null" in beacon, (
        "the beacon renders into the document, so it can move what the accessibility and tour checks read"
    )


def test_the_endpoint_the_client_calls_is_the_one_the_api_ships() -> None:
    """The URL is the join between the two corpora; a rename on either side has to redden something."""
    assert "/api/v1/events" in _client_source(), "the client no longer posts to the relay's path"
    router = ROOT / "apps/api/src/dsa_api/routers/events.py"
    assert router.is_file() and 'prefix="/api/v1/events"' in router.read_text(encoding="utf-8"), (
        "the relay route moved or vanished while the browser still posts to it"
    )
