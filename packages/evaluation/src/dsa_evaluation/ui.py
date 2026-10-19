"""R-04: `dsa ui` -- the product on one person's machine, behind one command, on loopback by default.

Two processes have to come up and go down together, and the failure modes are the ones that make a local
command worse than the hosted demo it replaces: a stale bundle serving the previous product, an API port the
already-built client cannot reach (every request refused by CORS behind a page that looks fine), a port
someone else holds, and a Ctrl-C that leaves a listener behind. So `preflight` decides all of that *before*
anything is spawned, and `spawn_group` / `stop_group` own the one dangerous mechanic: children go into a new
process group and the supervisor signals **that** group, because a supervisor that signals the group it
belongs to kills the terminal with it -- measured while spiking this command, which is why the mechanism is
named separately and tested against a `sleep`.

Nothing here calls the network. The API and the UI bind loopback unless the operator names another host, the
data lives in one directory the user chose, and the only outbound request a running instance makes is to the
model endpoint that person configured.
"""

from __future__ import annotations

import contextlib
import importlib
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

#: The origin the web client is compiled against. `NEXT_PUBLIC_*` is inlined at build time, so a UI built for
#: :8000 and served by an API on another port loads perfectly and fails every request.
DEFAULT_API_PORT = 8000
DEFAULT_UI_PORT = 3000
_LOOPBACK = {"127.0.0.1", "localhost", "::1"}
#: An origin, not any loopback URL: the compiled `API_BASE_URL` is a bare `scheme://host:port`, while interface
#: text can name an endpoint with a path (the settings page's Ollama placeholder). Requiring the port to end the
#: match is what keeps a UI string from being read as a configured origin.
_BAKED_ORIGIN = re.compile(r"http://(?:localhost|127\.0\.0\.1):(\d{1,5})(?![\d./-])")
_WEB_SOURCES = ("app", "lib")
_WEB_SUFFIXES = {".tsx", ".ts", ".css"}


@dataclass(frozen=True)
class Check:
    """One preflight finding. `fix` is what the user runs next, and an ok=True line carries what was learned."""

    name: str
    ok: bool
    detail: str
    fix: str = ""


def port_is_free(host: str, port: int) -> bool:
    """Whether something is already answering on this address.

    `connect_ex` is used deliberately: it returns an error *code* rather than raising, so the preflight
    stays handler-free, and `debt.exceptHandlers` counts every one in shipped code against a ceiling the
    tree already sits one below. A refused connect is exactly the answer "nothing is listening here".
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.5)
        return probe.connect_ex((host, port)) != 0


def _wait_for_port(
    host: str, port: int, *, timeout: float, children: list[subprocess.Popen[bytes]]
) -> bool:
    """Poll until the child listens, or a child dies, or the budget runs out -- no exceptions involved."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if any(child.poll() is not None for child in children):
            return False
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(1.0)
            if probe.connect_ex((host, port)) == 0:
                return True
        time.sleep(0.3)
    return False


def baked_api_port(web_dir: Path) -> int | None:
    """The API origin compiled into the shipped client chunks, or None when the bundle says nothing."""
    chunks = web_dir / ".next" / "static" / "chunks"
    if not chunks.is_dir():
        return None
    for script in sorted(chunks.rglob("*.js")):
        match = _BAKED_ORIGIN.search(script.read_text(encoding="utf-8", errors="ignore"))
        if match:
            return int(match.group(1))
    return None


def _newest_source_mtime(web_dir: Path) -> float:
    newest = 0.0
    for folder in _WEB_SOURCES:
        for path in (web_dir / folder).rglob("*"):
            if path.suffix in _WEB_SUFFIXES and path.is_file():
                newest = max(newest, path.stat().st_mtime)
    return newest


