"""R-04: `dsa ui` must be one command that stays on the user's machine, or it is a worse version of the demo.

The audience in §5 will not run two commands in two terminals (B15) and will not upload real data to a hosted
box (B7). `dsa ui` is the answer, and five things can silently ruin it before a browser ever opens:

1. **the parser seam.** `build_parser()` exists so the surface is inspectable without dispatching -- the defect
   `tests/unit/test_cli_help_surface.py` recorded as a prerequisite, where `--help` exits before argparse can
   report an unrecognised positional, so a help-only run cannot prove an advertised flag exists.
2. **the defaults.** Loopback host, and API port 8000, because `NEXT_PUBLIC_API_URL` is *inlined at build
   time*: the built client measured here contains the literal `http://localhost:8000`, so a UI served against
   a different API port would load and then have every request refused by CORS. That is the worst possible
   failure -- a working-looking page that cannot work.
3. **a stale or missing bundle.** `.next` absent, or older than the sources it should represent, must be an
   actionable error naming the build command, never a silent serve of the previous product.
4. **a busy port or a missing runtime.** Both are detected before spawning, not after a confusing half-start.
5. **teardown.** One interrupt must leave nothing listening. Children go into their own process group, and the
   supervisor signals *that* group -- a supervisor that signals the group it belongs to kills the terminal too
   (measured the hard way while spiking this command: the spike's teardown line destroyed its own shell).

Tested without booting the product: preflight is pure, the parser is inspected directly, and the teardown is
proved against a `sleep` child, which is the same process-group machinery with none of the flakiness §188's
runner taught us about real runs.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def _parser() -> argparse.ArgumentParser:
    from dsa_evaluation.cli import build_parser

    return build_parser()


def _ui_parser() -> argparse.ArgumentParser:
    for name, action in _parser()._subparsers._group_actions[0].choices.items():  # noqa: SLF001
        if name == "ui":
            return action
    raise AssertionError("`dsa ui` is not a registered subcommand")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _fake_web(
    root: Path, *, built: bool = True, fresh: bool = True, baked_port: int = 8000
) -> Path:
    """A web directory shaped like the real one: `.next/BUILD_ID` plus a chunk carrying the baked origin."""
    web = root / "apps" / "web"
    (web / "app").mkdir(parents=True, exist_ok=True)
    (web / "app" / "page.tsx").write_text(
        "export default function P() { return null; }\n", encoding="utf-8"
    )
    if built:
        nxt = web / ".next"
        (nxt / "static" / "chunks").mkdir(parents=True, exist_ok=True)
        (nxt / "BUILD_ID").write_text("test-build\n", encoding="utf-8")
        (nxt / "static" / "chunks" / "abc.js").write_text(
            f'const base="http://localhost:{baked_port}";\n', encoding="utf-8"
        )
        if not fresh:
            # The bundle must read as older than the sources it is supposed to represent: touch the
            # sources into the future relative to BUILD_ID, which is what `next build` stamped.
            marker = nxt / "BUILD_ID"
            stale = marker.stat().st_mtime - 60
            for source in (web / "app" / "page.tsx",):
                os.utime(source, (stale + 120, stale + 120))
            os.utime(marker, (stale, stale))
    return web


# --- 1. the seam and the advertised surface -------------------------------------------------------------


def test_build_parser_exists_and_ui_advertises_every_documented_flag() -> None:
    parser = _ui_parser()
    flags = {option for action in parser._actions for option in action.option_strings}  # noqa: SLF001
    assert {"--port", "--api-port", "--host", "--data-dir", "--json"} <= flags, (
        f"`dsa ui` advertises {sorted(flags)}; the plan's five flags are not all there"
    )


def test_the_defaults_are_loopback_and_the_baked_api_port() -> None:
    args = _ui_parser().parse_args([])
    assert args.host in {"127.0.0.1", "localhost"}, (
        f"`dsa ui` defaults to host {args.host!r}: a command the audience trusts must not open a listening "
        "socket on a network interface by default"
    )
    assert args.api_port == 8000, (
        f"default api port is {args.api_port}, but the built client is compiled against "
        "http://localhost:8000 -- the page would load and every request would fail CORS preflight"
    )


def test_a_deliberate_public_bind_is_still_an_explicit_choice() -> None:
    args = _ui_parser().parse_args(["--host", "192.0.2.1"])
    assert args.host == "192.0.2.1", (
        "a deliberate public bind must be expressible without writing all-interfaces in the test"
    )


# --- 2/3/4. preflight: every blocker before a single process is spawned --------------------------------


def test_preflight_passes_a_complete_web_directory(tmp_path: Path) -> None:
    from dsa_evaluation.ui import preflight

    api_port = _free_port()
    # The fake bundle is compiled for the port the test will start on, because that agreement is exactly
    # what the origin check exists to enforce.
    web = _fake_web(tmp_path, baked_port=api_port)
    report = preflight(
        web_dir=web, data_dir=tmp_path / "data", api_port=api_port, ui_port=_free_port()
    )
    assert [check.name for check in report if not check.ok] == [], (
        f"a well-formed directory was refused: {[(c.name, c.detail) for c in report if not c.ok]}"
    )


def test_preflight_refuses_a_missing_bundle_and_names_the_build_command(tmp_path: Path) -> None:
    from dsa_evaluation.ui import preflight

    web = _fake_web(tmp_path, built=False)
    report = preflight(
        web_dir=web, data_dir=tmp_path / "data", api_port=_free_port(), ui_port=_free_port()
    )
    blocker = [check for check in report if check.name == "web bundle" and not check.ok]
    assert blocker, "no `.next` at all, yet preflight found nothing wrong"
    assert "build" in blocker[0].fix, (
        f"the refusal says {blocker[0].fix!r}: it must tell the user what to run, not just that it failed"
    )


def test_preflight_refuses_a_bundle_older_than_the_sources_it_represents(tmp_path: Path) -> None:
    from dsa_evaluation.ui import preflight

    web = _fake_web(tmp_path, fresh=False)
    report = preflight(
        web_dir=web, data_dir=tmp_path / "data", api_port=_free_port(), ui_port=_free_port()
    )
    stale = [check for check in report if not check.ok and "bundle" in check.name]
    assert stale, (
        "a bundle older than app/ would serve the previous product and the user would blame `dsa ui`"
    )


def test_preflight_refuses_an_api_port_the_built_client_cannot_reach(tmp_path: Path) -> None:
    from dsa_evaluation.ui import preflight

    web = _fake_web(tmp_path, baked_port=8000)
    report = preflight(web_dir=web, data_dir=tmp_path / "data", api_port=9123, ui_port=_free_port())
    mismatch = [check for check in report if not check.ok and "origin" in check.name]
    assert mismatch, (
        "port 9123 was accepted although the bundle was compiled against :8000 -- the page loads, then "
        "every fetch is refused, which reads like a broken product"
    )
    assert "NEXT_PUBLIC_API_URL" in mismatch[0].fix, (
        "the fix must name the variable to rebuild with"
    )


def test_preflight_refuses_a_port_someone_else_is_listening_on(tmp_path: Path) -> None:
    from dsa_evaluation.ui import preflight

    with socket.socket() as held:
        held.bind(("127.0.0.1", 0))
        held.listen(1)
        busy = int(held.getsockname()[1])
        web = _fake_web(tmp_path)
        report = preflight(
            web_dir=web, data_dir=tmp_path / "data", api_port=busy, ui_port=_free_port()
        )
    blocked = [check for check in report if not check.ok and str(busy) in check.detail]
    assert blocked, f"port {busy} was in use and preflight did not notice"


def test_preflight_says_what_is_on_the_wire(tmp_path: Path) -> None:
    """The plan's item 4: no outbound call except the model endpoint the user configured."""
    from dsa_evaluation.ui import preflight

    web = _fake_web(tmp_path)
    report = preflight(
        web_dir=web, data_dir=tmp_path / "data", api_port=_free_port(), ui_port=_free_port()
    )
    network = [check for check in report if check.name == "network"]
    assert network, "preflight reports nothing about outbound traffic"
    assert "loopback" in network[0].detail.lower()


