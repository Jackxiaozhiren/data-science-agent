"""R-15: product events, consent-first, no PII -- the counterweight to shipping into silence (B14).

The funnel questions (arrival → starter question → run started → run completed → export taken) are answered
by events, and the vocabulary is **published as data**: ``product_events.json`` beside this module declares
every event, its payload fields, and what is prohibited. ``record_event`` refuses at emit time anything the
file does not declare, so a field that would carry dataset content or query text cannot be smuggled in by a
later edit -- the contract is enforced where the write happens, not checked afterwards by a test that reads
the log.

Consent is the whole switch: ``DSA_TELEMETRY=on`` appends to a JSONL log; any other value -- including the
default -- means **nothing happens**: no file is created, no line is written, and the caller cannot tell.
Local mode therefore ships silent, and the hosted demo only counts because its operator chose to set the
variable.

Shape errors raise. A payload key the vocabulary forbids is a code defect, and raising is what makes it a
defect rather than an empty log; the guard proves the raise. Disk failures are the *environment* and are
suppressed -- an unreachable log must not turn a finished analysis into a 500 -- and the suppression is the
only one in this module, because the ratchet counts every handler in shipped code.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

#: The vocabulary, read from beside this module: one copy in the source tree, mirrored byte-exact into the
#: vendored tree, so the API and the CLI cannot disagree about what an event is.
EVENTS_FILE = Path(__file__).with_name("product_events.json")

CONSENT_ENV = "DSA_TELEMETRY"
LOG_PATH_ENV = "DSA_EVENT_LOG"
DEFAULT_LOG_PATH = Path("data/events/events.jsonl")

_VALUE_PATTERN = re.compile(r"^[A-Za-z0-9._:/-]{0,64}$")
_ENUM_TOKEN = re.compile(r"^[A-Za-z0-9._:/-]+$")

_loaded: dict[str, Any] | None = None


def _spec() -> dict[str, Any]:
    """The vocabulary, cached because every request path may touch it."""
    global _loaded
    if _loaded is None:
        _loaded = json.loads(EVENTS_FILE.read_text(encoding="utf-8"))
    return _loaded


def consent_enabled() -> bool:
    """Whether this instance was *asked* to count. Default off: local mode ships silent."""
    return os.environ.get(CONSENT_ENV, "off").strip().lower() == "on"


def events_log_path() -> Path:
    return Path(os.environ.get(LOG_PATH_ENV) or DEFAULT_LOG_PATH)


def _declaration_refusal(
    name: str, expect_emitter: str
) -> tuple[dict[str, Any] | None, str | None]:
    """The vocabulary entry for ``name``, and the reason this call site may not use it.

    Ownership is checked before status: an event the browser emits cannot be recorded by server code at all,
    and answering "not active" would name the wrong defect. The funnel's claim is that each link is recorded
    where it is actually observed.

    Refusals come back as messages instead of being raised because the relay boundary has to answer 400 with
    the very words the in-process emitter would raise, and the shipped tree counts every exception handler --
    one predicate serves both doors, and the boundary needs no ``try``.
    """
    for event in _spec()["events"]:
        if event["name"] != name:
            continue
        if event["emitter"] != expect_emitter:
            return None, (
                f"event {name!r} is emitted by the {event['emitter']} client; "
                f"this call site records {expect_emitter}-emitted events only"
            )
        if event["status"] != "active":
            return None, (
                f"event {name!r} is declared but not active ({event['emitter']}-side only)"
            )
        return event, None
    return None, f"event {name!r} is not in the published vocabulary"


def _declared_value_refusal(name: str, key: str, value: str, described: str) -> str | None:
    """When the vocabulary declares a value as a list of choices, the list is enforced, not decorative.

    A field whose text reads "landing | datasets" states the only values that may reach the log, and that
    matters more once a browser can post a payload: a string that passes the identifier rule would still be
    an arbitrary value the vocabulary never promised. Descriptions without a pipe ("the effective reasoning
    mode at creation") stay prose and are not turned into an enum.
    """
    if "|" not in described:
        return None
    choices = [token.strip() for token in described.split("|")]
    if not choices or not all(_ENUM_TOKEN.match(token) for token in choices):
        return None
    if value in choices:
        return None
    return (
        f"event {name!r} payload key {key!r} has value {value!r}: {choices} are the choices the vocabulary "
        "declares, and a value it never named is not a value the log may hold"
    )


def _payload_refusal(name: str, payload: dict[str, Any], expect_emitter: str) -> str | None:
    """Why the vocabulary refuses this payload, or None when it is acceptable."""
    event, refusal = _declaration_refusal(name, expect_emitter)
    if refusal is not None or event is None:
        return refusal
    declared = event["payload"]
    prohibited = set(_spec()["prohibited_payload_keys"])
    # The prohibited check runs first: a key from those classes is the more specific refusal, and the one
    # whose message names what must never be logged.
    if prohibited & set(payload):
        return (
            f"event {name!r} payload carries prohibited keys {sorted(prohibited & set(payload))}: "
            "dataset content, query text and user-identifying values never enter the event log"
        )
    unknown = set(payload) - set(declared)
    if unknown:
        return f"event {name!r} got undeclared payload keys {sorted(unknown)}"
    missing = set(declared) - set(payload)
    if missing:
        return f"event {name!r} is missing its declared payload keys {sorted(missing)}"
    for key, value in payload.items():
        if value is None or isinstance(value, (bool, int)):
            continue
        if isinstance(value, str) and _VALUE_PATTERN.match(value):
            nested = _declared_value_refusal(name, key, value, declared[key])
            if nested is not None:
                return nested
            continue
        return (
            f"event {name!r} payload key {key!r} has value {value!r}: only null, booleans, integers and "
            f"short identifier-like strings matching {_VALUE_PATTERN.pattern} may be logged"
        )
    return None


def client_event_refusal(name: str, payload: dict[str, Any]) -> str | None:
    """What the vocabulary would refuse about a browser-posted event. The relay asks before it writes."""
    return _payload_refusal(name, payload, "web")


def _check_payload(name: str, payload: dict[str, Any], expect_emitter: str) -> None:
    problem = _payload_refusal(name, payload, expect_emitter)
    if problem is not None:
        raise ValueError(problem)


def _emit(name: str, payload: dict[str, Any]) -> None:
    if not consent_enabled():
        return
    record = {
        "event": name,
        "at": datetime.now(UTC).isoformat(timespec="seconds"),
        "payload": payload,
    }
    line = json.dumps(record, ensure_ascii=False, sort_keys=True)
    path = events_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with contextlib.suppress(OSError), path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def record_event(name: str, **payload: Any) -> None:
    """Validate always, append only when consented.

    The schema check sits *before* the consent gate on purpose: a payload that would carry query text is a
    code defect whether or not this instance counts, and if the check only ran behind the gate, the defect
    would be invisible exactly until someone enabled telemetry -- the silently-no-op shape §182 recorded in
    another form.

    This is the server's own door: it takes the events this process observes. A browser-observed event is
    refused here and goes through `record_client_event` instead.
    """
    _check_payload(name, payload, "api")
    _emit(name, payload)


def record_client_event(name: str, payload: dict[str, Any]) -> None:
    """The relay's door: a signal only the browser can know, validated by the same rules as a server one.

    Nothing loosens here. The vocabulary, the prohibited key classes and the value rule all still apply, and
    that is what makes it survivable for an unauthenticated client to hand over a record at all: the endpoint
    is a transport, not a second authority.
    """
    _check_payload(name, payload, "web")
    _emit(name, payload)


def read_events(path: Path | None = None) -> list[dict[str, Any]]:
    """The log, for reporting and for the guard that re-checks it from disk."""
    target = path or events_log_path()
    if not target.is_file():
        return []
    events: list[dict[str, Any]] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events
