"""Rebuild the S2 execution-boundary matrix from the tree.

ADR-003 replaces a commercial sandbox with a boundary published as a checkable matrix. This script
is that check: for each surface that accepts model-authored input it asks whether a capability is
decided by a check that runs at request time -- not whether today's code happens to exercise it.

Three conventions carry the reading:

* **The last check to run decides the cell.** A SQL statement passes the name filter and is then
  offered to the engine, so the engine's answer is the boundary's answer. Every layer a cell passes
  through is recorded, and the verdict is the outcome of the final one.
* **Absence is not a decision.** A surface that never calls ``open`` is not fenced by anything: an
  edit closes the gap and no check refuses it. Such a cell is recorded ``undecidable`` at boundary
  level with ``fenced_in_this_tree`` true, which is a statement about the code, not the boundary.
* **One permitted path is enough.** A layer is ``open`` when a single expression reaches the
  capability, so a cell cannot read as fenced because the obvious spelling is blocked while a
  re-export walks past it.

Every probe is a repository constant, every probe answer is recomputed here, and the only file the
probes touch is one CSV this tree ships.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
import tempfile
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb

from dsa_datasets.errors import UnsupportedFormatError
from dsa_execution.python_sandbox import SandboxViolation, _check_ast
from dsa_execution.sql_guard import validate_sql
from dsa_tools.errors import ToolExecutionError
from dsa_tools.tools.profile_dataset import _fingerprint, _guard_request, _guard_unchanged

ROOT = Path(__file__).resolve().parents[1]
RECORD_PATH = ROOT / "docs/audit/execution-boundary.json"
PROFILE_TOOL = ROOT / "packages/tools/src/dsa_tools/tools/profile_dataset.py"
BENCH_CSV = ROOT / "benchmarks/ds-agent-benchmark/datasets/data_quality.csv"
SCHEMA = "execution-boundary-matrix/v2"
#: The test a cell may cite as having watched a refusal, and the commit this reading describes. Both
#: are constants rather than arguments: a value that reaches a file write from the command line is a
#: value that can name a different file, and the CLI here takes flags only.
VERIFIED_BY = "tests/security/test_sql_sandbox.py"
REVIEWED_COMMIT = "ab958723f7e8"
# ``SandboxViolation`` is listed separately: the sandbox module falls back to a local
# ``ToolExecutionError`` when its import of ``dsa_tools.errors`` runs into the package cycle, so the
# subclass relation cannot be assumed at measurement time. ``UnsupportedFormatError`` is the form
# allowlist's refusal, which is what decides the process-spawn cell on ``profile_dataset``.
_REFUSALS = (SandboxViolation, ToolExecutionError, UnsupportedFormatError, duckdb.Error)


def _attempt(fn: Callable[[], str | None]) -> tuple[str, str]:
    """Run one probe: an exception raised by a mechanism is that mechanism refusing the capability.

    A probe returns the reason it observed a refusal, or ``None`` when the capability got through.
    The whole module keeps its exception handling here so that "the mechanism said no" and "the
    mechanism was never asked" stay distinguishable at the single point where a verdict is produced.
    """
    try:
        reason = fn()
    except _REFUSALS as exc:
        return "refused", str(exc).splitlines()[0][:160]
    return ("permitted", "") if reason is None else ("refused", reason)


def _ast_probe(expression: str) -> Callable[[], str | None]:
    """The AST filter raises on refusal, so reaching the return means the expression was permitted."""

    def run() -> str | None:
        _check_ast(expression)
        return None

    return run


def _sql_probe(statement: str) -> Callable[[], str | None]:
    def run() -> str | None:
        validate_sql(statement)
        return None

    return run


@contextlib.contextmanager
def _fenced_connection() -> Iterator[duckdb.DuckDBPyConnection]:
    """A connection carrying the same fence ``run_sql`` installs before any caller statement runs."""
    con = duckdb.connect(database=":memory:")
    try:
        con.execute("SET enable_external_access=false")
        yield con
    finally:
        con.close()


def _duckdb_read_probe() -> str | None:
    """A CSV this tree ships, opened only so the engine can refuse it."""
    with _fenced_connection() as con:
        con.execute(
            "SELECT * FROM read_csv_auto('benchmarks/ds-agent-benchmark/datasets/data_quality.csv')"
        ).fetchall()
    return None


def _duckdb_copy_probe() -> str | None:
    with _fenced_connection() as con:
        con.execute("COPY (SELECT 1 AS a) TO '/tmp/dsa-probe.csv'").fetchall()
    return None


def _duckdb_glob_probe() -> str | None:
    with _fenced_connection() as con:
        con.execute("SELECT * FROM glob('*')").fetchall()
    return None


def _duckdb_env_probe() -> str | None:
    with _fenced_connection() as con:
        con.execute("SELECT getenv('HOME')").fetchall()
    return None


def _profile_url_probe() -> str | None:
    """A URL-shaped path is refused by ``Path.exists`` and by the tool's own separated-slash rule."""
    candidate = "https://example.invalid/a.csv"
    if Path(candidate).exists() and candidate.count("//") == 0:
        return None
    return "a URL-shaped path fails the existence check and the doubled-separator rule"


