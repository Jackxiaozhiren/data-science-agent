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
  names was actually uploaded rather than half-pruned.
* ``web_bundle_targets_documented_api`` (advisory) -- a sampled chunk contains the canonical API host,
  which is what proves the bundle was built with ``NEXT_PUBLIC_API_URL`` set. Sampling is bounded, so a
  host that is not seen is reported as unproven, never as absent.

Exit codes are the product: ``0`` pass, ``1`` mismatch, ``2`` unmeasured. An unreachable host is never a
pass -- a sleeping free instance leaves the question open, and calling that green is how a gate stops
meaning anything (the failure mode ``scripts/run_web_live_gates.sh`` was written to avoid).

No write outside ``docs/audit/``. Network access is the point of this script, unlike ``audit_facts.py``
which is deliberately offline; both are stdlib-only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
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

#: Next serves build output from `/_next/static/**`; the Turbopack bundles live under `immutable/chunks`.
_CHUNK_REF = re.compile(r"""(?:src|href)=["'](/_next/static/[^"'?>]+\.js)["']""")
_MAX_BODY = 2_000_000
_MAX_CHUNKS = 12


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
    """Mismatch beats unmeasured beats pass, and only required checks can demote the result."""
    if any(c.status == VERDICT_MISMATCH for c in checks):
        return VERDICT_MISMATCH
    if any(c.required and c.status == VERDICT_UNMEASURED for c in checks):
        return VERDICT_UNMEASURED
    return VERDICT_OK


def _fetch(url: str, timeout: float) -> tuple[int, str, bytes]:
    # Checked rather than assumed: both defaults are https literals, but `--web` and `--api` are operator
    # input, and a `file:` URL would turn this probe into a local read that reports as a deployment fact.
    if urllib.parse.urlsplit(url).scheme not in ("http", "https"):
        raise ValueError(f"refusing a non-http(s) URL: {url!r}")
    request = urllib.request.Request(  # noqa: S310 - scheme restricted immediately above
        url, headers={"User-Agent": "dsa-served-artifact-probe"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - scheme restricted above
        return response.status, response.headers.get("content-type", ""), response.read(_MAX_BODY)


def probe(web: str, api: str, api_host: str, timeout: float) -> dict[str, Any]:
    checks: list[Check] = []
    observed: dict[str, Any] = {}

    try:
        status, _ctype, body = _fetch(f"{api.rstrip('/')}/version", timeout)
        payload = json.loads(body)
        observed["version_payload"] = payload
        errors = version_contract_errors(payload)
        checks.append(
            Check(
                "api_version_contract",
                VERDICT_OK if status == 200 and not errors else VERDICT_MISMATCH,
                f"HTTP {status}" + ("" if not errors else "; " + "; ".join(errors)),
            )
        )
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        checks.append(
            Check("api_version_contract", VERDICT_UNMEASURED, f"unreachable or unparseable: {exc}")
        )

    html: str | None = None
    try:
        status, ctype, body = _fetch(web, timeout)
        html = body.decode("utf-8", errors="replace")
        observed["web_status"] = status
        observed["web_content_type"] = ctype
        names = chunk_paths(html)
        observed["chunk_count"] = len(names)
        checks.append(
            Check(
                "web_shell_names_chunks",
                VERDICT_OK if status == 200 and names else VERDICT_MISMATCH,
                f"HTTP {status}, {len(names)} distinct chunk path(s) named",
            )
        )
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        checks.append(Check("web_shell_names_chunks", VERDICT_UNMEASURED, f"unreachable: {exc}"))

    if html is not None:
        names = chunk_paths(html)[:_MAX_CHUNKS]
        bad: list[str] = []
        host_seen = False
        for path in names:
            try:
                status, ctype, body = _fetch(f"{web.rstrip('/')}{path}", timeout)
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                bad.append(f"{path} -> {exc}")
                continue
            if status != 200:
                bad.append(f"{path} -> HTTP {status}")
            elif "javascript" not in ctype.lower():
                bad.append(f"{path} -> content-type {ctype!r}")
            elif api_host in body.decode("utf-8", errors="replace"):
                host_seen = True
        checks.append(
            Check(
                "web_chunks_answer",
                VERDICT_OK if names and not bad else VERDICT_MISMATCH,
                f"{len(names)} sampled, {len(bad)} did not answer as JavaScript"
                + ("" if not bad else ": " + "; ".join(bad[:3])),
            )
        )
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

    verdict = overall_verdict(checks)
    return {
        "recorded_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "verdict": verdict,
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
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
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
        RECORD.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"{report['verdict'].upper()} {report['recorded_at']} web={args.web} api={args.api}")
        for check in report["checks"]:
            print(f"  [{check['status']:10}] {check['name']}: {check['detail']}")

    return {VERDICT_OK: 0, VERDICT_MISMATCH: 1, VERDICT_UNMEASURED: 2}[report["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
