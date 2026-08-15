from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from dsa_datasets.loader import load_dataframe
from dsa_datasets.models import DatasetFormat
from dsa_datasets.profiler import build_profile
from dsa_datasets.validate import detect_format
from dsa_tools.base import BaseTool
from dsa_tools.errors import ToolExecutionError


class ProfileDatasetInput(BaseModel):
    path: str = Field(description="Absolute path to dataset file")
    dataset_id: str | None = None
    filename: str | None = None


class ProfileDatasetOutput(BaseModel):
    dataset_id: str
    profile: dict[str, Any]


class ProfileDatasetTool(BaseTool[ProfileDatasetInput, ProfileDatasetOutput]):
    name = "profile_dataset"
    description = "Profile a dataset file (schema, missing, duplicates, cardinality, distribution)"
    input_model = ProfileDatasetInput
    output_model = ProfileDatasetOutput

    async def execute(self, inp: ProfileDatasetInput) -> ProfileDatasetOutput:
        p = Path(inp.path)
        if not p.exists():
            raise ToolExecutionError(f"File not found: {inp.path}")
        # safety: block path traversal patterns; allow Data agent + system tmp for tests
        raw = inp.path
        if ".." in raw or raw.count("//") > 0:
            raise ToolExecutionError("Path traversal detected")
        fmt = detect_format(inp.filename or p.name)
        # use dataset_id from input or filename-based
        ds_id = inp.dataset_id or p.stem
        # leverage profiler quick path
        from dsa_datasets.profiler import quick_profile_for_path

        _df, profile = quick_profile_for_path(p, fmt, ds_id)
        return ProfileDatasetOutput(dataset_id=profile.dataset_id, profile=profile.model_dump(mode="json"))