# --- 5. teardown: the dangerous machinery, proved without the product -----------------------------------


def test_stopping_the_group_terminates_children_spawned_into_it() -> None:
    from dsa_evaluation.ui import spawn_group, stop_group

    child = spawn_group([sys.executable, "-c", "import time; time.sleep(120)"])
    try:
        assert child.poll() is None, "the child died immediately; the test proves nothing"
        stop_group(child, timeout=10.0)
    finally:
        if child.poll() is None:  # defensive: never leak a sleeper into the suite
            child.kill()
            child.wait(timeout=10)
    assert child.poll() is not None, "stop_group left the child running"


def test_stop_group_escalates_to_kill_when_a_child_ignores_term() -> None:
    """A child that will not take SIGTERM must still be gone afterwards, and gone *by* SIGKILL.

    The first version of this test raced in the flattering direction: it sent the signal before the child had
    executed `signal.signal(SIGTERM, SIG_IGN)`, so the child died on TERM and the guard passed even with the
    escalation deleted (found by plant). The child now announces that it is ignoring TERM, and the assertion
    names the signal, so only the escalation can satisfy it.
    """
    from dsa_evaluation.ui import spawn_group, stop_group

    stubborn = (
        "import signal, time\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        "print('ignoring-term', flush=True)\n"
        "time.sleep(120)\n"
    )
    child = spawn_group([sys.executable, "-c", stubborn], capture_output=True)
    try:
        assert child.stdout is not None
        ready = False
        deadline = time.monotonic() + 30.0
        while time.monotonic() < deadline:
            if b"ignoring-term" in child.stdout.readline():
                ready = True
                break
        assert ready, (
            "the child never reported that it was ignoring SIGTERM; the test proves nothing"
        )
        stop_group(child, timeout=3.0)
        assert child.poll() == -signal.SIGKILL, (
            f"the child exited as {child.poll()}; a TERM-ignoring child can only be removed by the "
            "SIGKILL escalation"
        )
    finally:
        if child.poll() is None:
            os.killpg(os.getpgid(child.pid), signal.SIGKILL)
            child.wait(timeout=10)


