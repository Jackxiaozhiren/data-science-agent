"""§96: the stale-claims gate must not report "clean" about a file it could not read.

`scan_file` ended in `except Exception: return []`, so a scanned document that raised on
read contributed nothing and the run printed its success line -- a gate silently subtracting
its own scope. The same file also needs to be *high severity*: the reporting step prints
low/medium findings and still exits 0, so a finding nobody fails on is a notice, not a gate.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/check_public_claims.py"


def _module() -> object:
    spec = importlib.util.spec_from_file_location("cpc_unreadable", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _refusing(monkeypatch: pytest.MonkeyPatch, name: str) -> None:
    real = Path.read_text

    def refuse(self: Path, *args: object, **kwargs: object) -> str:
        if self.name == name:
            raise OSError("permission gone")
        return real(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", refuse)


def test_an_unreadable_scanned_file_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _module()
    target = tmp_path / "README.md"
    target.write_text("# v4.4.0\n", encoding="utf-8")
    _refusing(monkeypatch, "README.md")

    findings = module.scan_file(target)  # type: ignore[attr-defined]
    assert findings, "an unreadable file produced no finding -- the gate looked away"
    kind, match, _line = findings[0]
    assert kind == "unreadable_file", kind
    assert "permission gone" in match, match


def test_a_readable_file_earns_no_unreadable_finding(tmp_path: Path) -> None:
    """Green-on-arrival: the fix must not flag the ordinary case."""
    module = _module()
    target = tmp_path / "ok.md"
    target.write_text("nothing version shaped about here\n", encoding="utf-8")

    findings = module.scan_file(target)  # type: ignore[attr-defined]
    assert [f for f in findings if f[0] == "unreadable_file"] == []


def test_unreadable_is_high_severity_so_the_gate_cannot_exit_zero() -> None:
    module = _module()
    prefixes = module.HIGH_SEVERITY_PREFIXES  # type: ignore[attr-defined]
    assert "unreadable_file" in prefixes, (
        f"the finding would only be printed, not failed: {sorted(prefixes)}"
    )


def test_the_existing_high_severity_rules_are_unchanged() -> None:
    """Guard the extraction: moving the tuple into a constant must keep every rule."""
    module = _module()
    prefixes = set(module.HIGH_SEVERITY_PREFIXES)  # type: ignore[attr-defined]
    assert {
        "version_consistency",
        "currency_claims",
        "measurement_claims",
        "old_package_pip",
        "old_repo",
    } <= prefixes
