"""Read the deployed artifacts and report whether they answer with the contract this tree publishes.

Why a probe rather than the version string: ``/version`` returns ``settings.version``, a value typed by
hand and never derived from the commit that is running. On 2026-11-07 the endpoint reported ``4.6.0``
while the served front-end still carried the previous build's copy. A number that cannot disagree with a
deploy is not evidence about the deploy, so this instrument reads what is actually served.

What it reads, in four separate verdicts rather than one:

* ``api_version_contract`` -- the ``/version`` payload still has the shape
  ``apps/api/src/dsa_api/routers/health.py`` publishes: ``version``, ``distribution``,
  ``reasoning_mode{mode,stub,provider,model,error,source}``, ``storage{durable,ephemeral_roots}``.
  A deployed API that dropped a key breaks the front-end's disclosure without failing any request.
* ``web_shell_names_chunks`` -- the page HTML still names built JavaScript. A shell that references
  nothing is a blank page that returns 200.
* ``web_chunks_answer`` -- every sampled chunk returns 200 with JavaScript, so the build that the shell
  names was actually uploaded rather than half-pruned. A chunk the host refuses is a mismatch; a chunk
  no answer arrived for is unmeasured, because a TLS reset is a fact about the read, not the build.
* ``web_bundle_targets_documented_api`` (advisory) -- a sampled chunk contains the canonical API host,
  which is what proves the bundle was built with ``NEXT_PUBLIC_API_URL`` set. Sampling is bounded, so a
  host that is not seen is reported as unproven, never as absent.

Exit codes are the product: ``0`` ok, ``1`` mismatch, ``2`` unmeasured. An unreachable host is never a
pass -- a sleeping free instance leaves the question open, and calling that green is how a gate stops
meaning anything (the failure mode ``scripts/run_web_live_gates.sh`` was written to avoid).

Two constraints this file inherits from ``scripts/audit_facts.py``: stdlib only, and no write outside
``docs/audit/``. It is deliberately *not* offline -- reading the deployment is the whole point -- and it
keeps its exception handling in one place (``_guarded``) so the repository's handler ceiling moves by one
rather than by one per read.
"""

from __future__ import annotations

import argparse
import http.client
import json
import re
import sys
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "docs" / "audit" / "served-artifacts.json"

DEFAULT_WEB = "https://data-science-agent-web.vercel.app"
DEFAULT_API = "https://data-science-agent-api-h43i.onrender.com"
#: Host the deployed bundle must have been built against; `apps/web/lib/api.ts` bakes it in at build time.
DEFAULT_API_HOST = "data-science-agent-api-h43i.onrender.com"

VERDICT_OK = "ok"
VERDICT_MISMATCH = "mismatch"
VERDICT_UNMEASURED = "unmeasured"
VERDICTS = (VERDICT_OK, VERDICT_MISMATCH, VERDICT_UNMEASURED)

USER_AGENT = "dsa-served-artifact-probe"
#: Next serves build output from `/_next/static/**`; the Turbopack bundles live under `immutable/chunks`.
_CHUNK_REF = re.compile(r"""(?:src|href)=["'](/_next/static/[^"'?>]+\.js)["']""")
_MAX_BODY = 2_000_000
_MAX_CHUNKS = 12


@dataclass(frozen=True)
class Reading:
    status: int
    content_type: str
    body: bytes


@dataclass
class Check:
    name: str
    status: str
    detail: str
    required: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
            "required": self.required,
        }


def _guarded[T](call: Callable[[], T]) -> tuple[T | None, str]:
    """Run one step, turning a network or parse failure into a reason instead of a traceback.

    The single exception boundary in this file, and deliberately narrow: a programming error (say a
    ``TypeError``) is not caught and must not be reported as an unreachable host.
    """
    try:
        return call(), ""
    except (OSError, http.client.HTTPException, ValueError) as exc:
        return None, f"{type(exc).__name__}: {exc}"


def _read(url: str, timeout: float) -> Reading:
    """One GET over ``http.client``; raises into ``_guarded`` rather than handling anything itself."""
    # Checked rather than assumed: both defaults are https literals, but `--web` and `--api` are operator
    # input, and a `file:` URL would turn this probe into a local read that reports as a deployment fact.
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise ValueError(f"refusing a non-http(s) URL: {url!r}")
    target = parts.path or "/"
    if parts.query:
        target = f"{target}?{parts.query}"
    connection_class = (
        http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
    )
    connection = connection_class(parts.hostname, parts.port, timeout=timeout)
    try:
        connection.request("GET", target, headers={"User-Agent": USER_AGENT})
        response = connection.getresponse()
        return Reading(
            status=response.status,
            content_type=response.getheader("content-type", "") or "",
            body=response.read(_MAX_BODY),
        )
    finally:
        connection.close()


