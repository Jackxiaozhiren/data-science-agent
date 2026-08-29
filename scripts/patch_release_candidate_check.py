from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[1]


def replace(path: str, old: str, new: str, *, count: int = 1) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"{path}: expected block not found")
    target.write_text(text.replace(old, new, count), encoding="utf-8")


def main() -> None:
    replace(
        "scripts/check_public_claims.py",
        "import re\nimport sys\n",
        "import os\nimport re\nimport sys\n",
    )
    replace(
        "scripts/check_public_claims.py",
        "def check_version_consistency():\n",
        '''def _allow_release_candidate_tag(base_tag: str, expected_version: str) -> bool:\n    \"\"\"Allow a forward same-major version only under explicit RC mode.\"\"\"\n    if os.getenv(\"DSA_RELEASE_CANDIDATE\", \"\").strip().lower() not in {\n        \"1\",\n        \"true\",\n        \"yes\",\n    }:\n        return False\n    try:\n        tagged = tuple(int(part) for part in base_tag.removeprefix(\"v\").split(\".\"))\n        expected = tuple(int(part) for part in expected_version.split(\".\"))\n    except ValueError:\n        return False\n    return len(tagged) == 3 and len(expected) == 3 and tagged[0] == expected[0] and expected > tagged\n\n\ndef check_version_consistency():\n''',
    )
    replace(
        "scripts/check_public_claims.py",
        '''        if base_tag != f"v{EXPECTED['version']}":\n            issues.append(f"git tag mismatch: {tag} base {base_tag} != v{EXPECTED['version']}")\n''',
        '''        if base_tag != f"v{EXPECTED['version']}" and not _allow_release_candidate_tag(\n            base_tag, EXPECTED["version"]\n        ):\n            issues.append(f"git tag mismatch: {tag} base {base_tag} != v{EXPECTED['version']}")\n''',
    )
    replace(
        "tests/test_automation_scripts.py",
        "from scripts import generate_release_announcement as announcements\n",
        "from scripts import check_public_claims as public_claims\nfrom scripts import generate_release_announcement as announcements\n",
    )
    tests = ROOT / "tests/test_automation_scripts.py"
    text = tests.read_text(encoding="utf-8")
    marker = "def test_public_claims_release_candidate_tag_mode_is_explicit"
    if marker not in text:
        text += '''\n\ndef test_public_claims_release_candidate_tag_mode_is_explicit(\n    monkeypatch: pytest.MonkeyPatch,\n) -> None:\n    monkeypatch.delenv(\"DSA_RELEASE_CANDIDATE\", raising=False)\n    assert not public_claims._allow_release_candidate_tag(\"v4.2.10\", \"4.3.0\")\n\n    monkeypatch.setenv(\"DSA_RELEASE_CANDIDATE\", \"1\")\n    assert public_claims._allow_release_candidate_tag(\"v4.2.10\", \"4.3.0\")\n    assert not public_claims._allow_release_candidate_tag(\"v4.3.0\", \"4.2.10\")\n    assert not public_claims._allow_release_candidate_tag(\"v5.0.0\", \"4.3.0\")\n    assert not public_claims._allow_release_candidate_tag(\"not-a-tag\", \"4.3.0\")\n'''
        tests.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
