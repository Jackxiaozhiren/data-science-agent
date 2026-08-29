from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dataset_snapshot(root: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    files = sorted(path for path in root.rglob("*") if path.is_file())
    for path in files:
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(_sha256_file(path)))
    return digest.hexdigest(), len(files)


def main() -> None:
    catalog = Path("benchmarks/ds-agent-benchmark/catalog.json")
    datasets = Path("benchmarks/ds-agent-benchmark/datasets")
    out = Path(os.environ["OUT_DIR"])
    out.mkdir(parents=True, exist_ok=True)

    datasets_sha256, dataset_file_count = _dataset_snapshot(datasets)
    manifest = {
        "workflow": "Real Model Evaluation Smoke",
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "git_commit": os.environ.get("GITHUB_SHA"),
        "variant": os.environ["VARIANT"],
        "model": os.environ["DSA_OPENAI_MODEL"],
        "scope": os.environ["RUN_SCOPE"],
        "task_limit": int(os.environ["TASK_LIMIT"]),
        "catalog": str(catalog),
        "catalog_sha256": _sha256_file(catalog),
        "datasets_dir": str(datasets),
        "datasets_sha256": datasets_sha256,
        "dataset_file_count": dataset_file_count,
        "input_cost_per_million": os.environ["DSA_INPUT_COST_PER_MILLION"],
        "output_cost_per_million": os.environ["DSA_OUTPUT_COST_PER_MILLION"],
        "pricing_reference_date": os.environ["PRICING_REFERENCE_DATE"],
    }
    (out / "workflow_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
