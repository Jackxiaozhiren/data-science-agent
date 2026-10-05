"""§116, Phase 4 target 2 seam #8: money lives apart from transport.

``dsa_llm/providers.py`` held the pricing estimate, the spend ceiling and the call log next to the HTTP
clients -- 503 lines in one module, with the cost controls (§96's refusal-on-unparseable-cap fix)
buried between two provider classes whose ``stream`` and ``metadata`` methods are byte-identical to
each other. The ceiling is a control a reviewer has to be able to find; it now has its own module.

Red on arrival: `dsa_llm.cost` does not exist.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LLM_SRC = REPO / "packages" / "llm" / "src" / "dsa_llm"

COST_NAMES = (
    "_CALL_LOG",
    "reset_call_log",
    "get_call_log",
    "_usd_for_usage",
    "_SPEND_CAP_ENV",
    "_spend_cap_usd",
)


def _top_level_defs(path: Path) -> set[str]:
    """Names bound at import time, `AnnAssign` included -- §114's lesson: `_CALL_LOG: list[...] = []`
    is annotated, and a helper that read only `Assign` would report it as absent."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            found.add(node.name)
        elif isinstance(node, ast.Assign):
            found |= {str(t.id) for t in node.targets if isinstance(t, ast.Name)}
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            found.add(node.target.id)
    return found


def test_cost_owns_the_money_and_the_call_log() -> None:
    cost = LLM_SRC / "cost.py"
    assert cost.is_file(), "dsa_llm.cost does not exist"
    defined = _top_level_defs(cost)
    missing = [n for n in COST_NAMES if n not in defined]
    assert not missing, f"cost.py does not define: {missing}"


def test_providers_no_longer_defines_them() -> None:
    """A second `_CALL_LOG` would be two logs, and a second ceiling would be two policies."""
    defined = _top_level_defs(LLM_SRC / "providers.py")
    leftover = [n for n in COST_NAMES if n in defined]
    assert not leftover, f"providers.py still defines the cost surface: {leftover}"


def test_cost_does_not_import_the_transport_module() -> None:
    tree = ast.parse((LLM_SRC / "cost.py").read_text(encoding="utf-8"))
    modules = {(n.module or "") for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | {
        a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
    }
    assert not [m for m in modules if m.endswith("providers")], sorted(modules)


def test_the_single_container_the_fixture_clears_is_the_one_the_writers_append_to() -> None:
    """`_CALL_LOG` is one of §87's four process-global containers, wherever it now lives."""
    conftest = REPO / "conftest.py"
    tree = ast.parse(conftest.read_text(encoding="utf-8"))
    entry = next(
        n
        for n in tree.body
        if isinstance(n, ast.Assign)
        and any(getattr(t, "id", "") == "_ISOLATED_GLOBALS" for t in n.targets)
    )
    pairs = {
        (ast.literal_eval(elt.elts[0]), ast.literal_eval(elt.elts[1]))
        for elt in entry.value.elts
        if isinstance(elt, ast.Tuple)
    }
    assert ("dsa_llm.cost", "_CALL_LOG") in pairs, pairs
    assert ("dsa_llm.providers", "_CALL_LOG") not in pairs, pairs

    from dsa_llm import cost, providers

    assert providers._CALL_LOG is cost._CALL_LOG, "providers holds a copy, not the live list"
    assert providers.get_call_log is cost.get_call_log
    assert providers.reset_call_log is cost.reset_call_log
    cost._CALL_LOG.clear()
    cost._CALL_LOG.append({"model": "seam-probe"})
    assert providers.get_call_log() == [{"model": "seam-probe"}]
    providers.reset_call_log()
    assert providers.get_call_log() == []


def test_the_benchmark_harness_reaches_the_log_through_its_real_path() -> None:
    """`dsa_evaluation.runner` imports the log helpers from `dsa_llm.providers`, inside a function body.

    Executed here as the same statement, because a lazy import that no longer resolves fails only
    when a benchmark runs -- not at collection, and not in the unit suite.
    """
    src = (REPO / "packages/evaluation/src/dsa_evaluation/runner.py").read_text(encoding="utf-8")
    assert "from dsa_llm.providers import get_call_log, reset_call_log" in src, (
        "the evaluation harness's import line changed shape; update this pin to whatever it now runs"
    )
    from dsa_llm.providers import get_call_log, reset_call_log

    reset_call_log()
    assert get_call_log() == []
