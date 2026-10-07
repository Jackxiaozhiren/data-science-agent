"""§124, Phase 4 target 7: every documentation page a reader can reach, or none.

`capabilities.navOrphanPages` has been sitting at its 23 ceiling for whole sections of this ledger,
reported and never acted on. The number is not decoration: a page under `docs/` that no `nav:` entry
references is built by mkdocs and reachable only by typing its URL, so the site presents itself as
complete while it hides 23 of its own pages -- including the two verification guides a security
reviewer needs (`security/VERIFY_RELEASE.md`, `security/VERIFY_PYPI_RELEASE.md`), the OSPS baseline,
the whole `v4_3/` evidence record (11 files, 1,594 lines), and the release announcements themselves.

Red on arrival: this file names all 23. The counter is derived from the collector itself, so the test
and the ratchet cannot disagree about what "orphan" means.
"""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MKDOCS = ROOT / "mkdocs.yml"
DOCS = ROOT / "docs"


def _nav_targets(text: str) -> set[str]:
    """Every page path any `nav:` entry resolves to, walking nested sections."""
    nav = yaml.safe_load(text)["nav"]

    def walk(node: object) -> set[str]:
        found: set[str] = set()
        if isinstance(node, dict):
            for value in node.values():
                found |= walk(value)
        elif isinstance(node, list):
            for item in node:
                found |= walk(item)
        elif isinstance(node, str):
            found.add(node)
        return found

    return walk(nav)


def _tracked_docs_pages() -> set[str]:
    """Tracked `docs/*.md`, by path relative to `docs/` -- git-tracked, so a scratch file on disk
    cannot move this number (the §113 lesson: a premise about the tree must be a premise about HEAD).
    """
    listing = subprocess.run(
        ["git", "ls-files", "docs"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    pages = {line.removeprefix("docs/") for line in listing if line.endswith(".md")}
    assert len(pages) >= 40, f"only {len(pages)} tracked pages -- the listing broke"
    return pages


def _orphan_pages(nav_pages: set[str], disk_pages: set[str]) -> set[str]:
    return {p for p in disk_pages if p not in nav_pages}


def test_the_collector_and_this_test_share_one_definition_of_orphan() -> None:
    """One number, one owner: the ratchet's derivation is the one asserted here."""
    spec = importlib.util.spec_from_file_location(
        "audit_facts_for_nav", ROOT / "scripts" / "audit_facts.py"
    )
    assert spec and spec.loader, "cannot load scripts/audit_facts.py"
    collector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(collector)
    capabilities = collector._collect_capabilities()
    assert _orphan_pages(
        _nav_targets(MKDOCS.read_text(encoding="utf-8")), _tracked_docs_pages()
    ) == set(capabilities["navOrphanPages"]), (
        "the test's derivation and the gate's disagree about what nav reachability means"
    )


def test_no_documented_page_is_unreachable_from_the_nav() -> None:
    orphans = _orphan_pages(_nav_targets(MKDOCS.read_text(encoding="utf-8")), _tracked_docs_pages())
    assert not orphans, "pages built but never navigable:\n  " + "\n  ".join(sorted(orphans))


def test_no_nav_entry_points_at_a_page_that_is_not_there() -> None:
    nav_pages = _nav_targets(MKDOCS.read_text(encoding="utf-8"))
    missing = sorted(p for p in nav_pages if not (DOCS / p).is_file())
    assert not missing, f"nav entries with no file behind them: {missing}"


def test_the_control_a_dropped_entry_is_reported_and_a_planted_one_is_dangling(
    tmp_path: Path,
) -> None:
    text = MKDOCS.read_text(encoding="utf-8")
    pages = _tracked_docs_pages()

    dropped = "\n".join(line for line in text.splitlines() if "evidence.md" not in line)
    assert dropped != text, "the fixture edit did not land -- this control proves nothing"
    assert "evidence.md" in _orphan_pages(_nav_targets(dropped), pages), (
        "removing the nav entry left the page reachable: the reader is guessing"
    )
    assert _nav_targets(dropped) != _nav_targets(text)

    planted = text.replace("nav:\n", "nav:\n  - Ghost: not-a-page.md\n", 1)
    assert planted != text, "the planted entry did not land"
    assert "not-a-page.md" in _nav_targets(planted)
    assert "not-a-page.md" in {p for p in _nav_targets(planted) if not (DOCS / p).is_file()}
