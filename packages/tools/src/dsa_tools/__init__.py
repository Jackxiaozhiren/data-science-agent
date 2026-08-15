from typing import Any

from dsa_tools.base import BaseTool, ToolResult
from dsa_tools.registry import clear, get, list_tools, register

from dsa_tools.tools.correlation import CorrelationTool
from dsa_tools.tools.create_chart import CreateChartTool
from dsa_tools.tools.evaluate_model import EvaluateModelTool
from dsa_tools.tools.hypothesis_test import HypothesisTestTool
from dsa_tools.tools.profile_dataset import ProfileDatasetTool
from dsa_tools.tools.regression import RegressionTool
from dsa_tools.tools.run_python import RunPythonTool
from dsa_tools.tools.run_sql import RunSQLTool
from dsa_tools.tools.train_model import TrainModelTool


def bootstrap() -> None:
    for t in [
        ProfileDatasetTool(),
        RunSQLTool(),
        RunPythonTool(),
        CorrelationTool(),
        HypothesisTestTool(),
        RegressionTool(),
        TrainModelTool(),
        EvaluateModelTool(),
        CreateChartTool(),
    ]:
        register(t)  # type: ignore[arg-type]


__all__ = ["BaseTool", "ToolResult", "bootstrap", "clear", "get", "list_tools"]

__version__ = "0.1.0"
