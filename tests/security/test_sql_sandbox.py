r"""`run_sql` is fed caller-authored SQL, so its fence cannot be a list of denied words.

Measured 2026-10-23: `SELECT * FROM '/tmp/leak.csv'` returned every row. DuckDB resolves a quoted path used
as a table name through its replacement scan, which names none of the denied functions -- `read_\w+`,
`\w+_scan\(`, `glob\(` all miss it -- so the blacklist the tool had was a fence only against the shapes
someone thought to write down. The fix is the engine's own switch: `SET enable_external_access=false` on the
in-memory connection, which removes the file-system reach instead of pattern-matching around it.

The dataset half still has to work: `dataset_path` is read by `load_dataframe` in Python and registered as an
Arrow relation, so the legitimate view is not external access and the tests below assert both sides.
"""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from dsa_tools.tools.run_sql import RunSQLTool

REPO = Path(__file__).resolve().parents[2]
RUN_SQL = REPO / "packages/tools/src/dsa_tools/tools/run_sql.py"


def _csv(tmp_path: Path, name: str = "outside.csv") -> Path:
    p = tmp_path / name
    p.write_text("col_a,col_b\nrow-1,row-2\nrow-3,row-4\n", encoding="utf-8")
    return p


@pytest.mark.asyncio
async def test_a_quoted_path_is_not_a_table_the_sandbox_reads(tmp_path: Path) -> None:
    tool = RunSQLTool()
    path = _csv(tmp_path)
    # noqa below: the SQL string IS the attack being pinned, so it is built on purpose
    res = await tool.run({"sql": f"SELECT * FROM '{path}'"})  # noqa: S608 - hostile input under test
    assert res.status == "error", (
        f"the replacement scan read a file outside the repository: {res.output}"
    )
    assert not getattr(res.output, "rows", None), (
        f"rows came back from a path the caller named: {res.output}"
    )


@pytest.mark.asyncio
async def test_the_denied_function_spelling_is_still_refused(tmp_path: Path) -> None:
    """Both layers, because one of them was already proved insufficient on its own."""
    tool = RunSQLTool()
    path = _csv(tmp_path)
    res = await tool.run({"sql": f"SELECT * FROM read_csv('{path}')"})  # noqa: S608 - hostile input under test
    assert res.status == "error"
    assert "Disallowed SQL pattern" in (res.error or ""), (
        f"the deny list stopped being the first thing to answer: {res.error}"
    )


@pytest.mark.asyncio
async def test_the_fence_does_not_cost_the_tool_its_own_job(tmp_path: Path) -> None:
    """`SELECT * FROM dataset` is the tool's purpose, and it must survive the switch."""
    tool = RunSQLTool()
    path = _csv(tmp_path, "kept.csv")
    res = await tool.run({"sql": "SELECT * FROM dataset", "dataset_path": str(path)})
    assert res.status == "ok", f"the legitimate dataset view broke: {res.error}"
    assert res.output.row_count == 2, f"unexpected rows through the dataset view: {res.output.rows}"
    assert res.output.columns == ["col_a", "col_b"]


def test_the_fence_is_set_before_any_caller_sql_reaches_the_connection() -> None:
    """Presence is not placement: the SET has to run before the caller's statement does."""
    tree = ast.parse(RUN_SQL.read_text(encoding="utf-8"))
    lines = RUN_SQL.read_text(encoding="utf-8").splitlines()

    set_lines: list[int] = []
    sql_lines: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr != "execute" or not node.args:
                continue
            first = node.args[0]
            if not isinstance(first, ast.Constant) or not isinstance(first.value, str):
                sql_lines.append(node.lineno)  # f-string / variable -> the caller's SQL
            elif "enable_external_access" in first.value:
                set_lines.append(node.lineno)
    assert set_lines, (
        "no engine-level external-access fence in the tool that runs caller-authored SQL"
    )
    assert sql_lines, "the statement that hands the caller's SQL to the connection was not found"
    assert min(set_lines) < min(sql_lines), (
        f"the fence is set at line {min(set_lines)}, after the SQL is executed at line {min(sql_lines)}"
    )
    assert any("SET enable_external_access=false" in lines[n - 1] for n in set_lines), (
        f"the fence does not actually turn access off: {[lines[n - 1] for n in set_lines]}"
    )


@pytest.mark.asyncio
async def test_a_json_path_used_as_a_table_is_not_read_either(tmp_path: Path) -> None:
    """One file type would certify one scanner; the switch is supposed to cover the family."""
    tool = RunSQLTool()
    path = tmp_path / "outside.json"
    payload = {"col_a": "row-1", "digest": hashlib.sha256(b"x").hexdigest()[:12]}
    path.write_text(str(payload).replace("'", '"'), encoding="utf-8")
    res = await tool.run({"sql": f"SELECT * FROM '{path}'"})  # noqa: S608 - hostile input under test
    assert res.status == "error", f"the scan for another format still read the file: {res.output}"
