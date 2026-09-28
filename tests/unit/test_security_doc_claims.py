"""SECURITY.md describes controls by pointing at source; those pointers must resolve.

The Sandbox Model section cited ``packages/execution/file_validator.py`` and
``sql_validator.py``, neither of which has ever existed, and named a
``PROMPT_INJECTION_PATTERNS`` symbol that is really ``_INJECTION_PATTERNS``. A
security document whose references do not resolve cannot be checked by the
reviewer it is written for, so the check belongs in CI rather than in prose.
"""

from __future__ import annotations

import ast
import os
import pathlib
import re

_SECURITY_DOC = pathlib.Path("SECURITY.md")
_PATH_LIKE = re.compile(r"`([^`\s]+\.(?:py|yml|yaml|toml|json|md|ts|tsx|mjs))`")
_SOURCE_ROOTS = ("packages", "apps", "src", "tests", "scripts", "docs", ".github", "release")


def _resolves(token: str) -> bool:
    """A cited file exists at that path, or (bare name) exists somewhere in the source tree."""
    if pathlib.Path(token).is_file():
        return True
    if "/" in token:
        return False
    name = pathlib.Path(token).name
    for root in _SOURCE_ROOTS:
        base = pathlib.Path(root)
        if not base.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in {"_vendor", "__pycache__", ".venv"}]
            if name in filenames and "_vendor" not in dirpath:
                return True
    return False


def test_security_md_cites_real_files() -> None:
    cited = sorted(set(_PATH_LIKE.findall(_SECURITY_DOC.read_text(encoding="utf-8"))))
    assert cited, "SECURITY.md cites no files, so this test checks nothing"
    missing = [p for p in cited if not _resolves(p)]
    assert not missing, f"SECURITY.md points at files that do not exist: {missing}"

    # Negative control: the reason the guard exists must still be unresolvable.
    assert not _resolves("file_validator.py"), (
        "the phantom validator is back, so a passing assertion proves nothing"
    )
    assert not _resolves("sql_validator.py"), "the phantom SQL validator is back"


def test_sandbox_section_symbol_claims_resolve() -> None:
    """Each identifier the section names must exist in the module that owns it."""
    from dsa_agent.state import Budget
    from dsa_execution import guardrails, python_sandbox

    section = (
        _SECURITY_DOC.read_text(encoding="utf-8")
        .split("## Sandbox Model", 1)[1]
        .split("\n## ", 1)[0]
    )

    assert hasattr(guardrails, "_INJECTION_PATTERNS"), "guardrails lost its pattern list"
    assert hasattr(guardrails, "contains_prompt_injection"), "guardrails lost its predicate"

    src = pathlib.Path("packages/execution/src/dsa_execution/python_sandbox.py").read_text(
        encoding="utf-8"
    )
    funcs = {
        n.name
        for n in ast.walk(ast.parse(src))
        if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
    }
    assert "_safe_import" in funcs, "the doc's named import hook is gone from the sandbox"
    denied = python_sandbox._DENY_IMPORTS | python_sandbox._DENY_ATTRS | python_sandbox._DENY_NAMES
    for tok in ("os", "subprocess", "socket", "requests", "eval", "exec", "open", "__import__"):
        assert tok in denied, (
            f"SECURITY.md lists {tok!r} as denied but the sandbox does not deny it"
        )
    for mod in (
        "polars",
        "numpy",
        "math",
        "statistics",
        "json",
        "re",
        "datetime",
        "collections",
        "itertools",
    ):
        assert mod in python_sandbox._ALLOW_IMPORTS, f"doc claims {mod!r} is allowed; it is not"

    budget_fields = set(Budget.model_fields)
    claimed = set(re.findall(r"\bmax_\w+\b", section))
    assert claimed == {"max_steps", "max_tool_calls", "max_retries"}, (
        f"the doc's budget sentence changed shape, so re-read it: {sorted(claimed)}"
    )
    for knob in claimed:
        assert knob in budget_fields, (
            f"SECURITY.md claims a budget {knob!r} Budget does not declare"
        )

    # Negative control: the phantom name this guard replaced must stay nonexistent.
    assert not hasattr(guardrails, "PROMPT_INJECTION_PATTERNS"), (
        "the phantom symbol returned, so the assertions above prove nothing"
    )
    assert "PROMPT_INJECTION_PATTERNS" not in section, "the doc re-advertised the phantom name"