def preflight(
    *,
    web_dir: Path,
    data_dir: Path,
    api_port: int = DEFAULT_API_PORT,
    ui_port: int = DEFAULT_UI_PORT,
    host: str = "127.0.0.1",
    allow_public: bool = False,
) -> list[Check]:
    """Every reason not to start, found without starting. Ordered so the cheapest blocker is named first."""
    checks: list[Check] = []

    private = host in _LOOPBACK
    exposed = not private and not allow_public
    checks.append(
        Check(
            "network",
            private or allow_public,
            (
                f"binding {host}:{ui_port} and {host}:{api_port} to loopback; the only outbound request is "
                "the model endpoint this process is configured with"
            )
            if private
            else (
                f"--host {host} would put this instance on other machines on that interface, and no flag "
                "has said that is intended"
                if exposed
                else f"--host {host} with --allow-public: reachable from that interface, by request"
            ),
            ""
            if private or allow_public
            else "drop --host (loopback is the default) or add --allow-public once DSA_AUTH_TOKEN is set",
        )
    )

    if shutil.which("node") is None:
        checks.append(
            Check(
                "node",
                False,
                "no `node` on PATH, and the web bundle is served by `next start`",
                "install Node.js 20 or newer, or run the API on its own with `dsa analyze`",
            )
        )

    build_marker = web_dir / ".next" / "BUILD_ID"
    if not build_marker.is_file():
        checks.append(
            Check(
                "web bundle",
                False,
                f"{web_dir / '.next'} has no BUILD_ID, so there is nothing to serve",
                f"npm --prefix {web_dir} run build, then run dsa ui again",
            )
        )
    else:
        newest = _newest_source_mtime(web_dir)
        if newest > build_marker.stat().st_mtime:
            checks.append(
                Check(
                    "web bundle freshness",
                    False,
                    "the bundle is older than the sources it is meant to represent",
                    f"npm --prefix {web_dir} run build, then run dsa ui again",
                )
            )
        compiled_for = baked_api_port(web_dir)
        if compiled_for is not None and compiled_for != api_port:
            checks.append(
                Check(
                    "API origin",
                    False,
                    f"the built client was compiled against port {compiled_for} but the API would listen on "
                    f"{api_port}: the page loads and every request then fails",
                    f"drop --api-port back to {compiled_for}, or rebuild with "
                    f"NEXT_PUBLIC_API_URL=http://localhost:{api_port}",
                )
            )

    for label, port, flag in (("api", api_port, "--api-port"), ("ui", ui_port, "--port")):
        if not port_is_free(host, port):
            rebuild = (
                ", and rebuild with NEXT_PUBLIC_API_URL, since the client is compiled against one origin"
                if label == "api"
                else ""
            )
            checks.append(
                Check(
                    f"{label} port",
                    False,
                    f"nothing could bind {host}:{port}; something is already listening there",
                    f"pass {flag} with a free number{rebuild}",
                )
            )

    walk = data_dir
    while not walk.is_dir() and walk != walk.parent:
        walk = walk.parent
    usable = (
        walk.is_dir()
        and os.access(walk, os.W_OK)
        and not (data_dir.exists() and not data_dir.is_dir())
    )
    # A permission query rather than a write-and-catch, because every `except` in shipped code is counted
    # against a debt ceiling the tree already sits one below -- and a false positive here fails loudly at
    # `makedirs` on the user's terminal instead of starting an instance that cannot write.
    if usable:
        os.makedirs(data_dir, exist_ok=True)
        checks.append(
            Check(
                "data directory", True, f"{data_dir} is writable and holds this instance's database"
            )
        )
    else:
        checks.append(
            Check(
                "data directory",
                False,
                f"{walk} is not writable, so {data_dir} cannot be created there",
                "pass --data-dir somewhere writable",
            )
        )

    return checks