def _read_chunk(url: str, timeout: float) -> tuple[Reading | None, str]:
    """Read one chunk, retrying a transport failure once.

    A CDN edge drops connections occasionally; the retry is here because a single TLS EOF was observed
    on 2026-11-09 against a healthy bundle. The retry never applies to an HTTP answer -- a 404 is a
    fact about the build and must not be retried into a different-looking result.
    """
    reading, error = _guarded(lambda: _read(url, timeout))
    if reading is None:
        reading, error = _guarded(lambda: _read(url, timeout))
    return reading, error


def chunk_verdict(names: list[str], bad: list[str], unread: list[str]) -> tuple[str, str]:
    """The chunk check's whole decision, so it can be exercised with fixtures instead of a CDN.

    ``bad`` holds chunks the host answered for and refused; ``unread`` holds chunks no answer arrived
    for. Only the first is evidence about the build -- conflating them is how a transient TLS reset gets
    recorded as a half-pruned deployment, which happened on 2026-11-09.
    """
    if not names:
        return VERDICT_MISMATCH, "the shell named no chunk to read"
    if bad:
        return (
            VERDICT_MISMATCH,
            f"{len(names)} sampled, {len(bad)} did not answer as JavaScript: " + "; ".join(bad[:3]),
        )
    if unread:
        return (
            VERDICT_UNMEASURED,
            f"{len(names)} sampled, {len(unread)} could not be read: " + "; ".join(unread[:3]),
        )
    return VERDICT_OK, f"{len(names)} sampled, all answered as JavaScript"


def chunk_paths(html: str) -> list[str]:
    """Every distinct JavaScript path the shell names, in document order."""
    seen: list[str] = []
    for match in _CHUNK_REF.finditer(html):
        path = match.group(1)
        if path not in seen:
            seen.append(path)
    return seen


def version_contract_errors(payload: Any) -> list[str]:
    """Reasons the `/version` payload no longer matches what the API publishes.

    Kept as a pure function so the decision can be exercised with fixtures instead of the network.
    """
    if not isinstance(payload, dict):
        return ["payload is not an object"]
    errors: list[str] = []
    for key in ("version", "distribution"):
        if not isinstance(payload.get(key), str) or not payload.get(key):
            errors.append(f"{key} is not a non-empty string")
    mode = payload.get("reasoning_mode")
    if not isinstance(mode, dict):
        errors.append("reasoning_mode is not an object")
    else:
        for key in ("mode", "provider", "source"):
            if not isinstance(mode.get(key), str) or not mode.get(key):
                errors.append(f"reasoning_mode.{key} is not a non-empty string")
        if not isinstance(mode.get("stub"), bool):
            errors.append("reasoning_mode.stub is not a boolean")
        if "model" not in mode or "error" not in mode:
            errors.append("reasoning_mode.model/error are not both present")
    storage = payload.get("storage")
    if not isinstance(storage, dict):
        errors.append("storage is not an object")
    else:
        if not isinstance(storage.get("durable"), bool):
            errors.append("storage.durable is not a boolean")
        roots = storage.get("ephemeral_roots")
        if not isinstance(roots, list) or any(not isinstance(r, str) for r in roots):
            errors.append("storage.ephemeral_roots is not a list of strings")
    return errors


def overall_verdict(checks: list[Check]) -> str:
    """Mismatch beats unmeasured beats ok, and only required checks can demote the result."""
    if any(c.status == VERDICT_MISMATCH for c in checks):
        return VERDICT_MISMATCH
    if any(c.required and c.status == VERDICT_UNMEASURED for c in checks):
        return VERDICT_UNMEASURED
    return VERDICT_OK


