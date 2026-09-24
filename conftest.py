import sys
from pathlib import Path

ROOT = Path(__file__).parent
for p in [
    ROOT / "apps/api/src",
    ROOT / "packages/agent/src",
    ROOT / "packages/llm/src",
    ROOT / "packages/datasets/src",
    ROOT / "packages/evaluation/src",
    ROOT / "packages/tools/src",
    ROOT / "packages/execution/src",
    ROOT / "packages/statistics/src",
    ROOT / "packages/ml/src",
    ROOT / "packages/visualization/src",
    ROOT / "packages/evidence/src",
    ROOT / "packages/reports/src",
    ROOT / "packages/mcp/src",
    ROOT / "src",
]:
    if p.exists():
        sys.path.insert(0, str(p))

# Dev truth is workspace source: importing data_science_agent inserts its
# _vendor dir at sys.path[0] (needed for the published wheel), which would
# shadow packages/*/src in tests and split coverage onto the vendored copies.
# Demote _vendor to a fallback so `import dsa_*` resolves to workspace source.
try:
    import data_science_agent  # noqa: F401

    _vendor_dir = str(ROOT / "src" / "data_science_agent" / "_vendor")
    while _vendor_dir in sys.path:
        sys.path.remove(_vendor_dir)
    sys.path.append(_vendor_dir)
except Exception:  # noqa: S110 - best-effort test-only path demotion
    pass
