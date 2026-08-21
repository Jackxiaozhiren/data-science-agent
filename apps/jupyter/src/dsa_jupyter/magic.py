"""%dsa magic for Jupyter (W4 §28) — line and cell magic."""

from __future__ import annotations

import argparse
import asyncio
import shlex
import sys
import threading
from pathlib import Path
from typing import Any

try:
    from IPython.core.magic import Magics, line_cell_magic, magics_class  # type: ignore[import-not-found]
    from IPython.display import HTML, Markdown, display  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    Magics = object  # type: ignore[assignment]
    def magics_class(cls):  # type: ignore[no-redef]
        return cls
    def line_cell_magic(func):  # type: ignore[no-redef]
        return func
    HTML = Markdown = display = None  # type: ignore[assignment]

from dsa_jupyter.display import display_analysis
from dsa_jupyter.metadata import collect_notebook_metadata


def _run_sync(coro_factory):  # type: ignore[no-untyped-def]
    """Run coroutine factory in a way that works inside Jupyter's running loop (§29)."""
    # Try nest_asyncio first
    try:
        import nest_asyncio  # type: ignore[import-not-found]

        nest_asyncio.apply()
    except Exception:
        pass
    try:
        return asyncio.run(coro_factory())
    except RuntimeError as e:
        if "cannot be called from a running event loop" in str(e):
            # Run in a new thread's loop
            result: list[Any] = []
            exc: list[BaseException] = []

            def _thread():
                try:
                    result.append(asyncio.run(coro_factory()))
                except BaseException as ex:
                    exc.append(ex)

            t = threading.Thread(target=_thread, daemon=True)
            t.start()
            t.join(timeout=120)
            if exc:
                raise exc[0]
            if result:
                return result[0]
            raise RuntimeError("Thread did not return")
        raise


