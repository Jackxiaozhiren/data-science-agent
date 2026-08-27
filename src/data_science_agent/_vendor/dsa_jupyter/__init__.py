"""dsa-jupyter — Jupyter integration for Data Science Agent (W4 §28-32)."""

from __future__ import annotations

__version__ = "0.1.0"

try:
    from dsa_jupyter.display import display_analysis, format_analysis_html
    from dsa_jupyter.magic import DSAMagic, load_ipython_extension
    from dsa_jupyter.metadata import collect_notebook_metadata

    __all__ = [
        "DSAMagic",
        "display_analysis",
        "format_analysis_html",
        "collect_notebook_metadata",
        "load_ipython_extension",
    ]
except Exception:  # pragma: no cover
    __all__ = []