def test_the_supervisor_is_not_in_the_group_it_signals() -> None:
    """Measured while spiking: `kill -TERM -PGID` from inside the group kills the caller's shell too."""
    from dsa_evaluation.ui import spawn_group

    child = spawn_group(
        [sys.executable, "-c", "import os; print(os.getpgid(0))"], capture_output=True
    )
    try:
        out = child.communicate(timeout=30)[0].decode().strip()
        assert out and int(out) == child.pid, (
            f"child pgid {out} != its own pid: the child shares the supervisor's group, so the teardown "
            "would signal the process that owns the terminal"
        )
    finally:
        if child.poll() is None:
            child.kill()


# --- the command's own contract: --json is machine-usable and honest -------------------------------------


def test_sigterm_asks_for_a_stop_instead_of_ending_the_supervisor() -> None:
    """Ctrl-C was handled; `kill`, a service stop and a harness all send SIGTERM, and that bypassed teardown.

    Measured live: after SIGTERM the supervisor was gone and ports 8000 and 3000 were still listening,
    because the default disposition ends the process without running the cleanup that stops the children.

    The check runs in a **child** process on purpose. The first version signalled the pytest process itself,
    and when the handler was removed in a plant the run died at rc 143 with no verdict line -- a crash reads
    as an infrastructure failure, not as this defect, which is the attribution cost §188 paid for three
    samples. Here a missing handler shows up as a non-zero child and a named assertion.
    """
    harness = (
        "import os, signal, threading, time\n"
        "from dsa_evaluation.ui import install_stop_handlers\n"
        "flag = threading.Event()\n"
        "install_stop_handlers(flag)\n"
        "os.kill(os.getpid(), signal.SIGTERM)\n"
        "deadline = time.monotonic() + 2.0\n"
        "while not flag.is_set() and time.monotonic() < deadline:\n"
        "    time.sleep(0.02)\n"
        "print('SET' if flag.is_set() else 'UNSET')\n"
    )
    proc = subprocess.run(  # noqa: S603 - fixed argv, the module's own harness, no shell
        [sys.executable, "-c", harness],
        capture_output=True,
        text=True,
        check=False,
        timeout=90,
    )
    assert proc.returncode == 0, (
        f"the harness was killed by SIGTERM (rc {proc.returncode}) instead of handling it: "
        f"{proc.stderr[-200:]}"
    )
    assert "SET" in proc.stdout, (
        f"SIGTERM reached the process but not the stop path: {proc.stdout!r}"
    )


def test_the_user_visible_lines_are_flushed() -> None:
    """Python block-buffers a piped stdout, and the first live run proved it: servers answering, no URL.

    Read as an AST rather than as a substring, so a wrapped line, a reformat, or a new print cannot slip
    past the guard by moving text around.
    """
    import ast
    import inspect

    from dsa_evaluation import ui as ui_module

    tree = ast.parse(inspect.getsource(ui_module.serve))
    offenders: list[str] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
            continue
        if node.func.id != "print":
            continue
        keywords = {keyword.arg for keyword in node.keywords if keyword.arg}
        if "file" in keywords:
            continue  # the blocker lines go to stderr, unbuffered by default
        if "flush" not in keywords:
            offenders.append(
                ast.get_source_segment(inspect.getsource(ui_module.serve), node) or "print(...)"
            )
    assert not offenders, f"unflushed user-visible prints would sit in a pipe: {offenders}"


