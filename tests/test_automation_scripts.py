from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import pytest

from scripts import check_public_claims as public_claims
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


def test_missing_version_pattern_is_reported_not_swallowed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "src/data_science_agent").mkdir(parents=True)
    (tmp_path / "release").mkdir()
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n', encoding="utf-8")
    (tmp_path / "CITATION.cff").write_text("cff-version: 1.2.0\n", encoding="utf-8")
    (tmp_path / "src/data_science_agent/__init__.py").write_text(
        '__version__ = "4.4.0"\n', encoding="utf-8"
    )
    (tmp_path / "src/data_science_agent/sdk.py").write_text(
        'self._version = "4.4.0"\n', encoding="utf-8"
    )
    (tmp_path / "release/sbom.json").write_text('{"version": "4.4.0"}', encoding="utf-8")
    monkeypatch.setattr(public_claims, "ROOT", tmp_path)

    issues = public_claims.check_version_consistency()

    assert any("pyproject=?" in issue for issue in issues), issues
    assert not any("check error" in issue for issue in issues), issues


def test_scan_scope_separates_declared_scope_from_surface_actually_read() -> None:
    root = public_claims.ROOT
    scanned, skipped = public_claims.scan_scope(root)
    prefixes = tuple(public_claims.HISTORICAL_PREFIXES)

    assert "docs/**/*.md" in public_claims.SCAN_GLOBS
    assert skipped, "the checker reads a fraction of what its globs advertise"
    assert all(str(p.relative_to(root)).startswith(prefixes) for p in skipped)
    assert not any(str(p.relative_to(root)).startswith(prefixes) for p in scanned)


