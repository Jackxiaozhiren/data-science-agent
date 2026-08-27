from __future__ import annotations

from pathlib import Path


def init_project(path: Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    for d in ["datasets", "analyses", "reports", "notebooks"]:
        (p / d).mkdir(exist_ok=True)
    (p / "config.yaml").write_text("version: 1\ndataset: datasets/\n", encoding="utf-8")
    (p / "README.md").write_text(f"# {p.name}\n\nCreated by `dsa init`.\n", encoding="utf-8")
    return p
