from __future__ import annotations

import base64
import io
import uuid
from pathlib import Path
from typing import Any, Literal

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import polars as pl
from pydantic import BaseModel, Field

from dsa_datasets.loader import load_dataframe
from dsa_datasets.validate import detect_format
from dsa_tools.base import BaseTool
from dsa_tools.errors import ToolExecutionError


class CreateChartInput(BaseModel):
    dataset_path: str | None = None
    chart_type: Literal["histogram", "bar", "scatter", "line", "boxplot", "heatmap"] = "histogram"
    x: str | None = None
    y: str | None = None
    group_by: str | None = None
    bins: int = Field(default=30, ge=5, le=100)


class CreateChartOutput(BaseModel):
    chart_type: str
    artifact_path: str
    base64_png: str
    diagnostics: dict[str, Any] = Field(default_factory=dict)


def _artifacts_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "artifacts" / "charts"


class CreateChartTool(BaseTool[CreateChartInput, CreateChartOutput]):
    name = "create_chart"
    description = "Create a chart (histogram/bar/scatter/line/boxplot/heatmap) from a dataset, saves PNG artifact"
    input_model = CreateChartInput
    output_model = CreateChartOutput

    async def execute(self, inp: CreateChartInput) -> CreateChartOutput:
        if not inp.dataset_path:
            raise ToolExecutionError("dataset_path required")
        p = Path(inp.dataset_path)
        if not p.exists():
            raise ToolExecutionError(f"dataset_path not found: {inp.dataset_path}")
        fmt = detect_format(p.name)
        df = load_dataframe(p, fmt)

        # validate columns
        if inp.x and inp.x not in df.columns:
            raise ToolExecutionError(f"x column {inp.x!r} not found")
        if inp.y and inp.y not in df.columns:
            raise ToolExecutionError(f"y column {inp.y!r} not found")

        fig, ax = plt.subplots(figsize=(7, 4.5))
        try:
            if inp.chart_type == "histogram":
                if not inp.x:
                    raise ToolExecutionError("x required for histogram")
                vals = df[inp.x].drop_nulls().to_numpy()
                ax.hist(vals, bins=inp.bins)
                ax.set_xlabel(inp.x)
                ax.set_ylabel("count")
                ax.set_title(f"Histogram of {inp.x}")
            elif inp.chart_type == "bar":
                if not inp.x:
                    raise ToolExecutionError("x required for bar (category)")
                # if y provided, aggregate sum; else count
                if inp.y:
                    agg = df.group_by(inp.x).agg(pl.col(inp.y).sum().alias("agg_y")).sort(inp.x)
                    ax.bar(agg[inp.x].to_list(), agg["agg_y"].to_list())
                    ax.set_ylabel(inp.y)
                else:
                    agg = df.group_by(inp.x).len().sort(inp.x)
                    ax.bar(agg[inp.x].to_list(), agg["len"].to_list())
                    ax.set_ylabel("count")
                ax.set_xlabel(inp.x)
                ax.set_title(f"Bar: {inp.x}" + (f" by {inp.y}" if inp.y else ""))
                plt.xticks(rotation=20, ha="right")
            elif inp.chart_type == "scatter":
                if not inp.x or not inp.y:
                    raise ToolExecutionError("x and y required for scatter")
                sub = df.select([inp.x, inp.y]).drop_nulls()
                ax.scatter(sub[inp.x].to_numpy(), sub[inp.y].to_numpy(), s=12, alpha=0.7)
                ax.set_xlabel(inp.x)
                ax.set_ylabel(inp.y)
                ax.set_title(f"Scatter: {inp.x} vs {inp.y}")
            elif inp.chart_type == "line":
                if not inp.x:
                    raise ToolExecutionError("x required for line")
                # sort by x if numeric/datetime
                sub = df.select([c for c in [inp.x, inp.y] if c]).drop_nulls().sort(inp.x)
                if inp.y:
                    ax.plot(sub[inp.x].to_list(), sub[inp.y].to_list(), marker="o", markersize=3)
                    ax.set_ylabel(inp.y)
                else:
                    ax.plot(sub[inp.x].to_list(), marker="o", markersize=3)
                ax.set_xlabel(inp.x)
                ax.set_title(f"Line: {inp.x}" + (f" vs {inp.y}" if inp.y else ""))
            elif inp.chart_type == "boxplot":
                if not inp.x:
                    raise ToolExecutionError("x required for boxplot")
                if inp.group_by and inp.group_by in df.columns:
                    groups = df[inp.group_by].unique().to_list()
                    data = [
                        df.filter(pl.col(inp.group_by) == g)[inp.x].drop_nulls().to_numpy()
                        for g in groups
                    ]
                    ax.boxplot(data, tick_labels=[str(g) for g in groups])
                    ax.set_xlabel(inp.group_by)
                    ax.set_ylabel(inp.x)
                else:
                    ax.boxplot(df[inp.x].drop_nulls().to_numpy())
                    ax.set_ylabel(inp.x)
                ax.set_title(f"Boxplot: {inp.x}")
            elif inp.chart_type == "heatmap":
                # correlation heatmap for numeric cols
                numeric_cols = [
                    c
                    for c in df.columns
                    if df[c].dtype in (pl.Float64, pl.Float32, pl.Int64, pl.Int32)
                ]
                if len(numeric_cols) < 2:
                    raise ToolExecutionError("Need >=2 numeric columns for heatmap")
                corr = df.select(numeric_cols).corr()
                mat = corr.to_numpy()
                im = ax.imshow(mat, vmin=-1, vmax=1, cmap="RdBu")
                ax.set_xticks(range(len(numeric_cols)), numeric_cols, rotation=30, ha="right")
                ax.set_yticks(range(len(numeric_cols)), numeric_cols)
                plt.colorbar(im, ax=ax, label="correlation")
                ax.set_title("Correlation heatmap")
            else:
                raise ToolExecutionError(f"Unknown chart_type: {inp.chart_type}")

            fig.tight_layout()
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=150)
            plt.close(fig)
            png_bytes = buf.getvalue()
            b64 = base64.b64encode(png_bytes).decode()

            out_dir = _artifacts_dir()
            out_dir.mkdir(parents=True, exist_ok=True)
            fname = f"{uuid.uuid4().hex[:10]}_{inp.chart_type}.png"
            out_path = out_dir / fname
            out_path.write_bytes(png_bytes)

            return CreateChartOutput(
                chart_type=inp.chart_type,
                artifact_path=str(out_path),
                base64_png=b64,
                diagnostics={"x": inp.x, "y": inp.y, "rows": df.height},
            )
        except ToolExecutionError:
            plt.close(fig)
            raise
        except Exception as e:
            plt.close(fig)
            raise ToolExecutionError(f"Chart generation failed: {e}") from e