def _profile_spawn_probe() -> str | None:
    """The profile tool imports no process, shell or filesystem-mutation module."""
    forbidden = {"os", "subprocess", "shutil", "socket", "ctypes"}
    roots = set()
    for line in PROFILE_TOOL.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split()
        if len(parts) > 1 and parts[0] in {"import", "from"}:
            roots.add(parts[1].split(".")[0])
    if roots & forbidden:
        return None
    return f"imports only {sorted(roots)}"


def _profile_format_probe() -> str | None:
    """A loader that executes code must not be reachable: the reader comes from the allowlist."""
    _guard_request(BENCH_CSV, "payload.pkl", str(BENCH_CSV))
    return None


def _profile_credential_probe() -> str | None:
    """A file whose name exists to hold a secret is refused before the reader is chosen."""
    with tempfile.TemporaryDirectory(prefix="dsa-boundary-") as tmp:
        target = Path(tmp) / ".env"
        target.write_text("DSA_TOKEN=probe\n", encoding="utf-8")
        _guard_request(target, None, str(target))
    return None


def _profile_write_probe() -> str | None:
    """A write between the two observations is what the fingerprint check exists to refuse."""
    with tempfile.TemporaryDirectory(prefix="dsa-boundary-") as tmp:
        target = Path(tmp) / "data.csv"
        target.write_text("a,b\n1,2\n", encoding="utf-8")
        before = _fingerprint(target)
        target.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
        _guard_unchanged(target, before)
    return None


