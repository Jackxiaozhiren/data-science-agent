from __future__ import annotations

import asyncio
import base64
import io
import uuid
from pathlib import Path
from typing import Any

from dsa_plugins.plugin import BasePlugin

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from sklearn.metrics import mean_absolute_error, mean_squared_error


class TimeSeriesPlugin(BasePlugin):
    """Flagship plugin — fully executable (V4 §27).

    Capabilities (§22): forecast, backtest, metrics, visualization, evidence.
    Permissions (§23): dataset.read, process, artifact.write, filesystem.read (DENY default).
    Integrated into: Agent, SDK, CLI, Benchmark, Report (§27).
    """

    name = "dsa-time-series"
    version = "1.0.0"
    permissions = ["dataset.read", "process", "artifact.write", "filesystem.read"]
    dependencies: list[str] = []

    def register_tools(self) -> list[str]:
        return ["forecast", "backtest", "forecast_viz", "metrics", "evidence"]

    def register_models(self) -> list[str]:
        return ["arima", "prophet-stub", "linear_trend"]

    def register_evaluators(self) -> list[str]:
        return ["forecast_mae", "forecast_rmse", "forecast_mape"]

    # ---- Core (§27) ----
    def forecast(
        self,
        dataset_path: str | Path,
        date_col: str | None = None,
        value_col: str | None = None,
        periods: int = 30,
        method: str = "linear_trend",
    ) -> dict[str, Any]:
        """Forecast (§27) — delegates to dsa_tools ForecastTool.

        Returns ForecastOutput dict with forecast/metrics/diagnostics.
        """
        from dsa_tools.tools.forecast import ForecastInput, ForecastTool

        tool = ForecastTool()
        inp = ForecastInput(
            dataset_path=str(dataset_path),
            date_col=date_col,
            value_col=value_col,
            periods=periods,
            method=method,  # type: ignore[arg-type]
        )
        out = asyncio.run(tool.execute(inp))
        return out.model_dump(mode="json")

    def backtest(
        self,
        dataset_path: str | Path,
        date_col: str | None = None,
        value_col: str | None = None,
        method: str = "linear_trend",
        folds: int = 3,
    ) -> dict[str, Any]:
        """Backtest (§27) — rolling window MAE/RMSE.

        Splits dataset sequentially into folds, each fold holds out last 20% for test.
        Returns per-fold metrics and aggregate.
        """
        from dsa_datasets.loader import load_dataframe
        from dsa_datasets.validate import detect_format
        from dsa_tools.tools.forecast import _detect_cols
        from sklearn.linear_model import LinearRegression

        p = Path(dataset_path)
        if not p.exists():
            raise FileNotFoundError(f"dataset_path not found: {dataset_path}")
        fmt = detect_format(p.name)
        df = load_dataframe(p, fmt)
        date_c, value_c = _detect_cols(df, date_col, value_col)
        sub = df.select([date_c, value_c]).drop_nulls().sort(date_c)
        y = sub[value_c].to_numpy().astype(float)
        n = len(y)
        if n < 20:
            raise ValueError("Need >=20 rows for backtest")
        # sequential folds: each fold extends training window
        fold_size = n // (folds + 1)
        per_fold: list[dict[str, Any]] = []
        for i in range(folds):
            train_end = fold_size * (i + 1)
            test_end = min(train_end + fold_size, n)
            if test_end <= train_end:
                break
            y_train = y[:train_end]
            y_test = y[train_end:test_end]
            t_train = np.arange(train_end).reshape(-1, 1)
            t_test = np.arange(train_end, test_end).reshape(-1, 1)
            if method == "linear_trend":
                m = LinearRegression()
                m.fit(t_train, y_train)
                pred = m.predict(t_test)
            elif method == "moving_average":
                window = min(7, len(y_train))
                ma = float(np.mean(y_train[-window:]))
                pred = np.full_like(y_test, ma, dtype=float)
            else:  # naive
                pred = np.full_like(y_test, float(y_train[-1]), dtype=float)
            mae = float(mean_absolute_error(y_test, pred))
            rmse = float(np.sqrt(mean_squared_error(y_test, pred)))
            mape = float(np.mean(np.abs((y_test - pred) / np.where(y_test == 0, 1, y_test))) * 100)
            per_fold.append(
                {"fold": i + 1, "train_end": train_end, "test_end": test_end, "mae": mae, "rmse": rmse, "mape": mape, "n_test": len(y_test)}
            )
        agg = {
            "mae_mean": float(np.mean([f["mae"] for f in per_fold])) if per_fold else 0.0,
            "rmse_mean": float(np.mean([f["rmse"] for f in per_fold])) if per_fold else 0.0,
            "mae_std": float(np.std([f["mae"] for f in per_fold])) if per_fold else 0.0,
        }
        return {"dataset_path": str(p), "date_col": date_c, "value_col": value_c, "method": method, "folds": per_fold, "aggregate": agg}

    def metrics(self, forecast_result: dict[str, Any] | None = None, y_true: list[float] | None = None, y_pred: list[float] | None = None) -> dict[str, Any]:
        """Metrics (§27) — compute MAE/RMSE/MAPE from forecast holdout or explicit arrays."""
        if forecast_result and "metrics" in forecast_result:
            # passthrough from forecast tool
            base = dict(forecast_result["metrics"])
            # enrich
            if y_true is not None and y_pred is not None:
                base["mae"] = float(mean_absolute_error(y_true, y_pred))
                base["rmse"] = float(np.sqrt(mean_squared_error(y_true, y_pred)))
            return base
        if y_true is not None and y_pred is not None:
            yt = np.array(y_true, dtype=float)
            yp = np.array(y_pred, dtype=float)
            return {
                "mae": float(mean_absolute_error(yt, yp)),
                "rmse": float(np.sqrt(mean_squared_error(yt, yp))),
                "mape": float(np.mean(np.abs((yt - yp) / np.where(yt == 0, 1, yt))) * 100),
            }
        raise ValueError("Provide forecast_result or y_true/y_pred for metrics")

    def forecast_viz(
        self,
        dataset_path: str | Path,
        forecast_result: dict[str, Any] | None = None,
        date_col: str | None = None,
        value_col: str | None = None,
        periods: int | None = None,
    ) -> dict[str, Any]:
        """Visualization (§27) — historical + forecast line chart as PNG artifact.

        Returns {"artifact_path": str, "base64_png": str, "diagnostics": dict}
        Suitable for Notebook (§30) and Report (§27) embedding.
        """
        from dsa_datasets.loader import load_dataframe
        from dsa_datasets.validate import detect_format
        from dsa_tools.tools.forecast import _detect_cols

        p = Path(dataset_path)
        if not p.exists():
            raise FileNotFoundError(f"dataset_path not found: {dataset_path}")
        fmt = detect_format(p.name)
        df = load_dataframe(p, fmt)
        # infer cols if not provided
        if forecast_result:
            date_c = forecast_result.get("date_col") or date_col
            value_c = forecast_result.get("value_col") or value_col
            fc = forecast_result.get("forecast", [])
        else:
            # auto forecast if not provided
            fr = self.forecast(p, date_col, value_col, periods=periods or 30)
            date_c = fr["date_col"]
            value_c = fr["value_col"]
            fc = fr["forecast"]
        if not date_c or not value_c:
            date_c, value_c = _detect_cols(df, date_c, value_c)
        # historical tail (last 60)
        hist = df.select([date_c, value_c]).drop_nulls().sort(date_c).tail(60)
        fig, ax = plt.subplots(figsize=(8, 4.5))
        try:
            # plot history
            try:
                x_hist = hist[date_c].to_list()
                y_hist = hist[value_c].to_numpy().astype(float).tolist()
            except Exception:
                x_hist = list(range(len(hist)))
                y_hist = hist[value_c].to_numpy().astype(float).tolist()
            ax.plot(x_hist, y_hist, label="history", marker="o", markersize=2, linewidth=1.5)
            # plot forecast as continuation
            if fc:
                # use integer x for forecast continuation
                start = len(x_hist)
                x_fc = list(range(start, start + len(fc)))
                # for date axis, keep using integer continuation for simplicity
                # but label as forecast
                ax.plot(x_fc, fc, label="forecast", linestyle="--", marker="x", markersize=3)
            ax.set_xlabel(date_c)
            ax.set_ylabel(value_c)
            ax.set_title(f"Forecast: {value_c} ({len(fc)} periods)")
            ax.legend()
            fig.tight_layout()
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=150)
            plt.close(fig)
            png = buf.getvalue()
            b64 = base64.b64encode(png).decode()
            out_dir = Path("artifacts") / "charts"
            out_dir.mkdir(parents=True, exist_ok=True)
            fname = f"{uuid.uuid4().hex[:10]}_forecast.png"
            out_path = out_dir / fname
            out_path.write_bytes(png)
            return {"artifact_path": str(out_path), "base64_png": b64, "diagnostics": {"date_col": date_c, "value_col": value_c, "periods": len(fc)}}
        except Exception:
            plt.close(fig)
            raise

    def evidence(
        self,
        dataset_path: str | Path,
        forecast_result: dict[str, Any],
        claim: str | None = None,
        source_id: str | None = None,
    ) -> dict[str, Any]:
        """Evidence (§27) — wrap forecast result as evidence record.

        Returns dict with Insight→Evidence→ToolCall trace fields.
        """
        fc = forecast_result.get("forecast", [])
        metrics = forecast_result.get("metrics", {})
        mae = metrics.get("mae")
        default_claim = f"Forecast {forecast_result.get('value_col')} for {len(fc)} periods, holdout MAE={mae:.3f}" if mae is not None else f"Forecast {len(fc)} periods"
        return {
            "id": f"ev-{uuid.uuid4().hex[:8]}",
            "claim": claim or default_claim,
            "source_type": "model",
            "source_id": source_id or f"forecast:{forecast_result.get('method','unknown')}",
            "result": {"forecast": fc[:5], "metrics": metrics, "diagnostics": forecast_result.get("diagnostics", {})},
            "confidence": 0.8 if mae is not None and mae < 10 else 0.6,
            "validation_status": "pending",
        }

    # CLI/SDK helpers
    def run_full(
        self,
        dataset_path: str | Path,
        date_col: str | None = None,
        value_col: str | None = None,
        periods: int = 30,
        method: str = "linear_trend",
        do_backtest: bool = True,
        do_viz: bool = True,
    ) -> dict[str, Any]:
        """Full pipeline: forecast→backtest→metrics→viz→evidence (§27 integration)."""
        fr = self.forecast(dataset_path, date_col, value_col, periods, method)
        bt = self.backtest(dataset_path, fr["date_col"], fr["value_col"], method) if do_backtest else None
        viz = self.forecast_viz(dataset_path, fr) if do_viz else None
        ev = self.evidence(dataset_path, fr)
        return {"forecast": fr, "backtest": bt, "metrics": fr.get("metrics"), "visualization": viz, "evidence": ev}


def register() -> TimeSeriesPlugin:
    return TimeSeriesPlugin()
