"""Item 1 of the free-tier persistence discussion: the demo must be able to say it forgets.

`is_ephemeral_database()` has known that since it was written, but it only ever spoke to the server log, so
a visitor whose run vanished after an idle spin-down had no way to tell "this instance is free and its
container is recreated" from "this application loses data". `/version` now publishes the same fact, and the
web shell renders it -- which makes three things worth pinning, all of them measured rather than assumed:

* the rule is one rule. The macOS scratch directory has two spellings (`/tmp` and `/private/tmp`, and the
  same for `/var/folders`), and a check written against one of them reports throwaway storage as durable.
  `Path.resolve()` hands you the second spelling, so this is not a hypothetical.
* the disclosure names roles, never locations. `/version` is unauthenticated.
* `durable` is derived from the configuration the process actually holds. A constant that happens to be
  correct today is how the next §159-shaped stale claim gets shipped.
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
TS_OWNER = ROOT / "apps/web/lib/buildProvenance.ts"
TS_RENDERER = ROOT / "apps/web/app/components/layout/ProvenanceStatus.tsx"

ROLES = {"database", "datasets", "artifacts"}

#: (value, ephemeral). The two `/private/...` rows are the ones a single-spelling check gets wrong.
PREDICATE_CASES = [
    ("/tmp/dsa.db", True),
    ("/private/tmp/dsa.db", True),
    ("/var/folders/5l/abc/T/dsa.db", True),
    ("/private/var/folders/5l/abc/T/dsa.db", True),
    ("sqlite+aiosqlite:////tmp/dsa.db", True),
    ("sqlite+aiosqlite:///:memory:", True),
    ("sqlite+aiosqlite:////var/data/dsa.db", False),
    ("/var/data/datasets", False),
    ("/app/artifacts", False),
    ("./data/dsa.db", False),
    ("postgresql+asyncpg://db/dsa", False),
]


def disclosure_issues(payload: dict[str, Any]) -> list[str]:
    """Every way a storage disclosure can fail to be a disclosure: wrong shape, or a location leaking."""
    issues: list[str] = []
    if set(payload) != {"durable", "ephemeral_roots"}:
        issues.append(f"keys are {sorted(payload)}, expected exactly durable + ephemeral_roots")
    if not isinstance(payload.get("durable"), bool):
        issues.append("`durable` is not a boolean -- the UI branches on it")
    roots = payload.get("ephemeral_roots")
    if not isinstance(roots, list) or any(not isinstance(item, str) for item in roots or []):
        issues.append("`ephemeral_roots` is not a list of role names")
        return issues
    unknown = set(roots) - ROLES
    if unknown:
        issues.append(f"roles outside the known set: {sorted(unknown)}")
    if payload.get("durable") and roots:
        issues.append("claims durable while naming throwaway roots")
    if not payload.get("durable") and not roots:
        issues.append("claims non-durable while naming no root -- an unfalsifiable warning")
    for value in [*roots, *payload.values()]:
        if isinstance(value, str) and value.startswith("/"):
            issues.append(f"publishes a filesystem location: {value!r}")
    return issues


# ---------------------------------------------------------------- one rule, both spellings


@pytest.mark.parametrize(("value", "ephemeral"), PREDICATE_CASES)
def test_the_ephemeral_rule(value: str, ephemeral: bool) -> None:
    from dsa_api.core.storage_state import is_ephemeral_path

    assert is_ephemeral_path(value) is ephemeral, value


def test_the_database_predicate_is_that_rule_and_not_a_second_copy() -> None:
    from dsa_api.core.database import is_ephemeral_database
    from dsa_api.core.storage_state import is_ephemeral_path

    for value, _ in PREDICATE_CASES:
        assert is_ephemeral_database(value) is is_ephemeral_path(value), value


# ---------------------------------------------------------------- derived, not remembered


def _report_with(
    monkeypatch: pytest.MonkeyPatch, *, database: str, datasets: str, artifacts: str
) -> dict[str, Any]:
    from dsa_api.core import storage_state
    from dsa_api.core.config import settings

    monkeypatch.setattr(settings, "database_url", database, raising=True)
    monkeypatch.setenv("DSA_DATASET_DIR", datasets)
    monkeypatch.setenv("DSA_ARTIFACT_ROOT", artifacts)
    return storage_state.storage_report()


def test_a_free_instance_configuration_reports_which_roots_are_throwaway(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _report_with(
        monkeypatch,
        database="sqlite+aiosqlite:////tmp/dsa.db",
        datasets="/app/data/datasets",
        artifacts="/tmp/artifacts",
    )
    assert payload["ephemeral_roots"] == ["artifacts", "database"]
    assert payload["durable"] is False
    assert disclosure_issues(payload) == []


def test_a_stage_one_configuration_reports_durable(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _report_with(
        monkeypatch,
        database="sqlite+aiosqlite:////var/data/dsa.db",
        datasets="/var/data/datasets",
        artifacts="/var/data/artifacts",
    )
    assert payload == {"durable": True, "ephemeral_roots": []}
    assert disclosure_issues(payload) == []


def test_the_report_reads_the_configuration_at_call_time(monkeypatch: pytest.MonkeyPatch) -> None:
    """A value cached at import would keep saying `durable` after the operator mounts a disk, and vice versa."""
    first = _report_with(
        monkeypatch,
        database="sqlite+aiosqlite:////var/data/dsa.db",
        datasets="/var/data/datasets",
        artifacts="/var/data/artifacts",
    )
    second = _report_with(
        monkeypatch,
        database="sqlite+aiosqlite:////tmp/dsa.db",
        datasets="/var/data/datasets",
        artifacts="/var/data/artifacts",
    )
    assert (first["durable"], second["durable"]) == (True, False)
    assert second["ephemeral_roots"] == ["database"]


# ---------------------------------------------------------------- the endpoint publishes it


def test_version_publishes_the_same_report_the_module_computes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dsa_api.core.storage_state import storage_report
    from dsa_api.routers.health import version as version_route

    payload = asyncio.run(version_route())
    assert payload["storage"] == storage_report()
    assert disclosure_issues(payload["storage"]) == []
    assert "reasoning_mode" in payload and "version" in payload, (
        "the disclosure did not arrive intact"
    )


def test_the_serialised_form_carries_no_path() -> None:
    from dsa_api.core.storage_state import storage_report

    text = json.dumps(storage_report())
    assert '"/' not in text, f"an absolute path reached the wire: {text}"


# ---------------------------------------------------------------- the web side reads it once


def ts_owner_issues(owner: str, renderer: str) -> list[str]:
    issues: list[str] = []
    if "asStorageState" not in owner:
        issues.append("buildProvenance.ts no longer parses `storage` -- the field would be ignored")
    if "durable" not in owner or "ephemeral_roots" not in owner:
        issues.append("the parser stopped reading one of the two published keys")
    if "describeStorage" not in owner:
        issues.append("the wording left its owner")
    if "if (state.durable) return null" not in owner:
        issues.append("describeStorage no longer stays quiet on a durable deployment")
    if "describeStorage" not in renderer or "storage.short" not in renderer:
        issues.append("ProvenanceStatus stopped rendering the disclosure")
    if re.search(r">\s*not kept\s*<", renderer):
        issues.append("ProvenanceStatus hardcodes the warning instead of asking the API")
    return issues


def test_the_web_layer_owns_the_storage_wording_in_one_module() -> None:
    assert (
        ts_owner_issues(
            TS_OWNER.read_text(encoding="utf-8"), TS_RENDERER.read_text(encoding="utf-8")
        )
        == []
    )


def test_the_web_check_can_fail() -> None:
    """Negative control on synthetic sources, so the real ones are not being compared with themselves."""
    dropped_parser = TS_OWNER.read_text(encoding="utf-8").replace(
        "asStorageState", "asSomethingElse"
    )
    assert any(
        "no longer parses" in issue
        for issue in ts_owner_issues(dropped_parser, TS_RENDERER.read_text(encoding="utf-8"))
    )

    always_warns = TS_OWNER.read_text(encoding="utf-8").replace(
        "if (state.durable) return null;", "/* warning always fires */"
    )
    assert any(
        "stays quiet" in issue
        for issue in ts_owner_issues(always_warns, TS_RENDERER.read_text(encoding="utf-8"))
    )

    hardcoded = TS_RENDERER.read_text(encoding="utf-8").replace(
        '{storage ? <span className="shrink-0 text-amber-700">{storage.short}</span> : null}',
        '<span className="shrink-0 text-amber-700">not kept</span>',
    )
    assert hardcoded != TS_RENDERER.read_text(encoding="utf-8"), "the planted renderer did not land"
    assert any(
        "hardcodes" in issue
        for issue in ts_owner_issues(TS_OWNER.read_text(encoding="utf-8"), hardcoded)
    )
