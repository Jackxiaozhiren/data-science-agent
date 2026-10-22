"""The MCP App page renders wire text into HTML, so that rendering is the security boundary.

``/mcp-app`` assembles two fragments with ``innerHTML``: the dataset ``<option>`` list, built from a resource's
own ``name`` and ``description``, and the evidence table, built from ``id``, ``claim`` and ``source_type``. A claim
quotes the question the client typed and the header row of the analysed file, and ``pl.read_csv`` keeps a header
verbatim, so both are input the product never authored. ``enableScripts`` is not involved -- the page's own script
is the executor.

The probe loads the script out of ``dsa_mcp.app.HTML`` (the bytes the route actually returns), stubs the handful
of browser globals it touches at load time, and calls the two renderers on a payload that is an ``<img onerror>``
tag. The payload's own proof is asserted first, exactly as in the VS Code and Jupyter guards: if the same string
interpolated raw is not live markup, a clean result would certify nothing.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from dsa_mcp.app import HTML

_PAYLOAD = '<img src=x onerror="alert(1)">'
_HARNESS = """
const fs = require("node:fs");
const src = fs.readFileSync(process.argv[2], "utf8");
const els = new Map();
const element = () => ({ innerHTML: "", textContent: "", hidden: false, disabled: false, style: {} });
const document = {
  getElementById: (id) => {
    if (!els.has(id)) els.set(id, element());
    return els.get(id);
  },
};
const location = { search: "" };
const history = { replaceState: () => {} };
const stubConsole = { log: () => {} };
const noTransport = async () => {
  throw new Error("the probe never reaches the server");
};
const output = {};
// The page script is top-level code, so the only way to run it and still hold the functions it declares is to
// evaluate it with its globals passed as parameters and read the declarations back out of its own scope.
new Function(
  "document",
  "location",
  "history",
  "console",
  "fetch",
  "output",
  src + "\\noutput.esc = esc; output.renderOptions = renderOptions; output.renderEvidence = renderEvidence;",
)(document, location, history, stubConsole, noTransport, output);

const P = process.argv[3];
const ev = output.renderEvidence([
  { id: P, claim: P, source_type: P },
  { id: 7, claim: undefined, source_type: null },
]);
const opts = output.renderOptions([
  { uri: "dataset://" + P, name: P, description: P },
  { uri: "dataset://plain", name: "plain" },
]);
process.stdout.write(JSON.stringify({
  ev,
  opts,
  fallback: output.esc(P),
  rawInOldShape: (`<td>${P}</td>`.match(/<img /g) || []).length,
}));
"""


def _script() -> str:
    match = re.search(r"<script>(.*?)</script>", HTML, re.DOTALL)
    assert match, "the App page no longer carries an inline script -- where does it build its HTML?"
    return match.group(1)


def _render(tmp_path: Path) -> dict[str, str]:
    script_file = tmp_path / "app-page.js"
    script_file.write_text(_script(), encoding="utf-8")
    harness = tmp_path / "harness.cjs"
    harness.write_text(_HARNESS, encoding="utf-8")
    cp = subprocess.run(
        ["node", str(harness), str(script_file), _PAYLOAD],
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    return json.loads(cp.stdout)


def test_wire_text_reaches_the_page_only_in_escaped_form(tmp_path: Path) -> None:
    out = _render(tmp_path)
    assert out["rawInOldShape"] == 1, (
        "the payload is not live markup when interpolated raw, so the assertions below certify nothing"
    )
    assert "<img " not in out["ev"], f"an evidence field reached innerHTML unescaped: {out['ev']}"
    assert "<img " not in out["opts"], f"a dataset field reached innerHTML unescaped: {out['opts']}"
    assert "&lt;img" in out["ev"] and "&lt;img" in out["opts"], (
        f"expected the escaped form of the payload in both fragments: {out}"
    )
    assert 'onerror="' not in out["ev"] + out["opts"], (
        f"an inline event handler survived into the fragment: {out}"
    )
    assert out["fallback"] == "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;", (
        f"esc() no longer quotes the characters the sinks need closed: {out['fallback']}"
    )
    assert "<table><tr><th>id</th>" in out["ev"] and "<td>7</td>" in out["ev"], (
        f"the renderer stopped emitting the table it is supposed to build: {out['ev']}"
    )
    assert "plain" in out["opts"], f"a resource with no description vanished: {out['opts']}"


def test_the_page_writes_html_only_through_the_named_renders() -> None:
    """Every ``innerHTML`` assignment in the page must be a call into an escaping renderer or a constant.

    The set is pinned rather than pattern-matched on purpose: adding a third HTML sink makes this red, and the
    only ways forward are to route it through ``esc()`` or to name it here after checking what feeds it.
    """
    statements = re.findall(r"\.innerHTML\s*=\s*([^;\n]+);", _script())
    assert len(statements) == 3, (
        f"expected the three known sinks, found {len(statements)}: {statements}"
    )
    for stmt in statements:
        collapsed = re.sub(r"'[^']*'", "''", stmt)
        assert (
            "renderOptions(" in collapsed or "renderEvidence(" in collapsed or "${" not in collapsed
        ), f"an HTML sink interpolates something that is not esc()'d: {stmt}"