def probe(web: str, api: str, api_host: str, timeout: float) -> dict[str, Any]:
    """Read all four things and return the report; never raises for a deployment that is simply down."""
    checks: list[Check] = []
    observed: dict[str, Any] = {}

    reading, error = _guarded(lambda: _read(f"{api.rstrip('/')}/version", timeout))
    payload: Any = None
    parse_error = ""
    if reading is not None:
        payload, parse_error = _guarded(lambda: json.loads(reading.body))
    if reading is None or parse_error:
        checks.append(
            Check(
                "api_version_contract",
                VERDICT_UNMEASURED,
                f"unreachable or unparseable: {error or parse_error}",
            )
        )
    else:
        observed["version_payload"] = payload
        errors = version_contract_errors(payload)
        checks.append(
            Check(
                "api_version_contract",
                VERDICT_OK if reading.status == 200 and not errors else VERDICT_MISMATCH,
                f"HTTP {reading.status}" + ("" if not errors else "; " + "; ".join(errors)),
            )
        )

    html: str | None = None
    shell, shell_error = _guarded(lambda: _read(web, timeout))
    if shell is None:
        checks.append(
            Check("web_shell_names_chunks", VERDICT_UNMEASURED, f"unreachable: {shell_error}")
        )
    else:
        html = shell.body.decode("utf-8", errors="replace")
        observed["web_status"] = shell.status
        observed["web_content_type"] = shell.content_type
        names = chunk_paths(html)
        observed["chunk_count"] = len(names)
        checks.append(
            Check(
                "web_shell_names_chunks",
                VERDICT_OK if shell.status == 200 and names else VERDICT_MISMATCH,
                f"HTTP {shell.status}, {len(names)} distinct chunk path(s) named",
            )
        )

    if html is not None:
        names = chunk_paths(html)[:_MAX_CHUNKS]
        bad: list[str] = []
        unread: list[str] = []
        host_seen = False
        for path in names:
            chunk, chunk_error = _read_chunk(f"{web.rstrip('/')}{path}", timeout)
            if chunk is None:
                unread.append(f"{path} -> {chunk_error}")
            elif chunk.status != 200:
                bad.append(f"{path} -> HTTP {chunk.status}")
            elif "javascript" not in chunk.content_type.lower():
                bad.append(f"{path} -> content-type {chunk.content_type!r}")
            elif api_host in chunk.body.decode("utf-8", errors="replace"):
                host_seen = True
        # An HTTP answer that says "no" is a fact about the build; a connection that never delivered one
        # is a fact about this run. `chunk_verdict` keeps the two apart.
        chunk_status, chunk_detail = chunk_verdict(names, bad, unread)
        checks.append(Check("web_chunks_answer", chunk_status, chunk_detail))
        checks.append(
            Check(
                "web_bundle_targets_documented_api",
                VERDICT_OK if host_seen else VERDICT_UNMEASURED,
                f"{api_host!r} seen in a sampled chunk"
                if host_seen
                else f"{api_host!r} not seen in {len(names)} sampled chunk(s); bounded sampling, "
                "so this is not evidence of absence",
                required=False,
            )
        )

    return {
        "recorded_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "verdict": overall_verdict(checks),
        "targets": {"web": web, "api": api, "expected_api_host": api_host},
        "checks": [c.as_dict() for c in checks],
        "observed": observed,
        "basis": (
            "Served artifacts only: the `/version` payload and the JavaScript the page names. "
            "No local build, no repository source and no version string is treated as evidence about "
            "what is deployed. Bounded sampling: chunks are read up to a fixed limit, so a negative "
            "result is reported as unproven rather than absent."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=("Read the deployed artifacts and report the verdict.")
    )
    parser.add_argument("--web", default=DEFAULT_WEB, help="web origin to read")
    parser.add_argument("--api", default=DEFAULT_API, help="api origin to read")
    parser.add_argument(
        "--expect-api-host", default=DEFAULT_API_HOST, help="host the bundle must target"
    )
    parser.add_argument(
        "--timeout", type=float, default=90.0, help="per-request timeout in seconds"
    )
    parser.add_argument(
        "--write", action="store_true", help=f"record the report at {RECORD.relative_to(ROOT)}"
    )
    parser.add_argument(
        "--json", action="store_true", help="print the report instead of one summary line"
    )
    args = parser.parse_args(argv)

    report = probe(args.web, args.api, args.expect_api_host, args.timeout)

    if args.write:
        RECORD.parent.mkdir(parents=True, exist_ok=True)
        RECORD.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"{report['verdict'].upper()} {report['recorded_at']} web={args.web} api={args.api}")
        for check in report["checks"]:
            print(f"  [{check['status']:10}] {check['name']}: {check['detail']}")

    return {VERDICT_OK: 0, VERDICT_MISMATCH: 1, VERDICT_UNMEASURED: 2}[report["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
