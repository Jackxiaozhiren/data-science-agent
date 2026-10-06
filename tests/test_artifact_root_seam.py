"""§122, D-L4-07 and D-L4-09: one artifact root, chosen by the process -- not by the module, and
not by the tool argument.

Measured on this tree before the change, by resolving the shipped expression
`Path(__file__).resolve().parents[4] / "artifacts"` for every layout the project ships:

    source agent   -> <root>/artifacts            (packages/agent/src/dsa_agent/report.py)
    source tools   -> <root>/packages/artifacts    (packages/tools/src/dsa_tools/tools/*.py)
    vendored agent -> <root>/artifacts
    vendored tools -> <root>/src/artifacts
    installed wheel-> <venv>/lib/python3.12/site-packages/artifacts

Three of those exist on this machine as real directories holding real output -- 166,980 entries
under `artifacts/`, 26,250 under `packages/artifacts/`, 6,435 under `src/artifacts/` -- which is
why `.gitignore` lines 20-22 list all three spellings: the split was noticed and ignored rather
than fixed. Meanwhile both readers resolve the same logical directory differently:
`dsa_mcp/resources.py` uses `Path(f"artifacts/reports/{run_id}/report.md")` (working-directory
relative) and the time-series plugin uses `Path("artifacts") / "charts"`. So a run started in any
directory that is not the repo root writes a report the MCP server can never find, and an installed
wheel writes into its own library tree.

Red on arrival: `dsa_datasets.artifact_paths` does not exist yet, and every site test below is asserted
against the shipped files with a parser rather than a grep.
"""

from __future__ import annotations

import ast
import asyncio
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ENV_ROOT = "DSA_ARTIFACT_ROOT"

WRITERS = (
    ROOT / "packages/agent/src/dsa_agent/report.py",
    ROOT / "packages/agent/src/dsa_agent/graph.py",
    ROOT / "packages/tools/src/dsa_tools/tools/create_chart.py",
    ROOT / "packages/tools/src/dsa_tools/tools/feature_importance.py",
    ROOT / "packages/tools/src/dsa_tools/tools/generate_report.py",
    ROOT / "packages/tools/src/dsa_tools/tools/save_artifact.py",
)
READERS = (
    ROOT / "packages/mcp/src/dsa_mcp/resources.py",
    ROOT / "plugins/dsa-time-series/src/dsa_time_series/plugin.py",
)
SITES = WRITERS + READERS
RESOLVER = ROOT / "packages/datasets/src/dsa_datasets/artifact_paths.py"


def _layout_roots() -> dict[str, Path]:
    """The old rule, recomputed here so the tests can say what it would have produced."""
    layouts = {
        "source agent": ROOT / "packages/agent/src/dsa_agent/report.py",
        "source tools": ROOT / "packages/tools/src/dsa_tools/tools/save_artifact.py",
        "vendored agent": ROOT / "src/data_science_agent/_vendor/dsa_agent/report.py",
        "vendored tools": ROOT / "src/data_science_agent/_vendor/dsa_tools/tools/save_artifact.py",
    }
    return {name: path.parents[4] / "artifacts" for name, path in layouts.items()}


def _roots_the_old_rule_picked(source: str) -> list[str]:
    """Expressions of the shape `<something>.parents[N]` in one module, found by parsing."""
    offenders: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute):
            if node.value.attr == "parents":
                offenders.append(ast.unparse(node))
    return offenders


