"""Lane L1 guard: a CI step must report the status of the gate it runs.

GitHub Actions runs a bare ``- run:`` line with ``bash --noprofile --norc -e``,
which enables errexit but *not* pipefail. A pipeline therefore reports the exit
status of its last command, so ``uv run python -m mkdocs build --strict 2>&1 |
tail -n 50`` stays green even when mkdocs aborts. Any step that pipes a gate has
to opt into pipefail explicitly.
"""

import re
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"

# `| tail`, `| head`, `| grep`, `| tee`, `| jq` -- the truncators used in this repo.
_PIPE = re.compile(r"\|\s*(?:tail|head|grep|tee|jq)\b")
_RUN = re.compile(r"^\s*- run:\s*(.+)$")
_BLOCK = re.compile(r"^\s*run:\s*\|\s*$")


def _single_line_run_steps(text: str) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    in_block = False
    for lineno, line in enumerate(text.splitlines(), 1):
        if _BLOCK.match(line):
            in_block = True
            continue
        if in_block:
            # A multi-line block carries its own `set -euo pipefail`; skip its body
            # until indentation drops back to the step level.
            if re.match(r"^      - ", line) or re.match(r"^        [a-z]+:", line):
                in_block = False
            else:
                continue
        match = _RUN.match(line)
        if match:
            out.append((lineno, match.group(1)))
    return out


def test_piped_ci_steps_declare_pipefail() -> None:
    offenders: list[str] = []
    checked = 0
    for wf in sorted(WORKFLOWS.glob("*.yml")):
        for lineno, cmd in _single_line_run_steps(wf.read_text(encoding="utf-8")):
            checked += 1
            if _PIPE.search(cmd) and "pipefail" not in cmd:
                offenders.append(f"{wf.name}:{lineno}: {cmd[:90]}")
    assert checked > 0, "no single-line run steps found -- the parser broke"
    assert not offenders, "piped steps report tail's exit code, not the gate's:\n" + "\n".join(
        offenders
    )


# (`ruff check` / `ruff format --check`) lists apps/jupyter, so the surface is
# style-checked and never type-checked; mypy itself reports the dsa_jupyter.*
# override in pyproject.toml as an unused section on every CI run.
def test_mypy_steps_type_check_every_shipped_tree() -> None:
    missing: list[str] = []
    seen = 0
    for name in ("ci.yml", "publish.yml"):
        for _, cmd in _single_line_run_steps((WORKFLOWS / name).read_text(encoding="utf-8")):
            if "mypy" not in cmd:
                continue
            seen += 1
            if "apps/jupyter" not in cmd:
                missing.append(name)
    assert seen > 0, "no mypy step found in ci.yml or publish.yml -- the parser broke"
    assert not missing, f"mypy omits apps/jupyter in: {', '.join(missing)}"


# `--strict` escalates warnings to errors, but `validation.links.not_found:
# ignore` stops mkdocs emitting the warning in the first place, so the docs gate
# CI runs (and CONTRIBUTING.md's Security line mandates) cannot fail on a broken link.
def test_mkdocs_strict_has_a_link_signal() -> None:
    cfg = Path(__file__).resolve().parents[1] / "mkdocs.yml"
    ignore_only = all(
        mode == "ignore"
        for key, mode in _link_validation_modes(cfg.read_text(encoding="utf-8")).items()
        if key == "not_found"
    )
    modes = _link_validation_modes(cfg.read_text(encoding="utf-8"))
    assert "not_found" in modes, f"no validation.links.not_found key in {cfg}"
    assert not ignore_only, (
        f"not_found is set to ignore, so --strict has nothing to escalate: {modes}"
    )


def _link_validation_modes(text: str) -> dict[str, str]:
    """Read the two `validation.links` sub-modes without needing a YAML parser."""
    modes: dict[str, str] = {}
    in_links = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "links:":
            in_links = True
            continue
        if in_links:
            if ":" not in stripped or stripped.startswith("#"):
                break
            key, _, value = stripped.partition(":")
            if key.strip() in {"not_found", "absolute_links"}:
                modes[key.strip()] = value.strip()
            else:
                break
    return modes


ROOT = Path(__file__).resolve().parents[1]