def test_identical_text_is_flagged_only_outside_a_historical_prefix(tmp_path: Path) -> None:
    body = "Install it with pip install data-science-agent today.\n"
    (tmp_path / "README.md").write_text(body, encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_text(body, encoding="utf-8")
    (tmp_path / "docs" / "v4_3").mkdir()
    (tmp_path / "docs" / "v4_3" / "record.md").write_text(body, encoding="utf-8")

    scanned, skipped = public_claims.scan_scope(tmp_path)

    # §130: `docs/` is no longer exempt as a whole, so the live page joins README in the scanned
    # set and only the dated archive under it is skipped. Same bytes, verdict keyed on path.
    assert sorted(p.name for p in scanned) == ["README.md", "guide.md"], [p.name for p in scanned]
    assert [p.name for p in skipped] == ["record.md"]
    # Payload is a naming claim, not a number: the typed "155 tests" rule was retired in
    # §76 precisely because it could only catch numbers somebody had typed once.
    # Byte-identical text, opposite verdicts: the exclusion keys off the path, so
    # a clean run says nothing about anything under a historical prefix.
    assert public_claims.scan_file(scanned[0])
    assert public_claims.scan_file(skipped[0])


def test_public_claims_release_candidate_ref_is_narrow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GITHUB_HEAD_REF", raising=False)
    monkeypatch.delenv("GITHUB_REF_NAME", raising=False)
    assert not public_claims._is_release_candidate_ref("4.3.0")

    monkeypatch.setenv("GITHUB_HEAD_REF", "release/v4.3.0-rc")
    assert public_claims._is_release_candidate_ref("4.3.0")

    monkeypatch.setenv("GITHUB_HEAD_REF", "release/v4.3.0-rc2")
    assert public_claims._is_release_candidate_ref("4.3.0")

    monkeypatch.setenv("GITHUB_HEAD_REF", "release/v4.4.0-rc")
    assert not public_claims._is_release_candidate_ref("4.3.0")

    monkeypatch.setenv("GITHUB_HEAD_REF", "feature/v4.3.0-rc")
    assert not public_claims._is_release_candidate_ref("4.3.0")

    monkeypatch.delenv("GITHUB_HEAD_REF", raising=False)
    monkeypatch.setenv("GITHUB_REF_NAME", "release/v4.3.0-rc1")
    assert public_claims._is_release_candidate_ref("4.3.0")


# --- §113: the claim checker's own scope claims ------------------------------------------------
#
# `HISTORICAL_PREFIXES` is a declaration that a surface was read and judged era-bound. Two of its
# six entries named trees no `SCAN_GLOBS` pattern can reach, so `scan_scope()` never opened them
# and never counted them: the printed "N skipped as historical" understated nothing about the trees
# it *did* read, but the list itself promised coverage that did not exist. Phase 4 target 1 asks
# for the skip-list to be derived rather than assumed, which is what these measure.


def _reachable_prefix_counts(root: Path) -> dict[str, int]:
    """How many files each declared exemption can actually reach through the configured globs."""
    counts = dict.fromkeys(public_claims.HISTORICAL_PREFIXES, 0)
    for pattern in public_claims.SCAN_GLOBS:
        for path in root.glob(pattern):
            if any(x in str(path) for x in public_claims.NOISE_SUBSTRINGS):
                continue
            rel = str(path.relative_to(root))
            for prefix in counts:
                if rel.startswith(prefix):
                    counts[prefix] += 1
    return counts


def test_no_historical_prefix_is_declared_without_a_glob_that_reaches_it() -> None:
    """RED before §113: `research/` and `benchmarks/` were unreachable exemptions."""
    counts = _reachable_prefix_counts(public_claims.ROOT)
    dead = sorted(prefix for prefix, n in counts.items() if n == 0)
    assert not dead, f"declared exempt but reachable by no SCAN_GLOB (never opened): {dead}"


def test_the_control_an_unreachable_prefix_is_reported_and_a_reachable_one_is_not(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The guard above must key on reachability, not on the shipped list."""
    (tmp_path / "docs" / "v4_3").mkdir(parents=True)
    (tmp_path / "docs" / "v4_3" / "record.md").write_text("x\n", encoding="utf-8")
    monkeypatch.setattr(public_claims, "SCAN_GLOBS", ["README.md", "docs/**/*.md"])
    counts = _reachable_prefix_counts(tmp_path)
    assert counts.get("docs/v4_3/") == 1, counts
    dead = sorted(p for p, n in counts.items() if n == 0)
    assert "research/" in dead, dead
    assert "src/data_science_agent/" in dead, dead

    (tmp_path / "research").mkdir()
    (tmp_path / "research" / "paper.md").write_text("x\n", encoding="utf-8")
    monkeypatch.setattr(
        public_claims, "SCAN_GLOBS", ["README.md", "docs/**/*.md", "research/**/*.md"]
    )
    assert "research/" not in [p for p, n in _reachable_prefix_counts(tmp_path).items() if n == 0]


def test_the_benchmark_readmes_are_inside_the_surface_the_checker_reads() -> None:
    """The freeze document is current-tense product prose, not a historical record."""
    scanned, skipped = public_claims.scan_scope(public_claims.ROOT)
    names = {str(p.relative_to(public_claims.ROOT)) for p in scanned}
    assert "benchmarks/baseline/README.md" in names, sorted(n for n in names if "benchmark" in n)
    assert "benchmarks/baseline/README.md" not in {
        str(p.relative_to(public_claims.ROOT)) for p in skipped
    }


def test_the_vendored_workspace_tree_is_neither_scanned_nor_counted(tmp_path: Path) -> None:
    """`.workspace` holds a third-party clone, so it belongs with `node_modules`, not with prose.

    Exercised on a fixture rather than the shipped tree, because `.workspace` is gitignored
    (`.gitignore:49`, zero files tracked): on a clean checkout the glob under test matches nothing,
    so a premise asserted against disk would pass here and go red on the runner -- §103's exact trap,
    re-earned.
    """
    assert ".workspace" in public_claims.NOISE_SUBSTRINGS, "the vendored-tree exclusion was dropped"
    (tmp_path / "benchmarks/baseline").mkdir(parents=True)
    (tmp_path / "benchmarks/baseline/README.md").write_text("x\n", encoding="utf-8")
    deep = tmp_path / "benchmarks/external/datascibench/.workspace/MetaGPT"
    deep.mkdir(parents=True)
    (deep / "README.md").write_text("pip install metagpt\n", encoding="utf-8")
    scanned, skipped = public_claims.scan_scope(tmp_path)
    names = sorted(str(p.relative_to(tmp_path)) for p in (*scanned, *skipped))
    assert "benchmarks/baseline/README.md" in [str(p.relative_to(tmp_path)) for p in scanned], names
    assert not any(".workspace" in n for n in names), (
        f"a vendored README reached the claim scan: {names}"
    )


# --- §130: the claim checker used to skip all of `docs/` ---------------------------

LIVE_DOCS_PAGES = (
    "docs/getting-started.md",
    "docs/reproducibility.md",
    "docs/api.md",
    "docs/architecture.md",
    "docs/security.md",
    "docs/security/VERIFY_RELEASE.md",
    "docs/tools.md",
    # §136: the announcement copy tells readers which release to install, so it is a live surface,
    # not a record -- five published releases went by with it naming v4.2.10 and nothing saw it.
    "docs/announcements/latest.md",
)
DATED_DOCS_RECORDS = (
    "docs/v4_3/",
    "docs/announcements/v",
    "docs/announcements/README.md",
    "docs/ADR/",
)


def _scanned_names() -> tuple[set[str], set[str]]:
    scanned, skipped = public_claims.scan_scope(public_claims.ROOT)
    root = public_claims.ROOT
    return (
        {str(p.relative_to(root)) for p in scanned},
        {str(p.relative_to(root)) for p in skipped},
    )


def test_the_current_docs_pages_are_inside_the_surface_the_checker_reads() -> None:
    """Target 1's unfinished half: `docs/` sat in `HISTORICAL_PREFIXES` whole.

    47 markdown files under `docs/` matched the checker's own globs, and every one of them was
    classified as a historical record -- including the pages a user follows to install, reproduce or
    verify a release. A blanket prefix is how a checker reports "0 issues" while reading a third of
    its advertised surface, which is §113.3's complaint about two dead prefixes, one level up.
    """
    scanned, skipped = _scanned_names()
    missing = [p for p in LIVE_DOCS_PAGES if p not in scanned]
    assert not missing, f"still skipped as historical: {missing}"
    assert "docs/reproducibility.md" not in skipped


def test_only_dated_docs_records_are_exempted_and_each_still_matches_something() -> None:
    """Each exemption is a dated record; and a prefix with no reachable file is §113's defect.

    `docs/audit/` was the tempting fourth -- it is not release prose. Measured, `SCAN_GLOBS` matches
    zero `.md` under it, so declaring it would have been exactly the dead exemption the reachability
    test below kills.
    """
    prefixes = set(public_claims.HISTORICAL_PREFIXES)
    assert "docs/" not in prefixes, "the whole docs tree is exempt again"
    assert set(DATED_DOCS_RECORDS) <= prefixes, sorted(prefixes)
    counts = _reachable_prefix_counts(public_claims.ROOT)
    for prefix in DATED_DOCS_RECORDS:
        assert counts.get(prefix, 0) > 0, f"{prefix} matches no file the checker can reach"
    assert counts.get("docs/audit/", 0) == 0, (
        "docs/audit/ is reachable now; revisit the exemption list"
    )
    dead = sorted(p for p in prefixes if counts.get(p, 0) == 0)
    assert not dead, f"historical prefixes that reach nothing: {dead}"


def test_the_widened_net_costs_no_suppression_and_no_finding() -> None:
    """Raising what can fail must not require quieting anything (the §113.3 shape, re-run).

    Before: 19 files scanned, 85 skipped. After: 50 and 54, and all four rules still report zero
    issues -- so the wider surface is bought without an exemption, a `noqa`, or a tuned-down rule.
    """
    scanned, skipped = _scanned_names()
    assert len(scanned) >= 45, f"only {len(scanned)} files scanned -- the widening was reverted"
    assert public_claims.check_currency_claims() == []
    assert public_claims.check_measurement_claims() == []
    assert public_claims.check_maturity() == []
    assert public_claims.check_version_consistency() == []
