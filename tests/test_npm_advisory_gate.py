"""§91: the npm advisory gate must be able to tell "no fix exists" from "we stopped looking".

`main` went red at CI step 14 on an advisory whose `first_patched` is null (§89), which left
only two answers available to the previous gate: leave main red forever, or mute it. This
module tests the third answer, and every test below asserts a *failure* mode, because a
security exemption mechanism that cannot fail is the same as muting the gate.

`tests/fixtures/npm_audit_web_2026-10-03.json` is a verbatim `npm --prefix apps/web audit
--json` capture (5 high, all reachable from one `braces` advisory), so the shape under test is
npm's, not a guess at npm's.
"""

from __future__ import annotations

import copy
import importlib.util
import json
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/check_npm_advisories.py"
REAL_LIST = REPO / "docs/audit/npm-advisory-exceptions.json"
CAPTURE = REPO / "tests/fixtures/npm_audit_web_2026-10-03.json"

#: The date the capture was taken, so no test depends on the day it runs.
TODAY = date(2026, 10, 3)

_spec = importlib.util.spec_from_file_location("check_npm_advisories", SCRIPT)
assert _spec and _spec.loader
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)


def _audit_doc() -> dict:
    return json.loads(CAPTURE.read_text(encoding="utf-8"))


def _write_audit(tmp_path: Path, doc: dict | None = None, *, raw: str | None = None) -> Path:
    path = tmp_path / "audit.json"
    path.write_text(raw if raw is not None else json.dumps(doc), encoding="utf-8")
    return path


def _write_list(tmp_path: Path, advisories: list[dict]) -> Path:
    path = tmp_path / "exceptions.json"
    path.write_text(json.dumps({"advisories": advisories}), encoding="utf-8")
    return path


def _entry(ghsa: str = "GHSA-vfj7-8cjw-p6xm", package: str = "braces", **over: object) -> dict:
    base: dict = {
        "id": ghsa,
        "package": package,
        "severity": "high",
        "advisory_url": f"https://github.com/advisories/{ghsa}",
        "affected_range": "<= 3.0.3",
        "why_unactionable": "no release sits outside the affected range",
        "exposure": "dev-dependency chain only",
        "advised": "2026-09-18",
        "review_by": "2026-11-07",
    }
    base.update(over)
    return base


def _run(audit: Path, exceptions: Path) -> int:
    return gate.main([str(audit), "--exceptions", str(exceptions)], today=TODAY)


def test_the_real_capture_is_clean_only_because_the_list_is_carrying_it(capsys) -> None:
    """Green-on-arrival by construction: this is the state §91 was written to produce.

    It is falsified by ``test_emptying_the_list_turns_the_gate_red``, which flips only the
    list and must go red on the same audit document.
    """
    assert _run(CAPTURE, REAL_LIST) == gate.EXIT_CLEAN
    out = capsys.readouterr().out
    assert "EXEMPT GHSA-vfj7-8cjw-p6xm" in out
    assert "tolerated until 2026-11-07" in out


def test_emptying_the_list_turns_the_gate_red(tmp_path: Path, capsys) -> None:
    audit = _write_audit(tmp_path, _audit_doc())
    assert _run(audit, _write_list(tmp_path, [])) == gate.EXIT_VIOLATION
    assert "GHSA-vfj7-8cjw-p6xm" in capsys.readouterr().out


def test_every_vulnerable_node_is_named_not_just_the_one_with_the_advisory(
    tmp_path: Path, capsys
) -> None:
    """npm reports five nodes for one advisory; the gate must account for all five.

    A reader that only matched the node carrying the GHSA url would wave the chain through
    while reporting one line, which is how a partial exemption reads as a complete one.
    """
    assert _run(CAPTURE, _write_list(tmp_path, [_entry()])) == gate.EXIT_CLEAN
    out = capsys.readouterr().out
    for node in ("braces", "chokidar", "fast-glob", "micromatch", "tailwindcss"):
        assert f"reached from {node}" in out, out


def test_an_expired_exemption_fails(tmp_path: Path, capsys) -> None:
    audit = _write_audit(tmp_path, _audit_doc())
    expired = _write_list(tmp_path, [_entry(review_by="2026-01-01")])
    assert _run(audit, expired) == gate.EXIT_VIOLATION
    assert "expired 2026-01-01" in capsys.readouterr().out


def test_an_exemption_for_an_advisory_no_longer_reported_fails(tmp_path: Path, capsys) -> None:
    """The list must decay with the tree, or it stops meaning anything."""
    clean = _audit_doc()
    clean["vulnerabilities"] = {}
    clean["metadata"]["vulnerabilities"]["total"] = 0
    audit = _write_audit(tmp_path, clean)
    assert _run(audit, _write_list(tmp_path, [_entry()])) == gate.EXIT_VIOLATION
    assert "no longer reports" in capsys.readouterr().out


def test_a_second_high_advisory_is_not_covered_by_the_first(tmp_path: Path) -> None:
    doc = _audit_doc()
    doc["vulnerabilities"]["lodash"] = {
        "name": "lodash",
        "severity": "high",
        "isDirect": True,
        "via": [
            {
                "source": 1,
                "name": "lodash",
                "dependency": "lodash",
                "title": "prototype pollution",
                "url": "https://github.com/advisories/GHSA-35jh-r7q6-w983",
                "severity": "high",
                "range": "<4.17.21",
            }
        ],
        "effects": [],
        "range": "<4.17.21",
        "nodes": ["node_modules/lodash"],
        "fixAvailable": True,
    }
    audit = _write_audit(tmp_path, doc)
    assert _run(audit, _write_list(tmp_path, [_entry()])) == gate.EXIT_VIOLATION