def _artifact_literals(source: str) -> list[str]:
    """`Path("artifacts")` / `Path(f"artifacts/...")` -- a hand-rolled root written inline."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = getattr(func, "id", None) or getattr(func, "attr", None)
        if name not in {"Path", "PurePath"} or not node.args:
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            head = first.value
        elif isinstance(first, ast.JoinedStr) and first.values:
            head = getattr(first.values[0], "value", "")
        else:
            continue
        if isinstance(head, str) and head.split("/")[0] == "artifacts":
            found.append(ast.unparse(node))
    return found


def _calls_artifact_root(source: str) -> int:
    return sum(
        1
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and (getattr(node.func, "id", None) or getattr(node.func, "attr", None)) == "artifact_root"
    )


def test_the_resolver_is_one_module_with_one_rule() -> None:
    assert RESOLVER.is_file(), "dsa_datasets.artifact_paths does not exist"
    from dsa_datasets.artifact_paths import ENV_ROOT as resolver_env, artifact_root

    assert resolver_env == ENV_ROOT, f"the switch is named {resolver_env!r}, not {ENV_ROOT!r}"
    assert callable(artifact_root)
    # The resolver itself must not be layout-dependent: no `__file__`, no `.parents[...]`.
    # Checked through the parser, because the module's own docstring quotes the old expression.
    source = RESOLVER.read_text(encoding="utf-8")
    assert not _roots_the_old_rule_picked(source), _roots_the_old_rule_picked(source)
    names = [
        node.id
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Name) and node.id == "__file__"
    ]
    assert not names, "the resolver reads its own module path again"


def test_no_site_derives_the_artifact_root_from_its_own_module_path() -> None:
    offenders: list[str] = []
    for path in SITES:
        source = path.read_text(encoding="utf-8")
        for hit in _roots_the_old_rule_picked(source):
            offenders.append(f"{path.relative_to(ROOT)}: {hit}")
        for hit in _artifact_literals(source):
            offenders.append(f"{path.relative_to(ROOT)}: inline root {hit}")
    assert not offenders, "\n".join(offenders)


def test_every_site_asks_the_resolver() -> None:
    """The complement of the guard above: deleting the defect without wiring a rule would be green there."""
    silent = [
        str(p.relative_to(ROOT))
        for p in SITES
        if _calls_artifact_root(p.read_text(encoding="utf-8")) == 0
    ]
    assert not silent, f"sites that name no artifact root at all: {silent}"
    assert len(SITES) == 8, len(SITES)


def test_the_control_both_shapes_are_reported_and_the_fixed_shape_is_not(tmp_path: Path) -> None:
    module_path = 'p = Path(__file__).resolve().parents[4] / "artifacts" / run_id\n'
    inline = 'p = Path("artifacts") / "charts"\n'
    fstring = 'p = Path(f"artifacts/reports/{run_id}/report.md")\n'
    good = "p = artifact_root(run_id)\n"
    for shape in (module_path, inline, fstring):
        assert _roots_the_old_rule_picked(shape) or _artifact_literals(shape), (
            f"the scan is blind to {shape.strip()!r} -- the guard is decorative"
        )
    assert not _roots_the_old_rule_picked(good) and not _artifact_literals(good)
    assert _calls_artifact_root(good) == 1
    # The `__file__` guard is an AST scan, so it catches a real use and ignores prose about one.
    assert [
        n.id
        for n in ast.walk(ast.parse(module_path))
        if isinstance(n, ast.Name) and n.id == "__file__"
    ]
    quoted = ast.parse('"""the old rule was Path(__file__).parents[4], which is why it moved."""\n')
    assert not [n.id for n in ast.walk(quoted) if isinstance(n, ast.Name) and n.id == "__file__"]
    # ... and it is the shipped files, not an empty list, that the real test passes on.
    assert len([p for p in SITES if p.is_file()]) == len(SITES), (
        "a site moved; the scan silently shrank"
    )


def test_importing_the_rule_does_not_pull_the_plotting_stack(tmp_path: Path) -> None:
    """Why the rule lives in `dsa_datasets` rather than `dsa_tools`, pinned as a number.

    Measured on this tree: `import dsa_tools` costs 2791 ms and loads matplotlib and sklearn behind
    its tool registry, while `dsa_agent.report` (294 ms) and `dsa_mcp.server` (420 ms) load neither.
    A rule those two must reach would have been a tenfold import cost for every `import dsa_agent`.
    """
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "import dsa_datasets.artifact_paths, sys; "
            "print('matplotlib' in sys.modules, 'sklearn' in sys.modules, 'dsa_tools' in sys.modules)",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "False False False", proc.stdout


def test_the_default_root_is_the_process_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dsa_datasets.artifact_paths import artifact_root

    monkeypatch.delenv(ENV_ROOT, raising=False)
    monkeypatch.chdir(tmp_path)
    assert artifact_root("charts") == tmp_path / "artifacts" / "charts"
    assert artifact_root() == tmp_path / "artifacts"


def test_the_environment_override_wins_over_the_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The two arms point at different directories, so a resolver that ignored the switch fails here."""
    from dsa_datasets.artifact_paths import artifact_root

    elsewhere = tmp_path / "elsewhere"
    (tmp_path / "cwd").mkdir()
    monkeypatch.chdir(tmp_path / "cwd")
    monkeypatch.setenv(ENV_ROOT, str(elsewhere))
    assert artifact_root("reports", "run-1") == elsewhere / "reports" / "run-1"
    assert not (tmp_path / "cwd" / "artifacts").exists()