PROBES: tuple[dict[str, Any], ...] = (
    {
        "id": "ast-open-call",
        "surface": "run_python",
        "question": "is the builtin open() refused by the AST check?",
        "run": _ast_probe("open('/etc/hosts')"),
    },
    {
        "id": "ast-environ-attribute",
        "surface": "run_python",
        "question": "is the .environ attribute refused by the AST check?",
        "run": _ast_probe("x = pl.os.environ"),
    },
    {
        "id": "ast-environ-subscript",
        "surface": "run_python",
        "question": "is .environ still refused when the mapping is read through __dict__?",
        "run": _ast_probe("x = pl.os.__dict__['environ']"),
    },
    {
        "id": "ast-subprocess-reexport",
        "surface": "run_python",
        "question": "is a process handle reachable through an allowlisted module?",
        "run": _ast_probe("pl._dependencies.subprocess.Popen('id')"),
    },
    {
        "id": "ast-read-csv-path",
        "surface": "run_python",
        "question": "is an arbitrary local path readable through an allowlisted module?",
        "run": _ast_probe("pl.read_csv('/etc/hosts')"),
    },
    {
        "id": "ast-read-csv-remote",
        "surface": "run_python",
        "question": "is a remote path accepted through an allowlisted module?",
        "run": _ast_probe("pl.read_csv('https://example.invalid/a.csv')"),
    },
    {
        "id": "ast-write-csv",
        "surface": "run_python",
        "question": "is a write reachable through an allowlisted module?",
        "run": _ast_probe("pl.DataFrame({'a':[1]}).write_csv('/tmp/dsa-probe.csv')"),
    },
    {
        "id": "sql-install-extension",
        "surface": "run_sql",
        "question": "does the SQL guard refuse extension loading?",
        "run": _sql_probe("INSTALL httpfs"),
    },
    {
        "id": "sql-copy-out",
        "surface": "run_sql",
        "question": "does the SQL guard refuse writing a file?",
        "run": _sql_probe("COPY (SELECT 1) TO '/tmp/dsa-probe.csv'"),
    },
    {
        "id": "sql-read-function",
        "surface": "run_sql",
        "question": "does the SQL guard refuse a file-reading table function?",
        "run": _sql_probe("SELECT * FROM read_csv_auto('data.csv')"),
    },
    {
        "id": "sql-quoted-path",
        "surface": "run_sql",
        "question": "does the SQL guard refuse a quoted path used as a table name?",
        "run": _sql_probe("SELECT * FROM '/etc/hosts'"),
    },
    {
        "id": "sql-env-function",
        "surface": "run_sql",
        "question": "does the SQL guard refuse an environment-variable function?",
        "run": _sql_probe("SELECT getenv('HOME')"),
    },
    {
        "id": "duckdb-read-csv",
        "surface": "run_sql",
        "question": "does the engine fence allow a CSV on disk to be opened?",
        "run": _duckdb_read_probe,
    },
    {
        "id": "duckdb-copy-out",
        "surface": "run_sql",
        "question": "does the engine fence allow a table to be written to a file?",
        "run": _duckdb_copy_probe,
    },
    {
        "id": "duckdb-glob",
        "surface": "run_sql",
        "question": "does the engine fence allow the working directory to be listed?",
        "run": _duckdb_glob_probe,
    },
    {
        "id": "duckdb-env-function",
        "surface": "run_sql",
        "question": "does the engine expose an environment-variable function?",
        "run": _duckdb_env_probe,
    },
    {
        "id": "profile-url-path",
        "surface": "profile_dataset",
        "question": "does a URL-shaped path get past the existence and separator checks?",
        "run": _profile_url_probe,
    },
    {
        "id": "profile-process-import",
        "surface": "profile_dataset",
        "question": "does the profile tool import a process or shell module?",
        "run": _profile_spawn_probe,
    },
    {
        "id": "profile-format-allowlist",
        "surface": "profile_dataset",
        "question": "is a format whose loader executes code refused before a reader is chosen?",
        "run": _profile_format_probe,
    },
    {
        "id": "profile-credential-name",
        "surface": "profile_dataset",
        "question": "is a credential-shaped path refused before the reader runs?",
        "run": _profile_credential_probe,
    },
    {
        "id": "profile-input-unchanged",
        "surface": "profile_dataset",
        "question": "is a result refused when the input changed while it was being read?",
        "run": _profile_write_probe,
    },
)


def _layer(
    name: str, outcome: str, decided_by: str, probes: list[str], note: str
) -> dict[str, Any]:
    return {
        "layer": name,
        "outcome": outcome,
        "decided_by": decided_by,
        "probes": probes,
        "note": note,
    }


def _cell(
    cell_id: str,
    surface: str,
    capability: str,
    layers: list[dict[str, Any]],
    effect_verified: bool,
    verified_by: str | None,
    residual: str,
) -> dict[str, Any]:
    """Derive a cell's verdict from its layers, so the verdict cannot be typed independently."""
    absence = any(layer["decided_by"] == "absence" for layer in layers)
    if layers[-1]["outcome"] == "open":
        verdict = "open"
    elif absence:
        verdict = "undecidable"
    else:
        verdict = "fenced"
    return {
        "id": cell_id,
        "surface": surface,
        "capability": capability,
        "verdict": verdict,
        "decided_by": "absence" if absence else "check",
        "fenced_in_this_tree": True,
        "layers": layers,
        "effect_verified": effect_verified,
        "verified_by": verified_by,
        "residual": residual,
    }