def test_dsa_ui_json_refuses_instead_of_exiting_zero_silently(tmp_path: Path) -> None:
    exe = shutil.which("dsa")
    if exe is None:  # pragma: no cover - the console script is the surface under test
        pytest.skip("dsa console script not on PATH")
    web = _fake_web(tmp_path, built=False)
    proc = subprocess.run(  # noqa: S603 - fixed argv, no shell, --json preflight only
        [
            exe,
            "ui",
            "--json",
            "--web-dir",
            str(web),
            "--data-dir",
            str(tmp_path / "data"),
            "--api-port",
            str(_free_port()),
            "--port",
            str(_free_port()),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert proc.returncode != 0, (
        f"`dsa ui --json` exited {proc.returncode} against a tree with no bundle: a silent 0 is the "
        "shape that turns a broken setup into 'it started'"
    )
    payload = json.loads(proc.stdout)
    assert payload["ok"] is False, f"the JSON claimed success: {payload}"
    assert any("build" in check["fix"] for check in payload["checks"] if not check["ok"]), payload


def test_the_origin_this_command_prints_is_an_origin_the_api_answers(tmp_path, monkeypatch) -> None:
    """`localhost` and `127.0.0.1` are different CORS origins, and this command hands the user the address form.

    Measured live against a running instance: `http://127.0.0.1:3000` loaded the page and then had every
    request refused, because the API's shipped default allows only `http://localhost:3000`. A preflight failure
    is invisible in the page and obvious in the console, which is the worst combination for a first run.
    """
    from pathlib import Path

    from dsa_evaluation import ui

    for key in ("DSA_CORS_ORIGINS", "DSA_LLM_MODE", "DSA_DEMO_SEEDING", "NEXT_PUBLIC_API_URL"):
        monkeypatch.delenv(key, raising=False)

    env = ui.environment_for(Path("apps/web"), tmp_path, 8000, 3000)
    origins = env["DSA_CORS_ORIGINS"].split(",")
    assert "http://localhost:3000" in origins, f"the shipped default origin is missing: {origins}"
    assert "http://127.0.0.1:3000" in origins, (
        f"the URL this command prints is not an allowed origin, so following it breaks every request: {origins}"
    )

    named = ui.environment_for(Path("apps/web"), tmp_path, 8000, 3001, host="192.168.1.20")
    assert "http://192.168.1.20:3001" in named["DSA_CORS_ORIGINS"], named["DSA_CORS_ORIGINS"]

    monkeypatch.setenv("DSA_CORS_ORIGINS", "https://example.test")
    kept = ui.environment_for(Path("apps/web"), tmp_path, 8000, 3000)
    assert kept["DSA_CORS_ORIGINS"] == "https://example.test", (
        "an operator's explicit origin list was overwritten by a default"
    )


def test_the_origin_probe_reads_an_origin_and_not_a_placeholder(tmp_path) -> None:
    """The instrument that refuses a mismatched `--api-port` must not be fooled by interface text.

    Found the hard way: the settings page's Ollama placeholder, `http://localhost:11434/v1`, compiled into a
    chunk made both this probe and the browser tour read a *described* endpoint as the *configured* origin, so
    the tour refused to run against a bundle that was in fact correct. A bare origin is the signal; a path means
    somebody is talking about an endpoint rather than calling one.
    """
    from dsa_evaluation.ui import baked_api_port

    chunks = tmp_path / ".next" / "static" / "chunks"
    chunks.mkdir(parents=True)
    (chunks / "app.js").write_text(
        'const API="http://localhost:8000";'
        'const hint="http://localhost:11434/v1";'
        'const other="http://127.0.0.1:9/v1/chat/completions";',
        encoding="utf-8",
    )
    assert baked_api_port(tmp_path) == 8000, (
        "the probe took a URL with a path for the compiled API origin"
    )

    (chunks / "app.js").write_text('const hint="http://localhost:11434/v1";', encoding="utf-8")
    assert baked_api_port(tmp_path) is None, (
        "with only a placeholder in the bundle the probe still claimed to have found an origin"
    )
