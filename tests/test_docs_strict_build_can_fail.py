"""§129, Phase 4 target 1: `mkdocs build --strict` is shown to be able to fail.

CI runs `uv run python -m mkdocs build --strict` as a gate, and `mkdocs.yml` sets
`validation.links.not_found: warn`. "warn" plus "--strict" is the whole mechanism, and it is exactly the
kind of gate that can read as protection while doing nothing: a warning that strict happens to promote to
an error is a check, and one that does not is a log line. Per §11.3 a guard must be shown capable of
failing, and per §26 "exit 0 is not evidence" -- so this file builds a two-page site whose link is broken,
requires the build to be red with the reason named, then repairs the link and requires green.

The fixture is a scratch tree with its own `mkdocs.yml`; the real `docs/` is never written to. The site is
built with the material theme the project pins, so the probe is of the same code path CI runs, not of a
default theme.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PAGES = {
    "index.md": "# Home\n\nSee the [guide](guide.md).\n",
    "guide.md": "# Guide\n\nBack to the [home](index.md).\n",
}


def _build(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "mkdocs",
            "build",
            "--strict",
            "--clean",
            "-f",
            str(root / "mkdocs.yml"),
            "-d",
            str(root / "site"),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def _scratch(tmp_path: Path, *, pages: dict[str, str]) -> Path:
    root = tmp_path / "site"
    docs = root / "docs"
    docs.mkdir(parents=True)
    (docs / "index.md").write_text(pages["index.md"], encoding="utf-8")
    (docs / "guide.md").write_text(pages["guide.md"], encoding="utf-8")
    (root / "mkdocs.yml").write_text(
        "site_name: Probe\n"
        "docs_dir: docs\n"
        "theme:\n"
        "  name: material\n"
        "nav:\n"
        "  - Home: index.md\n"
        "  - Guide: guide.md\n"
        "markdown_extensions:\n"
        "  - toc:\n"
        "       permalink: true\n"
        "validation:\n"
        "  links:\n"
        "    not_found: warn\n"
        "    absolute_links: ignore\n",
        encoding="utf-8",
    )
    return root


def test_a_broken_internal_link_fails_the_strict_build(tmp_path: Path) -> None:
    """The red half: `missing.md` is referenced and does not exist."""
    broken = {
        "index.md": "# Home\n\nSee the [guide](guide.md) and the [changelog](missing.md).\n",
        "guide.md": "# Guide\n\nBack to the [home](index.md).\n",
    }
    root = _scratch(tmp_path, pages=broken)
    result = _build(root)
    assert result.returncode != 0, (
        "mkdocs --strict passed with a link to a page that does not exist -- the gate protects nothing\n"
        + result.stdout
        + result.stderr
    )
    combined = result.stdout + result.stderr
    assert "missing.md" in combined, combined[-800:]
    assert not (root / "site" / "changelog").exists()


def test_the_same_build_is_green_once_the_link_exists(tmp_path: Path) -> None:
    """The green half: identical tree, target present, so the red above is about the link."""
    root = _scratch(tmp_path, pages=PAGES)
    if not (root / "docs" / "changelog.md").exists():
        (root / "docs" / "changelog.md").write_text("# Changelog\n", encoding="utf-8")
    (root / "docs" / "index.md").write_text(
        "# Home\n\nSee the [guide](guide.md) and the [changelog](changelog.md).\n", encoding="utf-8"
    )
    result = _build(root)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (root / "site" / "changelog" / "index.html").is_file()


def test_the_projects_own_config_declares_the_mechanism() -> None:
    """The fixture proves mkdocs' behaviour; this proves the project asks for it.

    Read as YAML, not as a line scan: `not_found: warn` under a `--strict` build is the pair that makes a
    broken link an error, and either half alone would not.
    """
    text = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    assert "not_found: warn" in text, "the link validation setting the gate depends on is gone"
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "mkdocs build --strict" in ci, "CI no longer runs the strict build this gate is about"


def test_the_control_a_missing_page_named_in_nav_is_reported(tmp_path: Path) -> None:
    """A nav entry with no file behind it must be visible too, not just an in-page link."""
    root = _scratch(tmp_path, pages=PAGES)
    config = (
        (root / "mkdocs.yml")
        .read_text(encoding="utf-8")
        .replace("  - Guide: guide.md\n", "  - Guide: guide.md\n  - Ghost: ghost.md\n")
    )
    assert config != (root / "mkdocs.yml").read_text(encoding="utf-8")
    (root / "mkdocs.yml").write_text(config, encoding="utf-8")
    result = _build(root)
    assert result.returncode != 0, result.stdout + result.stderr
    assert "ghost.md" in result.stdout + result.stderr


def test_mkdocs_module_is_the_one_ci_invokes(tmp_path: Path) -> None:
    """`python -m mkdocs` must be a real entry point here, or every probe above is theatre.

    The module form is what CI runs and what this file shells out, so the standalone binary being absent
    or present is not what is under test.
    """
    result = subprocess.run(
        [sys.executable, "-m", "mkdocs", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip(), "mkdocs --version printed nothing"