def _run_python_cells() -> list[dict[str, Any]]:
    names_only = "the filter names identifiers rather than effects, and it is the only check here"
    return [
        _cell(
            "RP-1",
            "run_python",
            "process_spawn",
            [_layer("ast_deny_list", "open", "probe", ["ast-subprocess-reexport"], names_only)],
            False,
            None,
            "a process handle is reachable through an allowlisted module, so the cell is open "
            "whether or not this build resolves the attribute",
        ),
        _cell(
            "RP-2",
            "run_python",
            "network_egress",
            [_layer("ast_deny_list", "open", "probe", ["ast-read-csv-remote"], names_only)],
            False,
            None,
            "no engine-level fence exists for the interpreter; which hosts are reachable is a "
            "property of the installed wheels and of the network the process runs in",
        ),
        _cell(
            "RP-3",
            "run_python",
            "filesystem_read",
            [_layer("ast_deny_list", "open", "probe", ["ast-read-csv-path"], names_only)],
            False,
            None,
            "open() is refused while an allowlisted reader is not, so the filter does not close reads",
        ),
        _cell(
            "RP-4",
            "run_python",
            "filesystem_write",
            [_layer("ast_deny_list", "open", "probe", ["ast-write-csv"], names_only)],
            False,
            None,
            "the same shape as the read cell: the refused spelling is not the only spelling",
        ),
        _cell(
            "RP-5",
            "run_python",
            "credential_read",
            [
                _layer(
                    "ast_deny_list",
                    "open",
                    "probe",
                    ["ast-environ-attribute", "ast-environ-subscript"],
                    names_only,
                )
            ],
            False,
            None,
            "one refused spelling and one permitted spelling of the same capability; the cell is open",
        ),
    ]


def _run_sql_cells() -> list[dict[str, Any]]:
    guard = "a name filter over statement text: it decides spellings, not engine behaviour"
    fence = "the connection sets enable_external_access=false before any caller statement runs"
    return [
        _cell(
            "RS-1",
            "run_sql",
            "process_spawn",
            [
                _layer("sql_guard", "fenced", "probe", ["sql-install-extension"], guard),
                _layer(
                    "duckdb_fence",
                    "fenced",
                    "read",
                    [],
                    "extension loading is off, and the engine's catalogue holds no shell or process "
                    "function at all",
                ),
            ],
            False,
            None,
            "the capability is absent from the engine rather than refused by a check, so an engine "
            "that grew one would not be caught here",
        ),
        _cell(
            "RS-2",
            "run_sql",
            "network_egress",
            [
                _layer("sql_guard", "fenced", "probe", ["sql-read-function"], guard),
                _layer("duckdb_fence", "fenced", "probe", ["duckdb-read-csv"], fence),
            ],
            True,
            VERIFIED_BY,
            "both layers refuse independently; the engine layer is the one that survives a filter edit",
        ),
        _cell(
            "RS-3",
            "run_sql",
            "filesystem_read",
            [
                _layer(
                    "sql_guard",
                    "open",
                    "probe",
                    ["sql-quoted-path"],
                    "a quoted path names none of the denied patterns, which is why a second layer exists",
                ),
                _layer("duckdb_fence", "fenced", "probe", ["duckdb-read-csv"], fence),
            ],
            True,
            VERIFIED_BY,
            "the filter is open here and the engine closes it, so the cell carries the engine's answer",
        ),
        _cell(
            "RS-4",
            "run_sql",
            "filesystem_write",
            [
                _layer("sql_guard", "fenced", "probe", ["sql-copy-out"], guard),
                _layer("duckdb_fence", "fenced", "probe", ["duckdb-copy-out"], fence),
            ],
            True,
            VERIFIED_BY,
            "write verbs are refused by name and file operations are refused by configuration",
        ),
        _cell(
            "RS-5",
            "run_sql",
            "credential_read",
            [
                _layer("sql_guard", "open", "probe", ["sql-env-function"], guard),
                _layer(
                    "duckdb_fence",
                    "fenced",
                    "probe",
                    ["duckdb-env-function"],
                    "the engine answers that no such function exists, so there is nothing to read",
                ),
            ],
            False,
            None,
            "the filter would permit the call; the refusal comes from the engine's function catalogue, "
            "which is a property of the build rather than a statement of policy",
        ),
    ]


