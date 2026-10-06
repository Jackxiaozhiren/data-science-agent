"""§121, Phase 4 target 6: one discoverable command surface, and scripts that actually run.

Two things a contributor has to guess today: which command runs the whole gate set (the guides list
23 lines to copy-paste; CI runs them one step at a time), and whether a helper script can be executed
at all -- measured at the previous commit, six of the fifteen files under `scripts/` carry a `#!` line
and are not executable, while eight more have no shebang and are correctly not. `scripts/dev.sh` is in
the first group: a documented entry point that `./scripts/dev.sh` cannot start.

The runner is pinned to the same derived gate surface §120 built, so a gate added to `ci.yml` reddens
this file until the runner knows about it -- which is the point of having a runner instead of a second
list someone must remember to update.
"""

from __future__ import annotations

import importlib.util
import os
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_gates.sh"


def _gate_readers():
    """Load the CI readers from the sibling guard rather than restating them here."""
    path = ROOT / "tests" / "test_ci_gate_integrity.py"
    spec = importlib.util.spec_from_file_location("ci_gate_readers_for_runner", path)
    assert spec and spec.loader, f"cannot load {path}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _runner_gates(text: str) -> list[str]:
    """The quoted entries of the runner's GATES array, in order."""
    marker = "GATES=("
    assert marker in text, "the runner no longer declares a GATES array"
    body = text.split(marker, 1)[1]
    commands = []
    for line in body.split(")\n", 1)[0].splitlines():
        stripped = line.strip()
        if stripped.startswith('"') and stripped.endswith('"'):
            commands.append(stripped[1:-1])
    assert commands, "the GATES array parsed empty -- the reader broke"
    return commands


def test_a_gate_runner_exists_and_is_executable() -> None:
    assert RUNNER.is_file(), (
        "no scripts/run_gates.sh: the gate set is 23 lines to copy, not one command"
    )
    assert os.stat(RUNNER).st_mode & stat.S_IXUSR, "scripts/run_gates.sh is not executable"


def test_the_runner_covers_exactly_the_ci_gate_set() -> None:
    """A new gate in `ci.yml` has to appear here, or the runner lies about covering the gate set."""
    readers = _gate_readers()
    ci_text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    ci_gates = {
        readers._classify(readers._tokens(cmd))
        for _, cmd in readers._single_line_run_steps(ci_text)
    }
    ci_gates.discard(None)
    runner_gates = {
        readers._classify(readers._tokens(cmd))
        for cmd in _runner_gates(RUNNER.read_text(encoding="utf-8"))
    }
    runner_gates.discard(None)
    unclassified = [
        cmd
        for cmd in _runner_gates(RUNNER.read_text(encoding="utf-8"))
        if not readers._classify(readers._tokens(cmd))
    ]
    assert not unclassified, f"runner commands that are not a recognised gate: {unclassified}"
    assert runner_gates == ci_gates, (
        f"runner is missing {sorted(ci_gates - runner_gates)}, "
        f"runs gates CI does not {sorted(runner_gates - ci_gates)}"
    )


def test_scripts_with_a_shebang_are_executable() -> None:
    """RED before §121: six scripts say `#!/usr/bin/env ...` and cannot be started by name.

    The rule is one-way on purpose and states the other half too: a file with no shebang stays
    non-executable, so `chmod +x` cannot be used to make this green by blanket-applying it.
    """
    offenders: list[str] = []
    considered = 0
    for path in sorted((ROOT / "scripts").iterdir()):
        if path.suffix not in {".py", ".sh"} or not path.is_file():
            continue
        first = path.read_text(encoding="utf-8", errors="replace").splitlines()[:1]
        has_shebang = bool(first) and first[0].startswith("#!")
        executable = bool(os.stat(path).st_mode & stat.S_IXUSR)
        considered += 1
        if has_shebang and not executable:
            offenders.append(f"{path.name}: shebang, not executable")
        if executable and not has_shebang:
            offenders.append(f"{path.name}: executable, no shebang")
    assert considered >= 14, f"only {considered} scripts scanned -- the walk broke"
    assert not offenders, "\n".join(offenders)


