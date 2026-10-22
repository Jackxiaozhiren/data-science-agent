"""The `/mcp` page's "copy a call template" button used to copy a call that cannot succeed.

`copyTemplate` built `{ params: { name, arguments: {} } }` for every tool. The page exists to show a person how to
call these tools, and half of them reject an empty argument object -- `run_sql` needs `sql`, `analyze` needs `task`,
`causal_check` needs `dataset_path`, `treatment` and `outcome`. So the affordance was wrong in the way that is worst:
it looked finished, and the failure surfaced later, in whatever the user pasted it into.

The fix reads the tool's own `inputSchema`, which the server only started publishing under the protocol's field name
in this same round (``tools_for_wire``, ledger §250). This guard is an AST check rather than a substring one for the
usual reason here: `arguments: {}` and `arguments: requiredArguments(tool.inputSchema)` are both findable by eye in a
grep, and only one of them is a shape the server would accept.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

_WEB = Path(__file__).resolve().parents[2] / "apps" / "web"
_TABLE = _WEB / "app" / "mcp" / "McpTable.tsx"

_PROBE = """
const fs = require("node:fs");
const path = require("node:path");
const { createRequire } = require("node:module");
const require_ = createRequire(path.join(process.argv[2], "noop.js"));
const ts = require_("typescript");
const source = fs.readFileSync(process.argv[3], "utf8");
const file = ts.createSourceFile("McpTable.tsx", source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);

let argumentsValue = null;
let argumentsParent = null;
let helperBody = null;

function visit(node) {
  if (ts.isPropertyAssignment(node) && node.name.getText() === "arguments") {
    if (argumentsValue === null) {
      argumentsValue = node.initializer.getText();
      argumentsParent = node.parent.getText();
    }
  }
  if (ts.isFunctionDeclaration(node) && node.name && node.name.text === "requiredArguments") {
    helperBody = node.body ? node.body.getText() : "";
  }
  ts.forEachChild(node, visit);
}
visit(file);

process.stdout.write(JSON.stringify({ argumentsValue, argumentsParent, helperBody }));
"""


def _probe(tmp_path: Path) -> dict[str, str | None]:
    harness = tmp_path / "probe.cjs"
    harness.write_text(_PROBE, encoding="utf-8")
    cp = subprocess.run(
        ["node", str(harness), str(_WEB / "scripts"), str(_TABLE)],
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    return json.loads(cp.stdout)


def test_the_copied_template_carries_computed_arguments(tmp_path: Path) -> None:
    out = _probe(tmp_path)
    assert out["argumentsValue"] is not None, (
        "no `arguments` property found -- did copyTemplate move?"
    )
    assert "requiredArguments(" in out["argumentsValue"], (
        f"the copied template hands out a fixed argument object again: {out['argumentsValue']}"
    )
    assert out["argumentsValue"] not in ("{}", "Object()"), (
        f"the template arguments are empty again: {out['argumentsValue']}"
    )
    assert "name: tool.name" in (out["argumentsParent"] or ""), (
        f"the template no longer names the tool it was copied for: {out['argumentsParent']}"
    )


def test_the_helper_reads_the_schema_it_is_handed(tmp_path: Path) -> None:
    """An empty-object placeholder with a different name would pass the guard above, so check the derivation."""
    body = _probe(tmp_path)["helperBody"]
    assert body is not None, (
        "requiredArguments is gone, so nothing derives arguments from the schema"
    )
    assert "required" in body and "properties" in body, (
        f"requiredArguments no longer reads both halves of the schema: {body}"
    )
    assert "<required>" in body, (
        f"string parameters lost their unmissable placeholder, so a copied call looks complete: {body}"
    )