def test_an_advisory_with_no_resolvable_id_fails(tmp_path: Path) -> None:
    """An entry that cannot be named cannot be exempted."""
    doc = _audit_doc()
    doc["vulnerabilities"]["mystery"] = {
        "name": "mystery",
        "severity": "critical",
        "isDirect": False,
        "via": [{"source": 2, "name": "mystery", "url": "https://example.com/not-an-advisory"}],
        "effects": [],
        "range": "*",
        "nodes": ["node_modules/mystery"],
        "fixAvailable": False,
    }
    audit = _write_audit(tmp_path, doc)
    assert _run(audit, _write_list(tmp_path, [_entry()])) == gate.EXIT_VIOLATION


def test_a_low_severity_finding_does_not_reach_this_gate(tmp_path: Path) -> None:
    """`--audit-level=high` policed high and critical; that boundary is preserved."""
    doc = _audit_doc()
    doc["vulnerabilities"] = {
        "cookie": {
            "name": "cookie",
            "severity": "moderate",
            "isDirect": False,
            "via": [
                {
                    "source": 3,
                    "name": "cookie",
                    "url": "https://github.com/advisories/GHSA-aaaa-bbbb-cccc",
                    "severity": "moderate",
                }
            ],
            "effects": [],
            "range": "<1.0.0",
            "nodes": ["node_modules/cookie"],
            "fixAvailable": True,
        }
    }
    audit = _write_audit(tmp_path, doc)
    assert _run(audit, _write_list(tmp_path.parent, [])) == gate.EXIT_CLEAN


def test_an_empty_capture_is_an_input_error_never_a_pass(tmp_path: Path) -> None:
    """The failure mode `|| true` buys: a scan that produced nothing must not read green."""
    assert _run(_write_audit(tmp_path, raw=""), REAL_LIST) == gate.EXIT_INPUT_ERROR


def test_a_truncated_capture_is_an_input_error(tmp_path: Path) -> None:
    assert _run(_write_audit(tmp_path, raw='{"auditReportVersion": 2, "vuln'), REAL_LIST) == (
        gate.EXIT_INPUT_ERROR
    )


def test_a_foreign_report_version_is_an_input_error(tmp_path: Path) -> None:
    doc = _audit_doc()
    doc["auditReportVersion"] = 1
    audit = _write_audit(tmp_path, doc)
    assert _run(audit, REAL_LIST) == gate.EXIT_INPUT_ERROR


def test_a_missing_capture_is_an_input_error(tmp_path: Path) -> None:
    assert _run(tmp_path / "never-written.json", REAL_LIST) == gate.EXIT_INPUT_ERROR


def test_an_exemption_without_a_reason_or_a_date_is_refused(tmp_path: Path) -> None:
    audit = _write_audit(tmp_path, _audit_doc())
    stripped = _entry(review_by="2026-11-07")
    del stripped["why_unactionable"]
    assert _run(audit, _write_list(tmp_path, [stripped])) == gate.EXIT_INPUT_ERROR
    undated = copy.deepcopy(_entry())
    undated["review_by"] = "sometime next quarter"
    assert _run(audit, _write_list(tmp_path, [undated])) == gate.EXIT_INPUT_ERROR


def test_the_committed_list_is_bounded_and_carries_every_required_field() -> None:
    doc = json.loads(REAL_LIST.read_text(encoding="utf-8"))
    entries = doc["advisories"]
    assert entries, "the committed list went empty while the capture still reports 5 high"
    assert len(entries) <= 1, (
        f"{len(entries)} exemptions is above the ceiling this section opens with. Adding a "
        "second one is a human decision: name the advisory, the reason it is unactionable, "
        "and what re-review will do about it in AUDIT_LEDGER first."
    )
    for entry in entries:
        missing = [field for field in gate.REQUIRED_EXCEPTION_FIELDS if not entry.get(field)]
        assert not missing, f"{entry.get('id')} is missing {missing}"
        assert date.fromisoformat(entry["review_by"]) > date.fromisoformat(entry["advised"])


def test_the_committed_list_has_no_entry_this_capture_does_not_need() -> None:
    """A stale exemption is a lie about the tree; catch it in-repo, not in CI."""
    ids_in_capture = {
        via["url"].rsplit("/", 1)[1]
        for entry in _audit_doc()["vulnerabilities"].values()
        for via in entry["via"]
        if isinstance(via, dict) and "advisories/" in via.get("url", "")
    }
    committed = json.loads(REAL_LIST.read_text(encoding="utf-8"))["advisories"]
    listed = {entry["id"] for entry in committed}
    assert listed <= ids_in_capture, f"{sorted(listed - ids_in_capture)} is not in the capture"


def test_cyclic_via_references_terminate(tmp_path: Path, capsys) -> None:
    """npm's `via` graph is walked recursively; a cycle must terminate, not hang.

    A pair that points at each other resolves to no advisory at all, which the gate
    reports as a violation. Either outcome is acceptable; an unbounded walk is not.
    """
    doc = _audit_doc()
    doc["vulnerabilities"] = {
        "a": {
            "name": "a",
            "severity": "high",
            "isDirect": False,
            "via": ["b"],
            "effects": [],
            "range": "*",
            "nodes": ["node_modules/a"],
        },
        "b": {
            "name": "b",
            "severity": "high",
            "isDirect": False,
            "via": ["a"],
            "effects": [],
            "range": "*",
            "nodes": ["node_modules/b"],
        },
    }
    audit = _write_audit(tmp_path, doc)
    assert _run(audit, _write_list(tmp_path, [_entry()])) == gate.EXIT_VIOLATION
    assert "no advisory reachable" in capsys.readouterr().out
