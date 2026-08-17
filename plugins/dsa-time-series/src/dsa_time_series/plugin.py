from __future__ import annotations

from dsa_plugins.plugin import BasePlugin


class TimeSeriesPlugin(BasePlugin):
    name = "dsa-time-series"
    version = "1.0.0"
    permissions = ["read", "compute"]

    def register_tools(self) -> list[str]:
        return ["forecast", "backtest", "forecast_viz"]

    def register_models(self) -> list[str]:
        return ["arima", "prophet-stub"]

    def register_evaluators(self) -> list[str]:
        return ["forecast_mae"]


def register() -> TimeSeriesPlugin:
    return TimeSeriesPlugin()
