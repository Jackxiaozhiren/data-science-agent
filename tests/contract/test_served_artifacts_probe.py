"""The served-artifact probe has to be able to fail, and its record has to describe a real reading.

Two separate things are checked here, because a probe that only ever runs green is the failure mode
`scripts/run_web_live_gates.sh` was written to avoid:

* **The decision logic, with fixtures.** ``version_contract_errors`` and ``overall_verdict`` are pure, so
  each wrong shape the API could publish, and each verdict combination, is exercised without a network.
  Without this the guard could pass because the probe never reaches the network at all.
* **The committed record** (``docs/audit/served-artifacts.json``). It must stay shape-valid: a verdict
  from the declared set, an ISO timestamp, the four named checks, and a non-empty ``basis``. There is
  deliberately no freshness assertion -- a clock-based expiry would turn a recorded observation into a
  time bomb that reddens a future PR for a reason unrelated to that PR.

``unmeasured`` is the value this file exists to protect. An unreachable host is not a pass: on a free
instance that slept through the budget, the honest answer is that the question stayed open.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from scripts import probe_served_artifacts as probe

ROOT = Path(__file__).resolve().parents[2]
RECORD = ROOT / "docs" / "audit" / "served-artifacts.json"

#: The payload `/version` returns today, copied from the live reading rather than invented.
GOOD_PAYLOAD = {
    "version": "4.6.0",
    "distribution": "jack-data-science-agent",
    "reasoning_mode": {
        "mode": "heuristic",
        "stub": True,
        "provider": "stub",
        "model": None,
        "error": None,
        "source": "environment",
    },
    "storage": {"durable": False, "ephemeral_roots": ["artifacts", "database", "datasets"]},
}


def test_chunk_paths_keeps_both_next_static_layouts_and_drops_duplicates() -> None:
    html = (
        '<script src="/_next/static/chunks/main-app-abc.js"></script>'
        '<script src="/_next/static/immutable/chunks/1def.js"></script>'
        '<link href="/_next/static/chunks/main-app-abc.js">'
        '<script src="/_next/static/css/app.css"></script>'
    )
    assert probe.chunk_paths(html) == [
        "/_next/static/chunks/main-app-abc.js",
        "/_next/static/immutable/chunks/1def.js",
    ], (
        "Turbopack emits under immutable/chunks; a chunks-only pattern would report zero and look broken"
    )


def test_version_contract_accepts_the_shape_the_api_publishes() -> None:
    assert probe.version_contract_errors(GOOD_PAYLOAD) == []


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (lambda p: p.pop("distribution"), "distribution"),
        (lambda p: p.__setitem__("version", ""), "version"),
        (lambda p: p.__setitem__("reasoning_mode", "heuristic"), "reasoning_mode is not an object"),
        (lambda p: p["reasoning_mode"].pop("stub"), "reasoning_mode.stub"),
        (lambda p: p["reasoning_mode"].__setitem__("source", None), "reasoning_mode.source"),
        (lambda p: p["storage"].__setitem__("durable", "no"), "storage.durable"),
        (lambda p: p["storage"].__setitem__("ephemeral_roots", "artifacts"), "ephemeral_roots"),
    ],
)
def test_version_contract_rejects_each_field_the_front_end_reads(mutate, expected: str) -> None:
    payload = json.loads(json.dumps(GOOD_PAYLOAD))
    mutate(payload)
    errors = probe.version_contract_errors(payload)
    assert any(expected in error for error in errors), errors


def _check(name: str, status: str, required: bool = True) -> probe.Check:
    return probe.Check(name=name, status=status, detail="", required=required)


def test_mismatch_outranks_unmeasured_and_unmeasured_never_reads_as_ok() -> None:
    assert (
        probe.overall_verdict([_check("a", probe.VERDICT_UNMEASURED)]) == probe.VERDICT_UNMEASURED
    )
    assert (
        probe.overall_verdict(
            [_check("a", probe.VERDICT_UNMEASURED), _check("b", probe.VERDICT_MISMATCH)]
        )
        == probe.VERDICT_MISMATCH
    )
    assert probe.overall_verdict([_check("a", probe.VERDICT_OK)]) == probe.VERDICT_OK


def test_an_advisory_check_that_could_not_be_read_does_not_demote_a_required_pass() -> None:
    """Bounded chunk sampling proves presence, never absence -- so the origin check is advisory."""
    checks = [
        _check("api_version_contract", probe.VERDICT_OK),
        _check("web_bundle_targets_documented_api", probe.VERDICT_UNMEASURED, required=False),
    ]
    assert probe.overall_verdict(checks) == probe.VERDICT_OK


def test_an_empty_shell_is_a_mismatch_rather_than_a_quiet_pass() -> None:
    """A page that returns 200 and names no JavaScript is a blank page, not a measured success."""
    checks = [_check("web_shell_names_chunks", probe.VERDICT_MISMATCH)]
    assert probe.overall_verdict(checks) == probe.VERDICT_MISMATCH


def test_a_chunk_the_host_refuses_is_a_mismatch() -> None:
    status, detail = probe.chunk_verdict(["/a.js"], ["/a.js -> HTTP 404"], [])
    assert status == probe.VERDICT_MISMATCH
    assert "404" in detail


def test_a_chunk_no_answer_arrived_for_is_unmeasured_not_a_mismatch() -> None:
    """Observed 2026-11-09: one chunk raised SSLEOFError against a healthy bundle.

    A dropped connection says nothing about whether the build is complete, so it must not be recorded
    as one. The first draft of this probe did exactly that and reported a false mismatch.
    """
    status, detail = probe.chunk_verdict(["/a.js"], [], ["/a.js -> SSLEOFError: unexpected EOF"])
    assert status == probe.VERDICT_UNMEASURED, detail
    assert "could not be read" in detail


def test_a_refusal_outranks_an_unread_chunk() -> None:
    """When both kinds are present the definitive answer wins; the build really is missing an asset."""
    status, _ = probe.chunk_verdict(["/a.js", "/b.js"], ["/a.js -> HTTP 404"], ["/b.js -> timeout"])
    assert status == probe.VERDICT_MISMATCH


def test_the_recorded_reading_is_shape_valid_and_names_its_basis() -> None:
    assert RECORD.is_file(), (
        f"{RECORD.relative_to(ROOT)} is missing; the ADR's S1 exit condition needs one recorded reading, "
        "so run `python scripts/probe_served_artifacts.py --write` rather than deleting this assertion"
    )
    report = json.loads(RECORD.read_text(encoding="utf-8"))

    assert report["verdict"] in probe.VERDICTS, report["verdict"]
    assert datetime.fromisoformat(report["recorded_at"].replace("Z", "+00:00")).tzinfo is not None
    assert report["basis"].strip(), "a reading without a stated basis is not a measurement"

    names = [c["name"] for c in report["checks"]]
    assert names == [
        "api_version_contract",
        "web_shell_names_chunks",
        "web_chunks_answer",
        "web_bundle_targets_documented_api",
    ], names
    for check in report["checks"]:
        assert check["status"] in probe.VERDICTS
        assert check["detail"].strip(), f"{check['name']} recorded no detail"

    # The four checks are independent readings of one deployment; a record holding none of them measured
    # would satisfy the shape assertions above while saying nothing.
    assert any(c["status"] != probe.VERDICT_UNMEASURED for c in report["checks"]), (
        "every check was unmeasured -- the record documents a failed connection, not a deployment"
    )
