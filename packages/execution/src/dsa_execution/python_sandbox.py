from __future__ import annotations

import ast
import io
import sys
import time
import traceback
from contextlib import redirect_stderr, redirect_stdout
from typing import Any

from dsa_tools.errors import ToolExecutionError

_DENY_IMPORTS = {"os", "subprocess", "socket", "requests", "urllib", "httpx", "shutil", "pathlib", "sys", "eval", "exec", "open"}
_DENY_ATTRS = {"system", "popen", "call", "run", "exec", "eval", "__import__", "open", "socket", "connect"}
_DENY_NAMES = {"eval", "exec", "open", "__import__", "compile", "input"}


class SandboxViolation(ToolExecutionError):
    pass


def _check_ast(code: str) -> None:
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise SandboxViolation(f"SyntaxError: {e}") from e

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in _DENY_IMPORTS:
                    raise SandboxViolation(f"Import denied: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] in _DENY_IMPORTS:
                raise SandboxViolation(f"ImportFrom denied: {node.module}")
        elif isinstance(node, ast.Call):
            # detect __import__, eval, exec, open directly
            if isinstance(node.func, ast.Name) and node.func.id in _DENY_NAMES:
                raise SandboxViolation(f"Call denied: {node.func.id}()")
            if isinstance(node.func, ast.Attribute) and node.func.attr in _DENY_ATTRS:
                raise SandboxViolation(f"Attribute call denied: .{node.func.attr}()")


_ALLOWED_GLOBALS: dict[str, Any] = {}


def _build_safe_globals() -> dict[str, Any]:
    # minimal safe builtins
    import math
    import statistics

    import numpy as np
    import polars as pl

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
        "__import__": None,  # block dynamic import
    }
    return {
        "__builtins__": safe_builtins,
        "pl": pl,
        "np": np,
        "math": math,
        "statistics": statistics,
    }


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
    # timeout is best-effort via wall clock check inside? For MVP, synchronous exec + wall check
    local_vars: dict[str, Any] = {}
    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exec(code, g, local_vars)  # noqa: S102
    except SandboxViolation:
        raise
    except Exception as e:
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
