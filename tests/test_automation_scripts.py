from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import pytest

from scripts import generate_release_announcement as announcements
from scripts import render_leaderboard as leaderboard
from scripts import update_contributors as contributors


@pytest.mark.parametrize(
    "item",
    [
        {"login": "dependabot[bot]", "type": "Bot"},
        {"login": "github-actions[bot]", "type": "Bot"},
        {"login": "CommandCodeBot", "type": "User"},
    ],
)
def test_is_bot_recognizes_common_bot_accounts(item: dict[str, Any]) -> None:
    assert contributors.is_bot(item)


def test_contributor_render_filters_bots_and_sorts_humans() -> None:
    rendered = contributors.render(
        "owner/repo",
        [
            {"login": "zeta", "type": "User", "contributions": 2},
            {"login": "CommandCodeBot", "type": "User", "contributions": 99},
            {"login": "alpha", "type": "User", "contributions": 3},
        ],
    )

    assert "CommandCodeBot" not in rendered
    assert rendered.index("@alpha") < rendered.index("@zeta")


def test_contributor_render_handles_empty_human_list() -> None:
    rendered = contributors.render(
        "owner/repo",
        [{"login": "dependabot[bot]", "type": "Bot", "contributions": 10}],
    )
    assert "_No human contributors discovered yet_" in rendered


def test_contributor_publish_retries_sha_conflict(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = 0

    monkeypatch.setattr(contributors, "current_file", lambda _repository, _branch: ("sha", "old"))
    monkeypatch.setattr(contributors.time, "sleep", lambda _seconds: None)

    def fake_request(
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        nonlocal attempts
        assert path.endswith("/contents/CONTRIBUTORS.md")
        assert payload is not None
        if method == "PUT":
            attempts += 1
            if attempts == 1:
                raise contributors.GitHubAPIError(409, "conflict")
        return {}

    monkeypatch.setattr(contributors, "request_json", fake_request)
    contributors.publish("owner/repo", "main", "new")

    assert attempts == 2


def test_release_render_uses_canonical_release_data() -> None:
    rendered = announcements.render(
        "v9.9.9",
        {
            "body": "Verified release notes.",
            "published_at": "2026-08-28T12:00:00Z",
            "html_url": "https://github.com/owner/repo/releases/tag/v9.9.9",
        },
    )

    assert "# Data Science Agent v9.9.9" in rendered
    assert "Verified release notes." in rendered
    assert "2026-08-28" in rendered
    assert "https://github.com/owner/repo/releases/tag/v9.9.9" in rendered


def test_release_upsert_retries_conflict_and_preserves_sha(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    put_payloads: list[dict[str, Any]] = []
    put_attempts = 0
    encoded_old = base64.b64encode(b"old").decode("ascii")

    monkeypatch.setattr(announcements.time, "sleep", lambda _seconds: None)

    def fake_request(
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        nonlocal put_attempts
        if method == "GET":
            return {"sha": "existing-sha", "content": encoded_old}
        if method == "PUT":
            assert payload is not None
            put_payloads.append(payload)
            put_attempts += 1
            if put_attempts == 1:
                raise announcements.GitHubAPIError(422, "sha changed")
            return {}
        raise AssertionError(f"unexpected method: {method}")

    monkeypatch.setattr(announcements, "request_json", fake_request)
    announcements.upsert("owner/repo", "main", "docs/announcements/latest.md", "new", "v9.9.9")

    assert put_attempts == 2
    assert all(payload["sha"] == "existing-sha" for payload in put_payloads)


def test_release_upsert_skips_unchanged_content(monkeypatch: pytest.MonkeyPatch) -> None:
    content = "unchanged"
    encoded = base64.b64encode(content.encode()).decode("ascii")
    calls: list[str] = []

    def fake_request(
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        calls.append(method)
        assert payload is None
        return {"sha": "sha", "content": encoded}

    monkeypatch.setattr(announcements, "request_json", fake_request)
    announcements.upsert("owner/repo", "main", "docs/announcements/latest.md", content, "v1.0.0")

    assert calls == ["GET"]


def _entry(**overrides: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "system_name": "DSA",
        "version": "1.0.0",
        "commit": "abcdef123456",
        "benchmark_version": "v2",
        "model": "local",
        "task_success_rate": 1.0,
        "statistical_accuracy": 1.0,
        "evidence_coverage": 1.0,
        "reproducibility": 1.0,
        "latency_ms": 100.0,
        "cost_usd": 0.0,
    }
    entry.update(overrides)
    return entry


def test_leaderboard_load_entries_rejects_invalid_rate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = tmp_path / "leaderboard.json"
    data.write_text(json.dumps([_entry(task_success_rate=1.1)]), encoding="utf-8")
    monkeypatch.setattr(leaderboard, "DATA", data)

    with pytest.raises(ValueError, match="task_success_rate"):
        leaderboard.load_entries()


def test_leaderboard_load_entries_sorts_by_quality_then_latency(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = tmp_path / "leaderboard.json"
    data.write_text(
        json.dumps(
            [
                _entry(system_name="slower", latency_ms=200),
                _entry(system_name="faster", latency_ms=50),
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(leaderboard, "DATA", data)

    entries = leaderboard.load_entries()

    assert [entry["system_name"] for entry in entries] == ["faster", "slower"]


def test_leaderboard_replace_block_requires_markers() -> None:
    with pytest.raises(ValueError, match="markers"):
        leaderboard.replace_block("# no generated block", "generated")
