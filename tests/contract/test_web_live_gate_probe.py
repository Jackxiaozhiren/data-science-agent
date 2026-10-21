"""The live-gate runner's browser preflight must never guess a reason it did not observe.

`scripts/run_web_live_gates.sh` refuses before booting anything, and it names a different remedy per cause --
"install the browser" versus "install the package". Those are not interchangeable, and the version that collapsed
them reddened its own gate: a probe asking from the repository root could not resolve `playwright` in CI (which
installs `apps/web` and `apps/vscode` and never a root `node_modules`) and reported the browser as missing while it
was present. The probe is now a file beside the instruments, so Node resolves it the way it resolves them.

Asserted without depending on whether this machine has a browser: CI's job order means Chromium may or may not be
installed where pytest runs, so these tests pin the probe's vocabulary and the states they can force -- an emptied
browser directory, and a copy of the probe outside the package.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "apps" / "web" / "scripts" / "browser-state.mjs"
STATES = {"INSTALLED", "MISSING", "UNRESOLVABLE"}


def _answer(cwd: Path, script: Path = PROBE, extra_env: dict[str, str] | None = None) -> str:
    env = dict(os.environ, **(extra_env or {}))
    proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
        ["node", str(script)], cwd=str(cwd), capture_output=True, text=True, env=env
    )
    assert proc.returncode == 0, f"the probe exited {proc.returncode}: {proc.stderr.strip()[:200]}"
    lines = [line for line in proc.stdout.strip().splitlines() if line]
    assert len(lines) == 1, f"the runner branches on one line of output, got {lines}"
    return lines[0]


def test_the_probe_answers_with_one_of_three_words() -> None:
    """One line, one known state -- the caller branches on that text, so anything else silences the gate."""
    assert PROBE.exists(), f"{PROBE} is gone, so the live-gate preflight has nothing to call"
    answer = _answer(ROOT)
    assert answer in STATES, f"the probe printed {answer!r}, which the runner has no branch for"


def test_a_missing_browser_is_named_as_a_missing_browser(tmp_path: Path) -> None:
    """Empty the browser cache and the answer must become MISSING, not UNRESOLVABLE and not INSTALLED.

    Skipped where no browser exists at all: there the two states cannot be told apart, and an assertion that cannot
    fail for the condition it names is not a guard.
    """
    if _answer(ROOT) != "INSTALLED":
        import pytest

        pytest.skip(
            "no chromium browser installed here, so MISSING is indistinguishable from the norm"
        )
    forced = _answer(ROOT, extra_env={"PLAYWRIGHT_BROWSERS_PATH": str(tmp_path)})
    assert forced == "MISSING", (
        f"with the browser cache emptied the probe said {forced!r}; the runner would then name the wrong remedy "
        "for the same condition -- which is how this gate first reddened CI"
    )


def test_resolution_follows_the_file_and_not_the_cwd(tmp_path: Path) -> None:
    """Ask from outside the package and it must say UNRESOLVABLE: the property that ends the cwd dependence.

    The previous form was `cd apps/web && node -e ...`, correct only while every future caller remembered the `cd`.
    A file inside the package resolves its own specifier, so the disagreement between a probe and the instruments it
    guards cannot recur.
    """
    elsewhere = tmp_path / "outside-the-package"
    elsewhere.mkdir()
    copied = elsewhere / "browser-state.mjs"
    shutil.copyfile(PROBE, copied)
    assert _answer(elsewhere, copied) == "UNRESOLVABLE", (
        "a copy outside apps/web still resolved playwright, so the three answers the runner branches on do not "
        "separate a missing package from a missing browser"
    )