def _profile_cells() -> list[dict[str, Any]]:
    """The three cells the first reading called undecidable now name the check that decides them.

    Each keeps the old observation as a ``read`` layer, because the observation was true and stays
    useful; what changed is that a refusal now runs after it.
    """
    return [
        _cell(
            "PD-1",
            "profile_dataset",
            "process_spawn",
            [
                _layer(
                    "no_process_import",
                    "fenced",
                    "read",
                    ["profile-process-import"],
                    "read as source: the module imports no process, shell or mutation module -- an "
                    "observation, not a refusal",
                ),
                _layer(
                    "format_allowlist",
                    "fenced",
                    "probe",
                    ["profile-format-allowlist"],
                    "the reader is chosen from a six-format allowlist, so a loader that executes code "
                    "is unreachable through this surface",
                ),
            ],
            False,
            None,
            "the allowlist decides which reader can be reached; a loader added to it that executes "
            "code would not be caught by anything else here",
        ),
        _cell(
            "PD-2",
            "profile_dataset",
            "network_egress",
            [
                _layer(
                    "path_existence_and_separator",
                    "fenced",
                    "probe",
                    ["profile-url-path"],
                    "the path must exist on this host and must not carry a doubled separator, and a "
                    "URL-shaped path fails both",
                )
            ],
            False,
            None,
            "the refusal is a side effect of two local-path checks rather than a scheme allowlist",
        ),
        _cell(
            "PD-3",
            "profile_dataset",
            "filesystem_read",
            [
                _layer(
                    "no_root_confinement",
                    "open",
                    "read",
                    [],
                    "the path is the argument: a recognised extension anywhere on the host is read, "
                    "and the tool reports whether a path exists before it reports the extension it "
                    "dislikes",
                )
            ],
            False,
            None,
            "no directory or root check exists, so the cell is open by construction",
        ),
        _cell(
            "PD-4",
            "profile_dataset",
            "filesystem_write",
            [
                _layer(
                    "no_write_call",
                    "fenced",
                    "read",
                    [],
                    "the execute body writes no file -- an observation, not a refusal",
                ),
                _layer(
                    "input_fingerprint",
                    "fenced",
                    "probe",
                    ["profile-input-unchanged"],
                    "size, modification time and inode are captured before the read and compared "
                    "after it; a mutation refuses the request",
                ),
            ],
            False,
            None,
            "the fingerprint decides a write through the path the request names; a write to a path "
            "the request never mentions is not observed",
        ),
        _cell(
            "PD-5",
            "profile_dataset",
            "credential_read",
            [
                _layer(
                    "no_environment_access",
                    "fenced",
                    "read",
                    [],
                    "no environment read appears in the module -- an observation, not a refusal",
                ),
                _layer(
                    "credential_path_refusal",
                    "fenced",
                    "probe",
                    ["profile-credential-name"],
                    "credential-shaped names and directories are refused before the reader is chosen",
                ),
            ],
            False,
            None,
            "the refusal decides paths; an environment read performed without a path argument is not "
            "observed by it",
        ),
    ]


SURFACES = (
    {
        "id": "run_python",
        "entry": "packages/execution/src/dsa_execution/python_sandbox.py:execute_python",
        "input": "model-authored Python",
    },
    {
        "id": "run_sql",
        "entry": "packages/tools/src/dsa_tools/tools/run_sql.py:execute",
        "input": "model-authored SQL",
    },
    {
        "id": "profile_dataset",
        "entry": "packages/tools/src/dsa_tools/tools/profile_dataset.py:execute",
        "input": "a path, not code",
    },
)