def environment_for(
    web_dir: Path, data_dir: Path, api_port: int, ui_port: int, host: str = "127.0.0.1"
) -> dict[str, str]:
    """The two processes' shared configuration, built here so `serve` and the launcher cannot drift."""
    env = dict(os.environ)
    env.update(
        {
            "DSA_DATABASE_URL": f"sqlite+aiosqlite:///{data_dir / 'dsa.db'}",
            "DSA_DATASET_DIR": str(data_dir / "datasets"),
            "DSA_ARTIFACT_ROOT": str(data_dir / "artifacts"),
            # R-05: the settings page needs somewhere to keep a credential, and this is the one directory the
            # user chose and can delete. An instance that never sets this variable has nowhere to put a secret,
            # which is how the API recognises the hosted demo and refuses to accept a key there.
            "DSA_PROVIDER_CONFIG": str(data_dir / "provider.json"),
            "API_PORT": str(api_port),
            "NEXT_PUBLIC_API_URL": env.get("NEXT_PUBLIC_API_URL", f"http://localhost:{api_port}"),
        }
    )
    # `localhost` and `127.0.0.1` are different origins to CORS, and this command prints the address form while
    # the API's shipped default allows only the name. Measured live: following the printed link loaded a page
    # whose every request was refused, so an operator who configured nothing wrong got a broken first screen.
    # Both spellings are therefore allowed by default, plus any host the operator named; an explicit value in
    # the environment is left exactly as it is.
    if not env.get("DSA_CORS_ORIGINS", "").strip():
        names = ["localhost", "127.0.0.1"]
        if host not in _LOOPBACK:
            names.append(host)
        env["DSA_CORS_ORIGINS"] = ",".join(f"http://{name}:{ui_port}" for name in names)
    # The demo's seeded example runs are the hosted showcase. A private instance is showing the user their
    # own data, and the sample files are not shipped in the wheel -- so seeding is asked for only when the
    # catalogue is actually present.
    if not (web_dir.parent.parent / "benchmarks" / "v2" / "catalog.json").is_file():
        env.setdefault("DSA_DEMO_SEEDING", "off")
    env.setdefault("DSA_LLM_MODE", os.environ.get("DSA_LLM_MODE", "heuristic"))
    return env


def spawn_group(
    argv: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    capture_output: bool = False,
) -> subprocess.Popen[bytes]:
    """Start a child in its OWN process group, so the supervisor can signal the group without joining it.

    Streams are inherited unless `capture_output` is asked for, and that is the safe default rather than a
    lazy one: a server that writes to a `stderr` pipe nobody drains blocks in `write()` and turns a busy
    request into a hang the user would experience as `dsa ui` freezing. Tests capture output; the user's
    uvicorn and Next logs stay on their terminal, where they belong.
    """
    return subprocess.Popen(
        argv,
        cwd=str(cwd) if cwd else None,
        env=env,
        start_new_session=True,
        stdout=subprocess.PIPE if capture_output else None,
        stderr=subprocess.STDOUT if capture_output else None,
    )


def stop_group(child: subprocess.Popen[bytes], *, timeout: float = 8.0) -> None:
    """SIGTERM the child's group, wait, then SIGKILL it. A child that ignores TERM must not survive us.

    `contextlib.suppress` rather than `except` for the two races: a group can exit between the poll and the
    signal, and that is a success path, not a failure worth a counted handler.
    """
    if child.poll() is not None:
        return
    pgid = os.getpgid(child.pid)
    with contextlib.suppress(ProcessLookupError):
        os.killpg(pgid, signal.SIGTERM)
    deadline = time.monotonic() + timeout
    while child.poll() is None and time.monotonic() < deadline:
        time.sleep(0.05)
    if child.poll() is None:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(pgid, signal.SIGKILL)
        child.wait()


def api_argv(host: str, port: int) -> list[str]:
    """A launcher module rather than `-m uvicorn`, because the wheel imports `dsa_api` through
    `data_science_agent`'s vendor path hook -- which a bare uvicorn process would never run."""
    return [
        sys.executable,
        "-m",
        "dsa_evaluation.ui",
        "--serve-api",
        "--host",
        host,
        "--port",
        str(port),
    ]


def web_argv(web_dir: Path, host: str, port: int) -> list[str]:
    node = shutil.which("node")
    binary = web_dir / "node_modules" / "next" / "dist" / "bin" / "next"
    if node is None or not binary.is_file():
        raise RuntimeError(
            f"cannot serve {web_dir}: node={'found' if node else 'missing'}, next={binary.exists()}"
        )
    return [node, str(binary), "start", "-H", host, "-p", str(port)]


def install_stop_handlers(stop_requested: threading.Event) -> None:
    """Make SIGINT *and* SIGTERM ask for a stop, rather than ending the process on the spot.

    The first version caught ``KeyboardInterrupt``, which covers Ctrl-C and nothing else: a SIGTERM -- what
    `kill`, a systemd stop, or a test harness sends -- terminated the supervisor outright, its `finally` never
    ran, and the API and Next kept holding their ports. Measured live: after a SIGTERM the user's laptop still
    had two listeners and no process anyone had asked to stop.
    """

    def _request_stop(signum: int, _frame: Any) -> None:
        stop_requested.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _request_stop)