def test_the_control_a_missing_runner_gate_is_reported(tmp_path: Path) -> None:
    """The comparison above must be able to fail on a dropped gate, not silently shrink."""
    text = RUNNER.read_text(encoding="utf-8")
    dropped = "\n".join(line for line in text.splitlines() if "audit_facts.py" not in line)
    assert dropped != text, "the fixture edit did not land -- this control proves nothing"
    readers = _gate_readers()
    keys = {readers._classify(readers._tokens(cmd)) for cmd in _runner_gates(dropped)}
    assert "ratchet" not in keys, (
        "dropping the ratchet line left it classified: the reader is guessing"
    )

    # ... and the path check must be able to fail on a moved script, not just pass on the real one.
    moved = text.replace("scripts/audit_facts.py", "scripts/audit_debt.py", 1)
    offenders = [
        token
        for cmd in _runner_gates(moved)
        for token in _path_tokens(cmd)
        if not (ROOT / token).exists()
    ]
    assert offenders == ["scripts/audit_debt.py"], offenders


def test_the_runner_lists_its_commands_without_running_anything() -> None:
    """`--list` must actually execute: a script whose main path silently exits would pass the text tests.

    §118's npm lesson generalises -- a gate that prints nothing and exits 0 is not green, it is absent.
    """
    proc = subprocess.run(
        ["bash", str(RUNNER), "--list"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    listed = proc.stdout.strip().splitlines()
    assert len(listed) == len(_runner_gates(RUNNER.read_text(encoding="utf-8"))), (
        f"--list printed {len(listed)} lines, the array holds "
        f"{len(_runner_gates(RUNNER.read_text(encoding='utf-8')))}"
    )
    assert "audit_facts.py" in "\n".join(listed), listed[:3]
    assert "GATES ran" not in proc.stdout, "--list executed the gates"


def test_the_docs_point_at_the_runner() -> None:
    """A command surface nobody can find is not a command surface."""
    for rel in ("CONTRIBUTING.md", "docs/contributing.md"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "scripts/run_gates.sh" in text, f"{rel} never mentions the runner"


def _path_tokens(command: str) -> list[str]:
    """Repository paths a command names, excluding the two kinds that cannot be checked statically.

    Absolute paths point outside the tree (CI's `/tmp` outputs), and the path after `test -f` is the
    artefact the same command creates (`generate_sbom.py && test -f release/sbom.json`), so requiring
    it to exist before the runner has run would be requiring the gate to have already passed.
    """
    out: list[str] = []
    skip_next = False
    # `token` as a name would trip S105 ("hardcoded password assigned to: token"), which is ruff
    # pattern-matching on the variable name rather than its meaning; `arg` says the same thing.
    for arg in command.split():
        if skip_next:
            skip_next = False
            continue
        if arg == "-f":
            skip_next = True
            continue
        if arg.startswith(("/", "-")) or "." not in arg or "*" in arg:
            continue
        if any(sep in arg for sep in ("=", ">", "<")):
            continue
        out.append(arg)
    return out


def test_every_runner_command_names_a_real_invocation() -> None:
    """The runner is never executed by CI, so a moved script would fail only on a contributor's machine.

    Each path the commands mention has to resolve in the tree; `scripts/run_gates.sh --list` is run
    for real above, which is what proves the array is read at all rather than parsed out of a file
    nothing calls.
    """
    commands = _runner_gates(RUNNER.read_text(encoding="utf-8"))
    offenders = []
    for cmd in commands:
        for token in _path_tokens(cmd):
            if not (ROOT / token).exists():
                offenders.append(f"{cmd[:44]}... -> missing {token!r}")
    assert not offenders, "\n".join(offenders)
