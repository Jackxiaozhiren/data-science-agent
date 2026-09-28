def test_imports() -> None:
    import dsa_agent  # noqa: F401
    import dsa_api  # noqa: F401
    import dsa_datasets  # noqa: F401
    import dsa_llm  # noqa: F401

    assert dsa_api.__version__ == "0.1.0"


def test_documented_graph_section_names_resolve() -> None:
    """Symbols the agent doc presents as the graph entry points must exist.

    ``docs/agent.md`` described ``analyze_graph`` as the LangGraph extension's entry
    point; no such function exists anywhere in the code, and the sentence also claimed
    ``langgraph.graph.StateGraph`` is imported "when available" although the module
    imports it unconditionally. A doc that names a nonexistent API is a claim no
    reader can check, which is the failure this project exists to prevent.
    """
    import dsa_agent
    import dsa_agent.langgraph_graph as lg
    import importlib.util
    import pathlib
    import re

    lines = pathlib.Path("docs/agent.md").read_text(encoding="utf-8").splitlines()
    section, inside = [], False
    for line in lines:
        if line.startswith("## "):
            inside = line.strip() == "## Graph"
            continue
        if inside:
            section.append(line)

    def resolves(token: str) -> bool:
        if hasattr(dsa_agent, token) or hasattr(lg, token):
            return True
        try:  # third-party module names are legitimate in prose
            return importlib.util.find_spec(token) is not None
        except (ImportError, ValueError):
            return False

    named = [t for line in section for t in re.findall(r"`([a-z_][a-z0-9_]{3,})`", line)]
    assert named, "the Graph section names no symbol at all, so this test checks nothing"
    unresolved = [t for t in named if not resolves(t)]
    assert not unresolved, f"docs/agent.md names symbols that do not exist: {unresolved}"
    assert not resolves("analyze_graph"), (
        "the guard itself is vacuous: the phantom name still resolved"
    )

    src = pathlib.Path("packages/agent/src/dsa_agent/langgraph_graph.py").read_text(
        encoding="utf-8"
    )
    imports_it = "from langgraph.graph import END, StateGraph" in src.split("\n\n")[0] or bool(
        re.search(r"^from langgraph\.graph import", src, re.M)
    )
    assert imports_it, "the doc's dependency claim should be re-checked if this now differs"