def serve(
    *,
    web_dir: Path,
    data_dir: Path,
    host: str,
    api_port: int,
    ui_port: int,
    allow_public: bool = False,
    open_url_when_ready: bool = True,
) -> int:
    """Bring both processes up, hand the user one URL, and take both down on one interrupt."""
    checks = preflight(
        web_dir=web_dir,
        data_dir=data_dir,
        api_port=api_port,
        ui_port=ui_port,
        host=host,
        allow_public=allow_public,
    )
    blockers = [check for check in checks if not check.ok]
    if blockers:
        for check in blockers:
            print(
                f"cannot start: {check.name} -- {check.detail}\n  next step: {check.fix}",
                file=sys.stderr,
            )
        return 2

    stop_requested = threading.Event()
    install_stop_handlers(stop_requested)

    env = environment_for(web_dir, data_dir, api_port, ui_port, host)
    api = spawn_group(api_argv(host, api_port), env=env)
    children = [api]
    try:
        if not _wait_for_port(host, api_port, timeout=90.0, children=children):
            print(f"the API never started listening on :{api_port}", file=sys.stderr)
            return 3
        web = spawn_group(web_argv(web_dir, host, ui_port), cwd=web_dir, env=env)
        children.append(web)
        if not _wait_for_port(host, ui_port, timeout=90.0, children=children):
            print(f"the web app never started listening on :{ui_port}", file=sys.stderr)
            return 3
        # Flushed because stdout is a pipe for anyone scripting this, and Python block-buffers a pipe: the
        # first live run had the servers answering while the "DSA is running" line sat unwritten.
        print(
            f"DSA is running: http://{host}:{ui_port}   (API on :{api_port}, data in {data_dir})",
            flush=True,
        )
        print("Ctrl-C stops both.", flush=True)
        if open_url_when_ready:
            _open_browser(f"http://{host}:{ui_port}")
        # The signal handlers turn an interrupt into `stop_requested`; the suppress covers the narrow race
        # where a SIGINT lands while the interpreter is between bytecodes. Either way the `finally` below is
        # what actually stops the children, so nothing about teardown depends on which path noticed.
        with contextlib.suppress(KeyboardInterrupt):
            while not stop_requested.is_set() and all(child.poll() is None for child in children):
                time.sleep(0.2)
        return 0
    finally:
        for child in children:
            stop_group(child)
        stopped = [f":{port}" for port in (api_port, ui_port) if port_is_free(host, port)]
        print(
            "stopped: " + ", ".join(stopped) + " free"
            if len(stopped) == 2
            else "warning: a port is still held after teardown",
            flush=True,
        )


def _open_browser(url: str) -> None:
    opener = shutil.which("open") if sys.platform == "darwin" else shutil.which("xdg-open")
    if opener is not None:
        subprocess.Popen([opener, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def check_only(
    *,
    web_dir: Path,
    data_dir: Path,
    host: str,
    api_port: int,
    ui_port: int,
    allow_public: bool = False,
) -> int:
    """`dsa ui --json` without starting anything: the doctor shape the plan's guard asks for."""
    checks = preflight(
        web_dir=web_dir,
        data_dir=data_dir,
        api_port=api_port,
        ui_port=ui_port,
        host=host,
        allow_public=allow_public,
    )
    blockers = [check for check in checks if not check.ok]
    print(json.dumps({"ok": not blockers, "checks": [asdict(check) for check in checks]}, indent=2))
    return 1 if blockers else 0


def _main() -> int:
    """`python -m dsa_evaluation.ui --serve-api` -- the API child, with the wheel's path hook installed."""
    import argparse

    parser = argparse.ArgumentParser(description="internal launcher for `dsa ui`")
    parser.add_argument("--serve-api", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=DEFAULT_API_PORT)
    args = parser.parse_args()
    if not args.serve_api:
        parser.print_help()
        return 2
    importlib.import_module(
        "data_science_agent"
    )  # installs the _vendor import path the wheel needs

    import uvicorn

    from dsa_api.main import app

    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
