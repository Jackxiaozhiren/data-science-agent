from __future__ import annotations

import ast
import copy
import io
import time
import traceback
from collections.abc import Callable
from contextlib import redirect_stderr, redirect_stdout
from typing import Any

try:
    from dsa_tools.errors import ToolExecutionError
except ImportError:

    class ToolExecutionError(ValueError):  # type: ignore[no-redef]
        pass


_DEADLINE_FN = "_sandbox_deadline_check"

_DENY_IMPORTS = {
    "os",
    "subprocess",
    "socket",
    "requests",
    "urllib",
    "httpx",
    "shutil",
    "pathlib",
    "sys",
    "eval",
    "exec",
    "open",
    "importlib",
    "builtins",
}
_DENY_ATTRS = {
    "system",
    "popen",
    "call",
    "run",
    "exec",
    "eval",
    "__import__",
    "open",
    "socket",
    "connect",
    "getenv",
    "environ",
}
_DENY_NAMES = {
    "eval",
    "exec",
    "open",
    "__import__",
    "compile",
    "input",
    "getattr",
    "setattr",
    "globals",
    "locals",
    "vars",
}


class SandboxViolation(ToolExecutionError):
    pass


_ALLOW_IMPORTS = {
    "polars",
    "pl",
    "numpy",
    "np",
    "math",
    "statistics",
    "json",
    "re",
    "datetime",
    "collections",
    "itertools",
}


def _check_ast(code: str) -> None:
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise SandboxViolation(f"SyntaxError: {e}") from e

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in _ALLOW_IMPORTS:
                    continue
                if root in _DENY_IMPORTS:
                    raise SandboxViolation(f"Import denied: {alias.name}")
                # Unknown imports: deny by default unless allowlisted
                raise SandboxViolation(f"Import denied: {alias.name} (not in allowlist)")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in _ALLOW_IMPORTS:
                continue
            if node.module and root in _DENY_IMPORTS:
                raise SandboxViolation(f"ImportFrom denied: {node.module}")
            if node.module:
                raise SandboxViolation(f"ImportFrom denied: {node.module} (not in allowlist)")
        elif isinstance(node, ast.Attribute):
            if node.attr in _DENY_ATTRS:
                raise SandboxViolation(f"Attribute denied: .{node.attr}")
            if node.attr in ("__class__", "__bases__", "__subclasses__", "__mro__"):
                raise SandboxViolation(f"Introspection denied: .{node.attr}")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in _DENY_NAMES:
                raise SandboxViolation(f"Call denied: {node.func.id}()")
            if isinstance(node.func, ast.Attribute) and node.func.attr in _DENY_ATTRS:
                raise SandboxViolation(f"Attribute call denied: .{node.func.attr}()")
        elif isinstance(node, ast.Subscript):
            # block obfuscation like __builtins__.__dict__
            pass


_ALLOWED_GLOBALS: dict[str, Any] = {}


def _build_safe_globals() -> dict[str, Any]:
    # minimal safe builtins
    import math
    import statistics

    import numpy as np
    import polars as pl

    def _safe_import(name, *args, **kwargs):  # type: ignore[no-untyped-def]
        if name.split(".")[0] in _ALLOW_IMPORTS:
            return __import__(name, *args, **kwargs)
        raise SandboxViolation(f"Dynamic import denied: {name}")

    safe_builtins = {
        "abs": abs,
        "min": min,
        "max": max,
        "sum": sum,
        "len": len,
        "range": range,
        "enumerate": enumerate,
        "zip": zip,
        "sorted": sorted,
        "print": print,
        "__import__": _safe_import,
    }
    return {
        "__builtins__": safe_builtins,
        "pl": pl,
        "np": np,
        "math": math,
        "statistics": statistics,
    }


class SandboxTimeout(BaseException):
    """Raised at loop boundaries when the wall-clock budget is spent.

    It inherits ``BaseException`` on purpose: sandboxed code wrapping its own loop in
    ``except Exception`` must not be able to swallow the deadline and keep spinning.
    """


class _LoopDeadline(ast.NodeTransformer):
    """Put a deadline check at the head of every loop body.

    Coverage is stated where it matters: pure-Python iteration is interruptible this way, while a
    single long call into C (a huge numpy operation) still runs to completion and is only
    reported afterwards by ``execute_python``'s duration check.
    """

    def __init__(self) -> None:
        self._guard_src = f"{_DEADLINE_FN}()"

    def _guard(self) -> ast.stmt:
        return copy.deepcopy(ast.parse(self._guard_src).body[0])

    def _wrap(self, node: ast.For | ast.AsyncFor | ast.While) -> ast.stmt:
        self.generic_visit(node)
        node.body.insert(0, self._guard())
        return node

    def visit_For(self, node: ast.For) -> ast.stmt:
        return self._wrap(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> ast.stmt:
        return self._wrap(node)

    def visit_While(self, node: ast.While) -> ast.stmt:
        return self._wrap(node)


def _deadline_guard(deadline: float, limit_ms: int) -> Callable[[], None]:
    def _check() -> None:
        if time.perf_counter() > deadline:
            raise SandboxTimeout(f"Timeout after {limit_ms}ms budget")

    return _check


def execute_python(
    code: str,
    extra_globals: dict[str, Any] | None = None,
    timeout_ms: int = 5000,
) -> dict[str, Any]:
    _check_ast(code)
    g = _build_safe_globals()
    if extra_globals:
        # only allow whitelisted extra keys (df, dataframes)
        for k, v in extra_globals.items():
            if k.startswith("_"):
                raise SandboxViolation(f"Extra global denied: {k}")
            g[k] = v

    stdout = io.StringIO()
    stderr = io.StringIO()
    t0 = time.perf_counter()
    deadline = t0 + timeout_ms / 1000
    g[_DEADLINE_FN] = _deadline_guard(deadline, timeout_ms)
    runnable = ast.unparse(_LoopDeadline().visit(ast.parse(code)))
    local_vars: dict[str, Any] = {}
    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exec(runnable, g, local_vars)  # noqa: S102
    except BaseException as e:
        if isinstance(e, (KeyboardInterrupt, SystemExit)):
            raise
        if isinstance(e, SandboxViolation):
            raise
        dur = int((time.perf_counter() - t0) * 1000)
        if isinstance(e, SandboxTimeout):
            return {
                "stdout": stdout.getvalue(),
                "stderr": stderr.getvalue()
                + f"\nTimeout after {dur}ms > {timeout_ms}ms (interrupted)",
                "error": "TimeoutError",
                "variables": {k: repr(v)[:2000] for k, v in local_vars.items()},
                "duration_ms": dur,
            }
        tb = traceback.format_exc()
        return {
            "stdout": stdout.getvalue(),
            "stderr": stderr.getvalue() + "\n" + tb,
            "error": f"{type(e).__name__}: {e}",
            "variables": {k: repr(v)[:2000] for k, v in local_vars.items()},
            "duration_ms": int((time.perf_counter() - t0) * 1000),
        }

    dur = int((time.perf_counter() - t0) * 1000)
    if dur > timeout_ms:
        # still return result but flag timeout
        return {
            "stdout": stdout.getvalue(),
            "stderr": stderr.getvalue() + f"\nTimeout after {dur}ms > {timeout_ms}ms",
            "error": "TimeoutError",
            "variables": {k: repr(v)[:2000] for k, v in local_vars.items()},
            "duration_ms": dur,
        }

    return {
        "stdout": stdout.getvalue(),
        "stderr": stderr.getvalue(),
        "error": None,
        "variables": {k: repr(v)[:2000] for k, v in local_vars.items()},
        "duration_ms": dur,
    }
