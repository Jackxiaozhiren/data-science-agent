"""W5 VS Code Real Integration — §33-35 (MVP, Arch, Failure Handling)."""

from __future__ import annotations

import json
import re
import subprocess
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
    # dsa.ts must call CLI, not Agent logic. The command is argv rather than one string since §35's shell fix:
    # the program is `uv` and the words are the array, so the assertion reads the call rather than a substring
    # that only exists when the arguments are interpolated into a shell line.
    assert re.search(r"execFile\(\s*'uv'\s*,\s*\[\s*'run',\s*'dsa'", dsa), (
        "dsa.ts no longer shells out to the public CLI in argv form"
    )
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


#: Child-process calls that hand their argument to /bin/sh: `exec` and `execSync`. `execFile`, `execFileSync`
#: and `spawn` do not, `executeCommand` is the VS Code API rather than a process, and the receiver is required
#: on `exec` because `/re/.exec(s)` is a string method with the same name -- a predicate that flags that would
#: be loosened away within a week, which is how this kind of guard actually dies.
_SHELL_CALL = re.compile(r"\bexecSync\s*\(|\w+\.exec\s*\(|promisify\([^)]*\.exec\b")
#: The shell sink lived in one directory; the class is repo-wide, and the same lines that pin `apps/vscode` can
#: pin every script under apps/ and packages/.
_JS_GLOBS = (
    "apps/**/*.ts",
    "apps/**/*.tsx",
    "apps/**/*.mjs",
    "apps/**/*.js",
    "packages/**/*.ts",
    "packages/**/*.mjs",
)
_SKIP_DIRS = {"node_modules", ".next", "dist", "out", "__pycache__", ".venv", ".turbo"}


def test_no_extension_call_hands_the_shell_a_word_from_outside() -> None:
    """A dataset filename is outside input, and the workspace can set `dsa.pythonPath`.

    Every command was built as one string -- `exec(`uv run dsa analyze ${JSON.stringify(dataset)} ...`)` -- and
    `exec` hands that string to /bin/sh. JSON.stringify adds *shell* double quotes too, and shell double quotes
    still expand `$(...)` and backticks, so a file named `a$(touch /tmp/x).csv` ran the substitution before the
    CLI saw the path -- and reached the CLI as `a.csv`, silently truncated. `test_the_shell_vs_argv_pair`
    measures both halves; this test keeps the shape from coming back.
    """
    offenders: dict[str, list[str]] = {}
    for pattern in _JS_GLOBS:
        for source in sorted(REPO.glob(pattern)):
            if _SKIP_DIRS & set(source.parts):
                continue
            hits = [
                f"{i}: {line.strip()[:90]}"
                for i, line in enumerate(
                    source.read_text(encoding="utf-8", errors="replace").splitlines(), 1
                )
                if _SHELL_CALL.search(line)
            ]
            if hits:
                offenders[str(source.relative_to(REPO))] = hits
    assert offenders == {}, f"a shell-splicing call came back: {offenders}"

    # The predicate's own eyes, both directions -- otherwise "no offenders" may only mean "no sight".
    assert _SHELL_CALL.search("    const { stdout } = await cp.exec(cmd, { timeout: 30000 });"), (
        "the guard cannot see the shape it exists to catch, so it guards nothing"
    )
    assert not _SHELL_CALL.search('  const m = /rgba?\\\\(([^)]*)\\\\)/.exec(color ?? "");'), (
        "the guard fires on a regular expression's .exec() -- false positives get a guard loosened away"
    )
    assert not _SHELL_CALL.search("  await execFile('uv', argv, { timeout: 10000 });"), (
        "the guard fires on the safe shape too, so it will be widened away"
    )
    dsa = (VSCODE / "src" / "dsa.ts").read_text(encoding="utf-8")
    assert re.search(r"execFile\(\s*py\s*,\s*\[", dsa), (
        "the config-derived interpreter is not argv'd"
    )
    assert re.search(r"execFile\(\s*'uv'\s*,\s*\[", dsa), "the CLI calls are not argv'd"
    assert "JSON.stringify(dataset)" not in dsa and "JSON.stringify(task)" not in dsa, (
        "quoting reappeared where an argv array belongs"
    )


def test_the_shell_vs_argv_pair_behave_as_the_guard_assumes(tmp_path: Path) -> None:
    """The mechanism, measured rather than asserted: /bin/sh substitutes, `execFile` does not.

    Written as one node probe because the two outcomes are the point of the pair -- a test that only showed
    argv being safe would also pass in a world where the string form was safe, and the guard above would then
    be policing nothing.
    """
    marker = tmp_path / "substituted"
    probe = tmp_path / "probe.mjs"
    probe.write_text(
        "import cp from 'node:child_process';\n"
        "import util from 'node:util';\n"
        "import fs from 'node:fs';\n"
        "const exec = util.promisify(cp.exec);\n"
        "const execFile = util.promisify(cp.execFile);\n"
        "const marker = process.argv[2];\n"
        "const evil = `x$(touch ${marker}).csv`;\n"
        "await exec(`node echo.mjs ${JSON.stringify(evil)}`).catch(() => {});\n"
        "const shellSubstituted = fs.existsSync(marker);\n"
        "fs.rmSync(marker, { force: true });\n"
        "const out = await execFile(process.execPath, [new URL('./echo.mjs', import.meta.url).pathname, evil]);\n"
        "console.log(JSON.stringify({ shellSubstituted, argvIntact: out.stdout.trim() === evil }));\n",
        encoding="utf-8",
    )
    echo = tmp_path / "echo.mjs"
    echo.write_text("console.log(process.argv[2] ?? '');\n", encoding="utf-8")
    # `exec` runs in the probe's cwd, where echo.mjs sits next to it.
    result = subprocess.run(
        ["node", str(probe), str(marker)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr[-400:]
    observed = json.loads(result.stdout.strip().splitlines()[-1])
    assert observed == {"shellSubstituted": True, "argvIntact": True}, observed
