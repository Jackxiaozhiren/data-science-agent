"""The S2 boundary matrix must be a reading of the tree, not a table of assertions.

A matrix of "fenced / open / undecidable" is only worth recording if the verdicts are tied to
something that runs. Three ties are checked here, and each one exists because its absence would let
the table drift into a policy statement:

* **The probes are re-run.** ``scripts/measure_execution_boundary.py`` produces the record from
  expressions this repository ships, so a rebuild has to reproduce it exactly -- including the
  observations that came back ``permitted``. A tree edit that changes a filter changes the record,
  and CI says so instead of leaving a stale verdict in place.
* **The verdict is recomputed here, from the layers.** The derivation is written out again rather
  than imported, so a change to the script's rule cannot silently redefine what "fenced" meant in
  the record.
* **Absence never scores as a decision.** A capability fenced only because no call site exists is
  ``undecidable`` at boundary level. If that distinction were dropped, the matrix would report a
  boundary where there is only today's code.

What this file deliberately does not check: whether a ``fenced`` cell would survive an adversary.
That is what the record's ``not_claimed`` field says in prose, and no test can turn a name filter
into a containment mechanism.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from scripts import measure_execution_boundary as boundary

ROOT = Path(__file__).resolve().parents[2]
RECORD_PATH = ROOT / "docs/audit/execution-boundary.json"
BASIS_PAGE = ROOT / "docs/measurement-basis.md"
RECORD = json.loads(RECORD_PATH.read_text(encoding="utf-8"))
#: Every test the record is allowed to cite. A record naming a path of its own choosing would turn
#: a citation into a file probe, so the set is closed here instead of resolved from the record.
CITED_TESTS = {"tests/security/test_sql_sandbox.py"}
CAPABILITIES = {
    "process_spawn",
    "network_egress",
    "filesystem_read",
    "filesystem_write",
    "credential_read",
}


def _derive_verdict(cell: dict) -> tuple[str, str]:
    """The rule the record states, restated so the record cannot redefine it quietly."""
    layers = cell["layers"]
    absence = any(layer["decided_by"] == "absence" for layer in layers)
    if layers[-1]["outcome"] == "open":
        return "open", "absence" if absence else "check"
    if absence:
        return "undecidable", "absence"
    return "fenced", "check"


def test_rebuild_reproduces_the_record() -> None:
    fresh = boundary.build()
    assert fresh["schema"] == RECORD["schema"]
    assert fresh["surfaces"] == RECORD["surfaces"]
    assert fresh["probes"] == RECORD["probes"]
    assert fresh["cells"] == RECORD["cells"]
    assert fresh["summary"] == RECORD["summary"]


def test_every_probe_answer_is_one_of_the_two_values() -> None:
    ids = [probe["id"] for probe in RECORD["probes"]]
    assert len(set(ids)) == len(ids)
    for probe in RECORD["probes"]:
        assert probe["observed"] in {"permitted", "refused"}, probe["id"]
        assert probe["question"].endswith("?"), probe["id"]
        if probe["observed"] == "refused":
            assert probe["detail"], probe["id"]


def test_cell_verdict_is_recomputed_from_its_layers() -> None:
    for cell in RECORD["cells"]:
        verdict, decided_by = _derive_verdict(cell)
        assert (cell["verdict"], cell["decided_by"]) == (verdict, decided_by), cell["id"]
        assert cell["capability"] in CAPABILITIES, cell["id"]
        assert cell["surface"] in {surface["id"] for surface in RECORD["surfaces"]}, cell["id"]


def test_layer_outcomes_agree_with_the_probes_they_cite() -> None:
    observed = {probe["id"]: probe["observed"] for probe in RECORD["probes"]}
    for cell in RECORD["cells"]:
        for layer in cell["layers"]:
            cited = layer["probes"]
            assert all(name in observed for name in cited), (cell["id"], layer["layer"])
            if layer["decided_by"] == "probe":
                assert cited, (cell["id"], layer["layer"])
            answers = [observed[name] for name in cited]
            if not answers:
                assert layer["decided_by"] in {"read", "absence"}, (cell["id"], layer["layer"])
                continue
            expected = "open" if "permitted" in answers else "fenced"
            assert layer["outcome"] == expected, (cell["id"], layer["layer"], answers)


def test_absence_is_never_scored_as_a_decision() -> None:
    for cell in RECORD["cells"]:
        has_absence = any(layer["decided_by"] == "absence" for layer in cell["layers"])
        if has_absence:
            assert cell["verdict"] == "undecidable", cell["id"]
            assert cell["decided_by"] == "absence", cell["id"]
        else:
            assert cell["verdict"] in {"open", "fenced"}, cell["id"]


def test_summary_is_arithmetic_over_the_cells() -> None:
    cells = RECORD["cells"]
    summary = RECORD["summary"]
    verdicts = [cell["verdict"] for cell in cells]
    decided = sum(1 for cell in cells if cell["decided_by"] == "check")
    assert summary["cells"] == len(cells)
    assert summary["open"] == verdicts.count("open")
    assert summary["fenced"] == verdicts.count("fenced")
    assert summary["undecidable"] == verdicts.count("undecidable")
    assert summary["decided_by_check"] == decided
    assert summary["decidability"] == round(decided / len(cells), 4)
    assert summary["effect_verified"] == sum(1 for cell in cells if cell["effect_verified"])
    assert summary["layers"] == sum(len(cell["layers"]) for cell in cells)


def test_verification_sits_behind_a_verified_citation() -> None:
    for cell in RECORD["cells"]:
        if not cell["effect_verified"]:
            assert cell["verified_by"] is None, cell["id"]
            continue
        assert cell["verified_by"] in CITED_TESTS, cell["id"]


def test_every_cited_test_is_in_the_tree() -> None:
    for relative in sorted(CITED_TESTS):
        assert (ROOT / relative).exists(), relative


def test_the_record_disclaims_more_than_it_shows() -> None:
    text = " ".join(RECORD["not_claimed"]).lower()
    assert "containment" in text
    assert "publication_ready" in text
    assert "penetration" in text


def test_the_reading_carries_a_time_and_a_commit() -> None:
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", RECORD["recorded_at"])
    assert re.fullmatch(r"[0-9a-f]{12}", RECORD["reviewed_commit"])


def test_the_basis_page_sends_a_reader_to_the_record() -> None:
    page = BASIS_PAGE.read_text(encoding="utf-8")
    assert "execution-boundary.json" in page
    assert "measure_execution_boundary.py" in page