# The contributor guides restate CI's gate commands by hand, and a hand-copied
# list drifts silently. Measured before this guard existed: `CONTRIBUTING.md` and
# `docs/contributing.md` both omit `scripts` from the ruff lists, `CONTRIBUTING.md`
# omits `src apps/jupyter` from mypy, and neither runs the `--cov` floor or the
# debt ratchet CI enforces -- so a reader who follows a guide to the letter sees
# green locally and red remotely on a check they were told to run.
#
# Scope pin: this guards only the two documents that present themselves as the
# pre-PR gate. The shorter "Development" / "Quick Quality" blocks in README.md and
# docs/README.md are tasters, not gates -- they may run a subset, and are
# deliberately not compared here.
GUIDES = ("CONTRIBUTING.md", "docs/contributing.md")

# `uv run python -m` is invocation scaffolding, not part of the gate.
_SCAFFOLD = frozenset({"uv", "run", "python", "-m"})


def _classify(tokens: set[str]) -> str | None:
    """Name the gate a token stream implements, or None if it is not one we guard."""
    if "ruff" in tokens and "format" in tokens and "--check" in tokens:
        return "ruff-format"
    if "ruff" in tokens and "check" in tokens:
        return "ruff-check"
    if "mypy" in tokens:
        return "mypy"
    if "pytest" in tokens:
        return "pytest"
    if any(tok.endswith("audit_facts.py") for tok in tokens):
        return "ratchet"
    return None


def _tokens(cmd: str) -> set[str]:
    """Command tokens, with inline comments and CI's log-piping removed."""
    body = cmd.split("#", 1)[0].split("|", 1)[0]
    return set(body.split()) - _SCAFFOLD


def _bash_lines(text: str) -> list[str]:
    """Lines inside fenced code blocks -- the copy-paste surface a reader uses."""
    out: list[str] = []
    inside = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            inside = not inside
            continue
        if inside and line.strip():
            out.append(line.strip())
    return out


def _ci_gates() -> dict[str, set[str]]:
    """Each guarded gate as the CI workflow actually spells it."""
    gates: dict[str, set[str]] = {}
    for _, cmd in _single_line_run_steps((WORKFLOWS / "ci.yml").read_text(encoding="utf-8")):
        key = _classify(_tokens(cmd))
        if key and key not in gates:
            gates[key] = _tokens(cmd)
    return gates


def _guide_gates(path: Path) -> dict[str, set[str]]:
    gates: dict[str, set[str]] = {}
    for line in _bash_lines(path.read_text(encoding="utf-8")):
        key = _classify(_tokens(line))
        if key and key not in gates:
            gates[key] = _tokens(line)
    return gates


def test_contributing_guides_mirror_the_ci_gates() -> None:
    expected = _ci_gates()
    assert len(expected) == 5, f"expected 5 guarded gates in ci.yml, parsed {sorted(expected)}"
    offenders: list[str] = []
    for rel in GUIDES:
        guide = _guide_gates(ROOT / rel)
        for key, ci_tokens in sorted(expected.items()):
            if key not in guide:
                offenders.append(f"{rel}: never runs the {key} gate CI runs ({sorted(ci_tokens)})")
            elif guide[key] != ci_tokens:
                missing = sorted(ci_tokens - guide[key])
                extra = sorted(guide[key] - ci_tokens)
                offenders.append(
                    f"{rel}: {key} differs from ci.yml -- missing {missing}, extra {extra}"
                )
    assert not offenders, (
        "guide commands must match the CI gate they tell you to run:\n" + "\n".join(offenders)
    )


def test_gate_comparison_detects_a_shortened_list() -> None:
    """Negative control: a guide that drops a path must be reported, not skipped."""
    ci = _tokens("uv run mypy packages apps/api src apps/jupyter --ignore-missing-imports")
    narrow = _tokens("uv run mypy packages apps/api --ignore-missing-imports")
    assert _classify(narrow) == "mypy", "the shortened line must still classify as the same gate"
    assert ci != narrow, "a path dropped from the list has to be visible to the comparison"
    assert ci - narrow == {"src", "apps/jupyter"} and narrow - ci == set()
