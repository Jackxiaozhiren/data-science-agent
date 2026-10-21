"""W5 VS Code Real Integration — §33-35 (MVP, Arch, Failure Handling)."""

from __future__ import annotations

import json
from pathlib import Path


REPO = Path(__file__).parents[2]
VSCODE = REPO / "apps" / "vscode"


def test_package_manifest_commands_and_views() -> None:
    pkg = json.loads((VSCODE / "package.json").read_text())
    assert pkg["name"] == "dsa-vscode"
    assert pkg["version"] == "0.1.0"
    assert pkg["main"] == "./out/extension.js"
    cmds = {c["command"] for c in pkg["contributes"]["commands"]}
    # §33 6-step loop + doctor
    for required in (
        "dsa.openDataset",
        "dsa.askAnalysis",
        "dsa.runAnalysis",
        "dsa.viewResult",
        "dsa.viewEvidence",
        "dsa.openReport",
        "dsa.doctor",
    ):
        assert required in cmds, f"missing {required}"
    views = pkg["contributes"]["views"]["dsaExplorer"]
    ids = {v["id"] for v in views}
    assert "dsa.datasetExplorer" in ids
    assert "dsa.evidenceExplorer" in ids
    # activation
    assert "activationEvents" in pkg


def test_extension_src_exists_and_arch_guard() -> None:
    """§34 Architecture: Extension → Public SDK/CLI → Core (no direct dsa_agent import)."""
    ext = (VSCODE / "src" / "extension.ts").read_text()
    dsa = (VSCODE / "src" / "dsa.ts").read_text()
    views = (VSCODE / "src" / "views.ts").read_text()
    assert "registerCommand" in ext
    assert "DatasetTreeProvider" in views
    assert "ResultPanel" in views
    # Arch guard: extension must not import dsa_agent (Internal)
    assert "from dsa_agent" not in ext
    assert "import dsa_agent" not in ext
    assert "from dsa_agent" not in dsa
    # dsa.ts must call CLI, not Agent logic
    assert "uv run dsa" in dsa
    assert "child_process" in dsa
    # No duplicate Agent graph in extension
    assert "StateGraph" not in ext
    assert "MemorySaver" not in ext


def test_failure_handling_all_five_cases() -> None:
    """§35 must support 5 failures with clear suggestions."""
    dsa = (VSCODE / "src" / "dsa.ts").read_text()
    for case in (
        "LLM unavailable",
        "Python unavailable",
        "Dataset missing",
        "Plugin failure",
        "Backend unavailable",
    ):
        assert case in dsa, f"missing case {case}"
    # Each should have suggestion
    assert "Suggestion" in dsa or "suggestion" in dsa
    # Check functions exist
    for fn in (
        "checkPython",
        "checkLLM",
        "checkDataset",
        "checkPlugin",
        "checkBackend",
        "runAnalysis",
        "runProfile",
    ):
        assert fn in dsa


def test_views_implement_6step_flow() -> None:
    ext = (VSCODE / "src" / "extension.ts").read_text()
    # Flow commands
    for cmd in (
        "openDataset",
        "askAnalysis",
        "runAnalysis",
        "viewResult",
        "viewEvidence",
        "openReport",
    ):
        assert cmd in ext
    # Progress
    assert "withProgress" in ext
    assert "Planner" in ext
    # Evidence Explorer context
    assert "dsa:hasResult" in ext
    assert "EvidenceTreeProvider" in ext
    # ResultPanel HTML
    views = (VSCODE / "src" / "views.ts").read_text()
    assert "WebviewPanel" in views
    assert "Evidence" in views
    assert "Report" in views


def test_typescript_compiles() -> None:
    import subprocess

    cp = subprocess.run(
        ["npm", "--prefix", str(VSCODE), "run", "compile"], capture_output=True, text=True
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    assert (VSCODE / "out" / "extension.js").exists()
    assert (VSCODE / "out" / "dsa.js").exists()
    assert (VSCODE / "out" / "views.js").exists()


def test_result_webview_escapes_run_derived_text(tmp_path: Path) -> None:
    """The result panel is a `enableScripts: true` webview, so unescaped run data in it is code execution.

    The claim, its id and its source type are text that came out of the analysed file and the model, and they are
    interpolated into table cells. This calls the compiled `getHtml` directly -- with `vscode` stubbed, because the
    function touches none of it -- on a payload that is an `<img onerror>` tag, and asserts the rendered document
    carries the escaped form only.

    The second half is the payload's own proof: the same string placed through the interpolation the code used
    before yields a live `<img `, so a passing result cannot be explained by a payload that never was markup.
    """
    import subprocess

    views_js = VSCODE / "out" / "views.js"
    if not views_js.exists():
        cp = subprocess.run(
            ["npm", "--prefix", str(VSCODE), "run", "compile"], capture_output=True, text=True
        )
        assert cp.returncode == 0, cp.stderr + cp.stdout

    probe = """
const Module = require("module");
const load = Module._load;
Module._load = function (req, ...rest) {
  if (req === "vscode") {
    return {
      window: {},
      TreeItem: class {},
      TreeItemCollapsibleState: { None: 0 },
      EventEmitter: class { constructor() { this.event = () => {}; } },
    };
  }
  return load.call(this, req, ...rest);
};
const path = require("path");
const { ResultPanel } = require(path.join(process.argv[2], "out", "views.js"));
const PAYLOAD = '<img src=x onerror="alert(1)">';
const result = {
  run_id: "run-abc",
  status: PAYLOAD,
  report_markdown: PAYLOAD,
  evidence: [{ id: PAYLOAD, claim: PAYLOAD, source_type: PAYLOAD }],
};
const html = ResultPanel.prototype.getHtml.call({}, PAYLOAD, result);
const oldShape = `<td>${PAYLOAD.slice(0, 120)}</td>`;
console.log(JSON.stringify({
  rawInHtml: (html.match(/<img /g) || []).length,
  escapedInHtml: (html.match(/&lt;img /g) || []).length,
  rawInOldShape: (oldShape.match(/<img /g) || []).length,
  rawOnerrorAttr: /onerror="/.test(html),
}));
"""
    probe_file = tmp_path / "probe.cjs"
    probe_file.write_text(probe)
    cp = subprocess.run(["node", str(probe_file), str(VSCODE)], capture_output=True, text=True)
    assert cp.returncode == 0, cp.stderr + cp.stdout
    out = json.loads(cp.stdout.strip().splitlines()[-1])

    assert out["rawInOldShape"] == 1, (
        "the payload is not live markup when interpolated raw, so the assertions below certify nothing"
    )
    assert out["rawInHtml"] == 0, f"run-derived text reached the webview unescaped: {out}"
    assert out["escapedInHtml"] >= 5, (
        f"expected each of the five interpolated fields to escape, saw {out['escapedInHtml']}: {out}"
    )
    assert out["rawOnerrorAttr"] is False, (
        f'an onerror=" attribute survived into the document: {out}'
    )


def test_package_json_contributes_configuration() -> None:
    pkg = json.loads((VSCODE / "package.json").read_text())
    cfg = pkg["contributes"]["configuration"]["properties"]
    assert "dsa.pythonPath" in cfg
    assert "dsa.apiUrl" in cfg
    # Check engines
    assert "vscode" in pkg["engines"]


def test_no_stub_anymore() -> None:
    readme = (VSCODE / "README.md").read_text()
    assert "Stub" not in readme or "replaces stub" in readme
    assert "Open Dataset" in readme
    assert "Ask DSA" in readme
    assert "§33" in readme
    assert "§35" in readme