@magics_class
class DSAMagic(Magics):
    """%dsa magic — §28 MVP.

    Usage:
        %dsa --help
        %dsa profile sales.csv
        %dsa profile sales.csv --json
        %dsa analyze sales.csv --task "Analyze revenue" [--json]
        %%dsa analyze sales.csv
        Analyze revenue trend over time
    """

    def __init__(self, shell: Any) -> None:
        super().__init__(shell)

    @line_cell_magic
    def dsa(self, line: str, cell: str | None = None) -> Any:
        # cell magic: cell content is task if provided
        raw = line.strip()
        if cell is not None and cell.strip():
            # cell magic: treat cell as task if --task not in line
            if "--task" not in raw:
                # append task from cell
                task_from_cell = cell.strip().replace("\n", " ")[:500]
                raw = f"{raw} --task {shlex.quote(task_from_cell)}" if raw else f"--task {shlex.quote(task_from_cell)}"
            else:
                raw = f"{raw} {cell.strip()}"
        if not raw or raw in ("--help", "-h", "help"):
            return self._help()
        args = shlex.split(raw)
        # help
        if args and args[0] in ("--help", "-h", "help"):
            return self._help()
        cmd = args[0] if args else ""
        if cmd == "profile":
            return self._handle_profile(args[1:])
        if cmd == "analyze":
            return self._handle_analyze(args[1:])
        if cmd == "benchmark":
            return self._handle_benchmark(args[1:])
        if cmd == "doctor":
            return self._handle_doctor(args[1:])
        if cmd == "plugin":
            return self._handle_plugin(args[1:])
        # fallback: if no cmd, treat as analyze with task = raw
        # e.g. %dsa Analyze revenue in sales.csv
        return self._help(extra=f"Unknown command: {cmd}")

    def _help(self, extra: str | None = None) -> None:
        msg = """
`%dsa` — Data Science Agent Jupyter Magic (§28)

Commands:
  %dsa profile <dataset> [--json]               — Profile dataset (schema, rows, cols)
  %dsa analyze <dataset> --task "<question>" [--json]  — Run analysis (Agent)
  %dsa benchmark [--limit N] [--json]          — Run benchmark smoke
  %dsa doctor [--json]                         — Setup check
  %dsa plugin [--json]                         — List plugins

Cell magic:
  %%dsa analyze sales.csv
  Analyze revenue trend

Display:
  from data_science_agent import Agent
  agent = Agent()
  result = await agent.analyze("sales.csv", "Analyze revenue")
  result  # rich HTML (evidence + report + artifacts)

Reproducibility (§31): metadata dataset_hash/agent_version/sdk_version/prompt_version/tool_version/experiment_id is shown in header.
"""
        if extra:
            msg += f"\n{extra}\n"
        if display is not None and Markdown is not None:
            display(Markdown(msg))
        else:
            print(msg)
        return None

    def _handle_profile(self, args: list[str]) -> Any:
        parser = argparse.ArgumentParser(prog="%dsa profile", add_help=False)
        parser.add_argument("dataset", nargs="?", default=None)
        parser.add_argument("--json", action="store_true")
        try:
            ns, _ = parser.parse_known_args(args)
        except SystemExit:
            return None
        if not ns.dataset:
            if display is not None:
                display(HTML("<b style='color:red;'>Usage: %dsa profile &lt;dataset&gt; [--json]</b>"))
            else:
                print("Usage: %dsa profile <dataset> [--json]")
            return None
        from data_science_agent import Agent

        # progress
        if display is not None:
            display(HTML(f"<i>Profiling {ns.dataset} …</i>"))
        try:
            prof = Agent().profile(ns.dataset)
        except Exception as e:
            if display is not None:
                display(HTML(f"<b style='color:red;'>Profile failed: {e}</b>"))
            else:
                print(f"Profile failed: {e}")
            return None
        meta = collect_notebook_metadata(ns.dataset, None, None)
        if ns.json:
            if display is not None:
                display(HTML(f"<pre>{prof}</pre><small>{meta}</small>"))
            else:
                print(prof)
            return prof
        # rich display
        if display is not None:
            html = f"""
            <div style="border:1px solid #ddd; padding:10px; border-radius:6px;">
              <h4>📊 Profile: {ns.dataset}</h4>
              <b>Rows:</b> {prof.get('rows')} | <b>Columns:</b> {', '.join(map(str, prof.get('columns', [])[:10]))}<br/>
              <small>dataset_hash:{meta['dataset_hash']} sdk:{meta['sdk_version']}</small>
            </div>
            """
            display(HTML(html))
            # also show as table via polars if available
            try:
                import polars as pl  # type: ignore[import-not-found]

                from dsa_datasets.loader import load_dataframe
                from dsa_datasets.validate import detect_format

                p = Path(ns.dataset)
                df = load_dataframe(p, detect_format(p.name))
                display(df.head(5))
            except Exception:
                pass
        else:
            print(prof)
        return prof

    def _handle_analyze(self, args: list[str]) -> Any:
        parser = argparse.ArgumentParser(prog="%dsa analyze", add_help=False)
        parser.add_argument("dataset", nargs="?", default=None)
        parser.add_argument("--task", dest="task", default=None)
        parser.add_argument("--json", action="store_true")
        # allow --task with quote
        try:
            ns, _ = parser.parse_known_args(args)
        except SystemExit:
            return None
        if not ns.dataset or not ns.task:
            if display is not None:
                display(HTML("<b style='color:red;'>Usage: %dsa analyze &lt;dataset&gt; --task \"&lt;question&gt;\" [--json]</b>"))
            else:
                print('Usage: %dsa analyze <dataset> --task "<question>" [--json]')
            return None
        # Show progress (§29)
        if display is not None:
            display(HTML(f"<div style='background:#eef; padding:8px; border-radius:6px;'><b>🔬 Ask:</b> {ns.task}<br/><i>Running analysis on {ns.dataset} … (Planner→Scientist→Critic→Report)</i></div>"))
        else:
            print(f"Ask: {ns.task} | Running on {ns.dataset} …")
        from data_science_agent import Agent

        try:
            # Use _run_sync to handle Jupyter loop (§29 Show Progress)
            def _factory():
                return Agent().analyze(ns.dataset, ns.task)

            result = _run_sync(_factory)  # type: ignore[arg-type]
        except Exception as e:
            if display is not None:
                display(HTML(f"<b style='color:red;'>Analysis failed: {e}</b>"))
            else:
                print(f"Analysis failed: {e}")
            return None
        # Show result (§29-30)
        if ns.json:
            import json

            payload = {
                "run_id": result.run_id,
                "status": result.status,
                "evidence": len(result.evidence),
                "report": result.report_markdown[:800] if result.report_markdown else None,
                "meta": collect_notebook_metadata(ns.dataset, ns.task, result.run_id),
            }
            if display is not None:
                display(HTML(f"<pre>{json.dumps(payload, indent=2)}</pre>"))
            else:
                print(json.dumps(payload, indent=2))
            return result
        # rich display (§29-30)
        try:
            display_analysis(result, ns.dataset, ns.task)
        except Exception:
            # fallback
            print(f"status={result.status} evidence={len(result.evidence)}")
            if result.report_markdown:
                print(result.report_markdown[:2000])
        return result

    def _handle_benchmark(self, args: list[str]) -> Any:
        parser = argparse.ArgumentParser(prog="%dsa benchmark", add_help=False)
        parser.add_argument("--limit", type=int, default=1)
        parser.add_argument("--json", action="store_true")
        try:
            ns, _ = parser.parse_known_args(args)
        except SystemExit:
            return None
        if display is not None:
            display(HTML(f"<i>Running benchmark limit={ns.limit} …</i>"))
        from data_science_agent import Benchmark

        try:
            res = Benchmark().run(limit=ns.limit)
        except Exception as e:
            if display is not None:
                display(HTML(f"<b style='color:red;'>Benchmark failed: {e}</b>"))
            return None
        if ns.json:
            import json

            if display is not None:
                display(HTML(f"<pre>{json.dumps({'n_tasks': res.n_tasks, 'aggregate': res.aggregate}, indent=2)}</pre>"))
            return res
        if display is not None:
            display(HTML(f"<b>Benchmark:</b> {res.n_tasks} tasks, success={res.aggregate.get('task_success_rate')}"))
        else:
            print(f"Benchmark: {res.n_tasks} tasks")
        return res

    def _handle_doctor(self, args: list[str]) -> Any:
        import json as _json

        # Direct via dsa_evaluation.doctor
        try:
            from dsa_evaluation.doctor import run_doctor

            rep = run_doctor()
            if "--json" in args:
                if display is not None:
                    display(HTML(f"<pre>{_json.dumps(rep, indent=2)}</pre>"))
                return rep
            if display is not None:
                checks = "<br/>".join(f"{c['name']}: {c['status']}" for c in rep.get("checks", []))
                display(HTML(f"<b>dsa doctor ({rep.get('status')})</b><br/>{checks}"))
            else:
                print(rep)
            return rep
        except Exception as e:
            print(f"doctor failed: {e}")
            return None

    def _handle_plugin(self, args: list[str]) -> Any:
        if display is not None and Markdown is not None:
            from dsa_plugins.registry import list_plugins

            pls = list_plugins()
            md = "| Plugin | Version | Capabilities |\n|---|---|---|\n"
            for p in pls:
                md += f"| {p.name} | {p.version} | {', '.join(p.capabilities[:3])} |\n"
            display(Markdown(md))
            return pls
        else:
            from dsa_plugins.registry import list_plugins

            return list_plugins()


def load_ipython_extension(ipython: Any) -> None:
    """Called via `%load_ext dsa_jupyter` — registers magic + formatters (§28-30)."""
    # register magic
    try:
        ipython.register_magics(DSAMagic)
    except Exception:
        pass
    # register display formatter for Analysis
    try:
        from dsa_jupyter.display import register_formatter

        register_formatter(ipython)
    except Exception:
        pass
    # also make `from data_science_agent import Agent` display rich without explicit import of dsa_jupyter
    # by patching Analysis.__repr_html__ if not exists
    try:
        from data_science_agent.sdk import Analysis

        if not hasattr(Analysis, "_repr_html_"):

            def _repr_html_(self):  # type: ignore[no-untyped-def]
                from dsa_jupyter.display import format_analysis_html

                return format_analysis_html(self)

            Analysis._repr_html_ = _repr_html_  # type: ignore[attr-defined]
    except Exception:
        pass
