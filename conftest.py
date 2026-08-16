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