def test_the_root_does_not_move_when_the_module_is_relocated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-L4-07's mechanism, tested directly: retarget the module's recorded location and write.

    Under the old rule this moved the whole artifact tree (reproduced before §122: pointing
    `dsa_tools.tools.save_artifact.__file__` at a fake `<venv>/lib/python3.12/site-packages/...`
    path made the writer create `/tmp/probe_tree/packages/artifacts/...`, i.e. the install layout
    chose where user output landed). Under the rule the process decides, so the file stays under
    the working directory.
    """
    from dsa_tools.tools.save_artifact import SaveArtifactInput, SaveArtifactTool
    import dsa_tools.tools.save_artifact as save_module

    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.delenv(ENV_ROOT, raising=False)
    monkeypatch.chdir(work)
    save_module.__file__ = str(
        tmp_path
        / "venv/lib/python3.12/site-packages/data_science_agent/_vendor/dsa_tools/tools/save_artifact.py"
    )
    out = asyncio.run(
        SaveArtifactTool().execute(
            SaveArtifactInput(run_id="run-layout", filename="note.txt", content="x", type="note")
        )
    )
    landed = Path(out.path).resolve()
    assert landed == work / "artifacts" / "run-layout" / "note.txt", landed
    assert not (tmp_path / "venv").exists(), "the install tree was written into again"


@pytest.mark.parametrize(
    "run_id",
    ["../../escaped", "nested/../../x", "..", "/absolute/escape", ""],
    ids=["dotdot-up", "nested-up", "parent", "absolute", "empty"],
)
def test_a_run_id_cannot_choose_a_directory_outside_the_artifact_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, run_id: str
) -> None:
    """D-L4-09: `run_id` is tool input, and it was concatenated straight into the write path.

    The filename is validated (`..`, `/`, `\\` refused) but the run id was not, and the
    `relative_to(root)` check below it cannot help -- `root` itself already contains the escape.
    Reproduced before the fix: run_id `../../escaped` wrote
    `<tmp>/probe_tree/escaped/note.txt`, two levels above the artifact root it claimed to be under.
    """
    from dsa_tools.errors import ToolExecutionError
    from dsa_tools.tools.save_artifact import SaveArtifactInput, SaveArtifactTool

    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.delenv(ENV_ROOT, raising=False)
    monkeypatch.chdir(work)
    with pytest.raises((ToolExecutionError, ValueError)):
        asyncio.run(
            SaveArtifactTool().execute(
                SaveArtifactInput(run_id=run_id, filename="note.txt", content="x", type="note")
            )
        )
    # Nothing was created anywhere: the refusal has to come before the mkdir, not after the write.
    assert sorted(p.name for p in tmp_path.iterdir()) == ["work"], sorted(tmp_path.iterdir())
    assert not (work / "artifacts").exists(), "the root was created before the run id was checked"
    assert not Path("/absolute/escape").exists()


def test_the_writer_and_the_reader_resolve_the_same_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The defect this section exists for: the MCP reader could not find what the agent wrote."""
    from dsa_agent.report import write_report_artifacts
    from dsa_agent.state import AnalysisState
    from dsa_mcp.resources import read_resource

    store_root = tmp_path / "store"
    (tmp_path / "elsewhere-cwd").mkdir()
    monkeypatch.chdir(tmp_path / "elsewhere-cwd")
    monkeypatch.setenv(ENV_ROOT, str(store_root))
    run_id = f"run-{uuid.uuid4().hex[:10]}"
    state = AnalysisState(run_id=run_id, dataset_id="ds", user_query="which root?")
    paths = write_report_artifacts(state)
    written = Path(paths["markdown"])
    assert written == store_root / "reports" / run_id / "report.md", written

    # Positive arm: the reader reaches the writer's file even though cwd and root now differ.
    found = asyncio.run(read_resource(f"report://{run_id}"))
    assert not found.get("isError"), found
    assert found["text"] == written.read_text(encoding="utf-8")

    # Negative arm: the reader really consulted the filesystem, not an in-process cache.
    missing = asyncio.run(read_resource(f"report://{run_id}-nope"))
    assert missing.get("isError") and "not found" in missing["text"], missing


def test_the_three_roots_the_old_rule_produced_are_one_now() -> None:
    """The claim the section opens with, re-derived at test time rather than quoted from the ledger."""
    old = _layout_roots()
    assert len(set(old.values())) == 3, old
    from dsa_datasets.artifact_paths import artifact_root

    unified = {name: artifact_root("x") for name in old}
    assert len(set(unified.values())) == 1, unified
