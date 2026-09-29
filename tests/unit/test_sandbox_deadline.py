"""The sandbox's ``timeout_ms`` must be able to interrupt, not only label a finished run.

Before this, the check lived *after* ``exec`` returned: an infinite loop never returned, so the
"5s wall-clock" that SECURITY.md and the sandbox docstring advertise was reporting, not
containment. Measured directly: ``while True`` with ``timeout_ms=100`` ran past a 12 s CPU rlimit
and died on SIGXCPU without ever returning.

Runs go through a spawned child so the test can never hang CI -- a regression here is an
infinite loop by construction, and an assertion that can only be reached by waiting forever is
not a check.
"""

from __future__ import annotations

import multiprocessing
import time

from dsa_execution.python_sandbox import SandboxViolation, execute_python


def _child(code: str, timeout_ms: int, q) -> None:
    try:
        res = execute_python(code, timeout_ms=timeout_ms)
    except SandboxViolation as exc:  # the only exception this API propagates
        q.put(("violation", str(exc), None))
        return
    q.put(("returned", res.get("error"), res.get("duration_ms")))


def _run(code: str, timeout_ms: int, wall_s: float = 15.0):
    """Return (kind, message, duration_ms), or (None, "no return", None) if the child is stuck."""
    ctx = multiprocessing.get_context("spawn")
    q = ctx.SimpleQueue()
    p = ctx.Process(target=_child, args=(code, timeout_ms, q), daemon=True)
    p.start()
    deadline = time.monotonic() + wall_s
    while time.monotonic() < deadline:
        if not q.empty():
            item = q.get()
            p.join(5)
            if p.is_alive():
                p.terminate()
            return item
        time.sleep(0.05)
    p.terminate()
    p.join(5)
    return (None, "no return within the wall clock", None)


def test_infinite_loop_is_interrupted_near_its_budget() -> None:
    kind, message, duration = _run("i = 0\nwhile True:\n    i += 1\n", 200)
    assert kind is not None, (
        "execute_python never returned -- the sandbox still cannot preempt, only label"
    )
    assert kind in ("violation", "returned"), kind
    assert message and "ime" in message, f"no timeout surfaced: {kind} {message!r}"
    assert duration is None or duration < 5000, f"overran its 200ms budget by {duration}ms"


def test_short_loop_is_unaffected() -> None:
    kind, message, _ = _run("t = 0\nfor k in range(50):\n    t += k\nprint(t)\n", 5000)
    assert kind == "returned", f"{kind}: {message}"
    assert message is None, f"a bounded loop was interrupted: {message}"


def test_deadline_guard_is_installed_by_transform_not_by_prose() -> None:
    """The guard must be a real injected call, so a comment cannot satisfy the check."""
    import ast
    import inspect
    import pathlib

    src = pathlib.Path("packages/execution/src/dsa_execution/python_sandbox.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(src)
    transformers = [
        n.name
        for n in ast.walk(tree)
        if isinstance(n, ast.ClassDef)
        and any(
            isinstance(base, ast.Attribute) and base.attr == "NodeTransformer" for base in n.bases
        )
    ]
    assert transformers, "no ast.NodeTransformer exists, so loops are not guarded at their heads"
    assert "execute_python" in {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    # sanity: the module still imports and the symbol is the one under test
    assert callable(execute_python)
    assert inspect.signature(execute_python).parameters["timeout_ms"].default == 5000
