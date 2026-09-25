"""Lane L1 guard: the test session must exercise workspace source, not `_vendor`.

`conftest.py` inserts the workspace `src` dirs and then demotes
`src/data_science_agent/_vendor` to the end of `sys.path`, because importing
`data_science_agent` -- which the published wheel relies on -- puts `_vendor` at
`sys.path[0]`. The demotion is wrapped in `except Exception: pass`, so if it ever
stopped working the suite would run against the vendored mirror while coverage,
which omits `*/_vendor/*`, reported nothing. Nothing pinned that, so a broken
shim would have been silent.
"""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

_PROBE = "import dsa_agent; print(dsa_agent.__file__)"


def _resolve_in_fresh_interpreter(*, with_demotion: bool) -> str:
    """Import dsa_agent the way a test session does, with or without the demotion."""
    script = (
        "import sys\n"
        f"sys.path.insert(0, {str(REPO / 'packages/agent/src')!r})\n"
        f"sys.path.insert(0, {str(REPO / 'src')!r})\n"
        "import data_science_agent\n"  # the wheel's bootstrap: adds _vendor first
    )
    if with_demotion:
        script += (
            f"_v = {str(REPO / 'src/data_science_agent/_vendor')!r}\n"
            "while _v in sys.path:\n"
            "    sys.path.remove(_v)\n"
            "sys.path.append(_v)\n"
        )
    script += "\nimport dsa_agent\nprint(dsa_agent.__file__)"
    out = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=str(REPO),
        check=True,
    )
    return out.stdout.strip()


def test_shim_failure_state_resolves_to_the_vendored_copy() -> None:
    """Negative control: proves the guard below is not vacuous.

    Without the demotion the same import resolves inside `_vendor`, so the
    assertion in the next test is capable of failing.
    """
    resolved = _resolve_in_fresh_interpreter(with_demotion=False)
    assert "_vendor" in resolved, (
        "expected the un-demoted path to load the vendored mirror; if this changed, "
        "the demotion guard below is testing nothing and both tests need rethinking"
    )


def test_demoted_path_resolves_to_workspace_source() -> None:
    resolved = _resolve_in_fresh_interpreter(with_demotion=True)
    assert "_vendor" not in resolved, f"dsa_agent loaded from the vendored mirror: {resolved}"
    assert Path(resolved).is_relative_to(REPO / "packages/agent/src"), resolved


def test_in_session_imports_are_not_vendored() -> None:
    """What the suite actually does right now, under the real conftest.py."""
    import dsa_agent

    assert "_vendor" not in dsa_agent.__file__, dsa_agent.__file__
