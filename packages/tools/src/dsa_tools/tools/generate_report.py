from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from dsa_tools.base import BaseTool
from dsa_tools.errors import ToolExecutionError


class GenerateReportInput(BaseModel):
    run_id: str
    title: str = Field(default="Analysis Report")
    markdown: str | None = None
    state_json: str | None = Field(default=None, description="Full AnalysisState JSON for appendix; optional")
    include_repro: bool = True


class GenerateReportOutput(BaseModel):
    report_path: str
    experiment_path: str | None = None
    reproduce_path: str | None = None
    notebook_path: str | None = None


class GenerateReportTool(BaseTool[GenerateReportInput, GenerateReportOutput]):
    name = "generate_report"
    description = "Generate report.md + experiment.json + reproduce.sh + analysis.ipynb under artifacts/reports/<run_id>/"
    input_model = GenerateReportInput
    output_model = GenerateReportOutput

    async def execute(self, inp: GenerateReportInput) -> GenerateReportOutput:
        if not inp.run_id.strip():
            raise ToolExecutionError("run_id required")
        root = Path(__file__).resolve().parents[4] / "artifacts" / "reports" / inp.run_id
        root.mkdir(parents=True, exist_ok=True)

        md_path = root / "report.md"
        content = inp.markdown or f"# {inp.title}\n\nRun: {inp.run_id}\n"
        md_path.write_text(content, encoding="utf-8")

        exp_path = None
        repro_path = None
        nb_path = None

        if inp.state_json:
            try:
                state = json.loads(inp.state_json)
                dataset_path = state.get("dataset_path")
                dataset_sha = None
                if dataset_path and Path(dataset_path).exists():
                    try:
                        from dsa_datasets.hash_utils import sha256_file

                        dataset_sha = sha256_file(Path(dataset_path))
                    except Exception:
                        dataset_sha = None
                from dsa_evidence.repro import build_experiment_json, build_notebook_skeleton, build_reproduce_sh

                exp_path_obj = build_experiment_json(
                    run_id=inp.run_id,
                    dataset_path=dataset_path,
                    dataset_sha256=dataset_sha,
                    user_query=state.get("user_query", ""),
                    plan=state.get("plan", []),
                    tool_calls=state.get("tool_calls", []),
                    evidence=state.get("evidence", []),
                    insights=state.get("insights", []),
                    out_dir=root,
                )
                exp_path = str(exp_path_obj)
                if inp.include_repro:
                    repro_path = str(build_reproduce_sh(inp.run_id, dataset_path, state.get("user_query", ""), root))
                nb_path = str(build_notebook_skeleton(inp.run_id, root))
            except Exception as e:
                raise ToolExecutionError(f"Failed to build repro bundle: {e}") from e

        return GenerateReportOutput(
            report_path=str(md_path),
            experiment_path=exp_path,
            reproduce_path=repro_path,
            notebook_path=nb_path,
        )
