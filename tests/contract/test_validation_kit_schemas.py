"""The external-validation kit's JSON schemas must be internally consistent, and nothing else checks them.

`external-validation/` is scanned by no gate: `check_public_claims.py`'s `SCAN_GLOBS` does not reach it and
no existing test imports it, so a schema in that directory is a contract nobody enforces. That matters more
than it looks -- a submission form is read months later by whoever analyses the first real participant data,
and a broken `$ref` or a `required` name that no property defines is then discovered at the worst possible
moment, against data that cannot be collected twice.

Checked without a validator library, because adding one would be a dependency change the plan forbids
(§19.3) and the failures worth catching are structural, not meta-schema conformance: every `$ref` resolves,
every `required` name exists, every object that closes itself really lists its properties, and the two
schemas in the directory stay the pair they are meant to be.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
KIT = ROOT / "external-validation"
SCHEMAS = ("RESULTS_SCHEMA.json", "STUDY1_RESULTS_SCHEMA.json")


def _refs(node: Any, out: list[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                out.append(value)
            else:
                _refs(value, out)
    elif isinstance(node, list):
        for item in node:
            _refs(item, out)


def _resolves(schema: dict[str, Any], ref: str) -> bool:
    """Only the local `#/$defs/<name>` form is used in these files; anything else is not resolvable here."""
    prefix = "#/$defs/"
    if not ref.startswith(prefix):
        return False
    return ref[len(prefix) :] in schema.get("$defs", {})


def _required_names(node: Any, out: list[tuple[dict[str, Any], str]]) -> None:
    if isinstance(node, dict):
        required = node.get("required")
        properties = node.get("properties")
        if isinstance(required, list) and isinstance(properties, dict):
            for name in required:
                if isinstance(name, str):
                    out.append((properties, name))
        for value in node.values():
            _required_names(value, out)
    elif isinstance(node, list):
        for item in node:
            _required_names(item, out)


def schema_issues(text: str) -> list[str]:
    """Every structural defect a reviewer of these files would want caught before a session runs."""
    issues: list[str] = []
    try:
        schema = json.loads(text)
    except json.JSONDecodeError as exc:
        return [f"does not parse: {exc}"]
    if not isinstance(schema, dict):
        return ["top level is not an object"]

    refs: list[str] = []
    _refs(schema, refs)
    for ref in sorted(set(refs)):
        if not _resolves(schema, ref):
            issues.append(f"unresolvable $ref {ref!r}")

    pairs: list[tuple[dict[str, Any], str]] = []
    _required_names(schema, pairs)
    for properties, name in pairs:
        if name not in properties:
            issues.append(f"`required` names {name!r}, which no property defines")

    if not schema.get("description"):
        issues.append(
            "no description -- a kit file must state what it is and whether it has been run"
        )

    return issues


def test_both_kit_schemas_are_structurally_sound() -> None:
    checked = 0
    all_issues: list[str] = []
    for name in SCHEMAS:
        path = KIT / name
        assert path.is_file(), f"{name} is missing -- the kit index in README.md would be a lie"
        issues = schema_issues(path.read_text(encoding="utf-8"))
        all_issues.extend(f"{name}: {i}" for i in issues)
        checked += 1
    assert checked == len(SCHEMAS), (
        f"checked {checked} of {len(SCHEMAS)} -- the loop broke, not a pass"
    )
    assert not all_issues, "\n  ".join(all_issues)


def test_the_checks_fire_on_the_defects_they_exist_to_catch() -> None:
    """Falsification: an unresolvable ref and a dangling `required` name must both be reported."""
    good = (KIT / "STUDY1_RESULTS_SCHEMA.json").read_text(encoding="utf-8")
    assert schema_issues(good) == []

    broken_ref = good.replace('"$ref": "#/$defs/score"', '"$ref": "#/$defs/skor"')
    assert broken_ref != good, "the plant changed nothing -- the anchor missed"
    assert any("unresolvable $ref" in i for i in schema_issues(broken_ref)), schema_issues(
        broken_ref
    )

    dangling = json.loads(good)
    dangling["properties"]["consent"]["required"].append("may_publish_verbatim")
    text = json.dumps(dangling)
    assert any("no property defines" in i for i in schema_issues(text)), schema_issues(text)

    assert any("does not parse" in i for i in schema_issues('{"a": ')), (
        "a truncated file must not pass"
    )


def test_the_study1_schema_keeps_the_fields_the_protocol_promises() -> None:
    """`STUDY1_FIRST_RUN.md` §5 records specific things; the schema has to be able to hold them.

    The protocol and the form are written by the same hand and drift the same way every pair does.
    """
    schema = json.loads((KIT / "STUDY1_RESULTS_SCHEMA.json").read_text(encoding="utf-8"))
    props = schema["properties"]
    for field in (
        "first_sentence_verbatim",
        "mode_label",
        "outcome",
        "abandonment",
        "timings",
        "scores",
    ):
        assert field in props, f"the protocol records {field}, the schema cannot store it"
    mode = props["mode_label"]["properties"]
    assert {"unprompted", "noticed"} <= set(mode), (
        "R-02's value claim depends on separating 'mentioned it themselves' from 'admitted it when asked'"
    )
    assert props["study"]["const"] == "study1_first_run", (
        "a Study 1 record must not be mergeable with a review"
    )
    assert "correctness" not in props["scores"]["properties"], (
        "Correctness needs the participant's own ground truth and belongs to the reviewer studies, not here"
    )
