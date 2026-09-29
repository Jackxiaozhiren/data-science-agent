"""`dsa --help` is shipped documentation, so its own claims have to hold.

The root help described ``mcp`` as ``MCP (§32): dsa mcp tools``; that exact form exits with
``dsa: error: unrecognized arguments: tools`` (measured rc 2, before the help text was
corrected). Nothing read the help strings, so the CLI instructed the user to type a command
the parser rejects.

Scope of what this can check without dispatching anything: only the *subcommand and option
names* the help advertises. Argument-form validation cannot be done here -- appending
``--help`` makes argparse exit before it reports an unrecognised positional, so the trick that
keeps write-producing subcommands (``demo``, ``analyze``, ``benchmark``) from executing also
blinds the check to the exact defect. A ``build_parser()`` seam is the prerequisite, recorded
as an uplift item rather than worked around.
"""

from __future__ import annotations

import re
import shutil
import subprocess

import pytest

_ROOT_HELP = "root"


def _run(argv: list[str]) -> subprocess.CompletedProcess[str]:
    exe = shutil.which("dsa")
    if exe is None:  # pragma: no cover - the console script is the surface under test
        pytest.skip("dsa console script not on PATH")
    return subprocess.run(  # noqa: S603 - fixed argv, no shell, help-only invocation
        [exe, *argv], capture_output=True, text=True, check=False
    )


def _root_help() -> str:
    proc = _run(["--help"])
    assert proc.returncode == 0 and proc.stdout, "dsa --help failed or produced nothing"
    return proc.stdout


def _declared_subcommands(help_text: str) -> set[str]:
    block = re.search(r"\{([a-z0-9,\-]+)\}", help_text)
    assert block, "no subcommand choice list found in the help, so nothing is being checked"
    return set(block.group(1).split(","))


def test_every_advertised_subcommand_is_declared() -> None:
    text = _root_help()
    declared = _declared_subcommands(text)
    mentioned = set(re.findall(r"\bdsa\s+([a-z][a-z0-9-]+)", text))
    assert mentioned, "the help names no `dsa <command>` form, so this test checks nothing"
    phantom = sorted(mentioned - declared)
    assert not phantom, f"--help advertises commands the parser has no subparser for: {phantom}"

    # Negative control: the check must be capable of failing.
    assert "mcp-tools" not in declared
    assert not {"nope-subcommand"} <= declared, "the declared set stopped discriminating"

    # Option forms are not covered: no `dsa <sub> --flag` string appears in the root help
    # today, so an assertion over them would have an empty denominator and pass forever.
    # Measured: re.findall(r"\bdsa\s+([a-z][a-z0-9-]+)\s+(--[a-z][a-z0-9-]*)", text) == [].