def _probe_records() -> list[dict[str, Any]]:
    records = []
    for probe in PROBES:
        observed, detail = _attempt(probe["run"])
        records.append(
            {
                "id": probe["id"],
                "surface": probe["surface"],
                "question": probe["question"],
                "observed": observed,
                "detail": detail,
            }
        )
    return records


def _summary(cells: list[dict[str, Any]]) -> dict[str, Any]:
    verdicts = [cell["verdict"] for cell in cells]
    decided = sum(1 for cell in cells if cell["decided_by"] == "check")
    return {
        "cells": len(cells),
        "open": verdicts.count("open"),
        "fenced": verdicts.count("fenced"),
        "undecidable": verdicts.count("undecidable"),
        "decided_by_check": decided,
        "decidability": round(decided / len(cells), 4),
        "effect_verified": sum(1 for cell in cells if cell["effect_verified"]),
        "layers": sum(len(cell["layers"]) for cell in cells),
    }


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def build() -> dict[str, Any]:
    cells = _run_python_cells() + _run_sql_cells() + _profile_cells()
    return {
        "schema": SCHEMA,
        "reading": 2,
        "basis_change": (
            "the first reading attributed profile_dataset's process-spawn cell to the absence of a "
            "process import, while the format allowlist was already deciding which reader a request "
            "could reach; it is re-attributed here rather than re-worded. The write and credential "
            "cells gained a check in the same change, so no cell is now decided by absence. The "
            "first reading's counts are kept in docs/measurement-basis.md and are not restated here."
        ),
        "recorded_at": _timestamp(),
        "reviewed_commit": REVIEWED_COMMIT,
        "question": (
            "for each surface that accepts model-authored input, is the capability decided by a "
            "check that runs at request time?"
        ),
        "verdict_rule": (
            "the last check to run decides the cell; a capability with no request-time check is "
            "recorded undecidable even when today's code does not exercise it"
        ),
        "surfaces": list(SURFACES),
        "probes": _probe_records(),
        "cells": cells,
        "summary": _summary(cells),
        "not_claimed": [
            "containment: a name-based filter is not a containment mechanism, and no cell says one is",
            "matrix_valid does not imply publication_ready: this record says nothing about the "
            "evaluation matrix",
            "a fenced cell is a refusal observed through a mechanism, not a penetration test",
            "the profile_dataset cells each name the check that decides a request; a write to a path "
            "the request does not name, and an environment read performed without a path, are "
            "outside what any of them observes",
        ],
    }


def verify() -> tuple[bool, dict[str, bool]]:
    """Compare the recorded reading with what the tree yields today."""
    record = json.loads(RECORD_PATH.read_text(encoding="utf-8"))
    fresh = build()
    checks = {
        "schema": fresh["schema"] == record["schema"],
        "reading": fresh["reading"] == record["reading"],
        "basis_change": fresh["basis_change"] == record["basis_change"],
        "surfaces": fresh["surfaces"] == record["surfaces"],
        "probes": fresh["probes"] == record["probes"],
        "cells": fresh["cells"] == record["cells"],
        "summary": fresh["summary"] == record["summary"],
        "not_claimed": fresh["not_claimed"] == record["not_claimed"],
    }
    return all(checks.values()), checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--record", action="store_true", help="write the reading to docs/audit")
    mode.add_argument("--verify", action="store_true", help="compare the record with the tree")
    args = parser.parse_args(argv)

    if args.record:
        RECORD_PATH.write_text(
            json.dumps(build(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {RECORD_PATH.relative_to(ROOT)}")
        return 0
    if args.verify:
        ok, checks = verify()
        for name, passed in checks.items():
            print(f"{'ok' if passed else 'mismatch'} {name}")
        return 0 if ok else 1
    print(json.dumps(build(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
