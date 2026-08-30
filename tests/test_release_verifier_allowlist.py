from __future__ import annotations

import json

import dsa_evaluation.verify_release as release_verifier


def _manifest() -> dict[str, object]:
    return {
        "version": "4.3.0",
        "release_tag": "v4.3.0",
        "status": "release-candidate",
        "source_candidate_commit": "f" * 40,
        "gates": {key: "pass" for key in release_verifier._REQUIRED_EVIDENCE_GATES},
    }


def _write_manifest(tmp_path, payload: dict[str, object]) -> None:
    release_dir = tmp_path / "release" / "v4.3.0"
    release_dir.mkdir(parents=True)
    (release_dir / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")


def test_release_verifier_accepts_complete_retained_evidence(tmp_path, monkeypatch) -> None:
    _write_manifest(tmp_path, _manifest())
    monkeypatch.setattr(release_verifier, "ROOT", tmp_path)

    report = release_verifier.verify_release("v4.3.0")

    assert report["summary"] == "14/14 PASS"
    assert report["mode"] == "evidence-validation"
    assert report["manifest"] == str(tmp_path / "release" / "v4.3.0" / "manifest.json")
    assert not report["details"]


def test_release_verifier_rejects_invalid_candidate_sha(tmp_path, monkeypatch) -> None:
    manifest = _manifest()
    manifest["source_candidate_commit"] = "not-a-sha"
    _write_manifest(tmp_path, manifest)
    monkeypatch.setattr(release_verifier, "ROOT", tmp_path)

    report = release_verifier.verify_release("4.3.0")

    assert report["gates"]["source candidate SHA"] == "FAIL"
    assert report["summary"] == "13/14 PASS"


def test_release_verifier_does_not_map_unknown_version_to_a_path(tmp_path, monkeypatch) -> None:
    _write_manifest(tmp_path, _manifest())
    monkeypatch.setattr(release_verifier, "ROOT", tmp_path)

    report = release_verifier.verify_release("../../etc")

    assert report["manifest"] is None
    assert report["gates"]["manifest present"] == "FAIL"
    assert "Unsupported release identifier" in report["details"]["manifest present"]
