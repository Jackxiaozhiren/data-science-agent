"""Dataset layer: registry, validation, loader, profiler, hash, artefact paths.

The names below are resolved on first use (PEP 562) rather than imported eagerly. Eager re-exports meant that
importing *any* submodule ran this file first, and this file reached `dsa_datasets.loader` and `profiler` -- so
`from dsa_datasets.errors import ValidationError` in the API's upload route pulled polars into the process.
`dsa_api.services.dataset_service` defers its dataframe imports for exactly that reason ("so lightweight health
checks can start reliably on memory-constrained demo instances"), and deferring at the call site cannot help
while the package initialiser is eager. The public surface is unchanged; only when it costs is what moved.
"""

from __future__ import annotations

import importlib
from typing import Any

_EXPORTS: dict[str, str] = {
    "ColumnKind": "dsa_datasets.models",
    "ColumnProfile": "dsa_datasets.models",
    "DatasetError": "dsa_datasets.errors",
    "DatasetFormat": "dsa_datasets.models",
    "DatasetProfile": "dsa_datasets.models",
    "DatasetRecord": "dsa_datasets.models",
    "FileTooLargeError": "dsa_datasets.errors",
    "UnsupportedFormatError": "dsa_datasets.errors",
    "ValidationError": "dsa_datasets.errors",
    "build_profile": "dsa_datasets.profiler",
    "detect_format": "dsa_datasets.validate",
    "load_dataframe": "dsa_datasets.loader",
    "quick_profile_for_path": "dsa_datasets.profiler",
    "sha256_bytes": "dsa_datasets.hash_utils",
    "sha256_file": "dsa_datasets.hash_utils",
    "validate_file": "dsa_datasets.validate",
    "validate_filename": "dsa_datasets.validate",
    "validate_size": "dsa_datasets.validate",
}

__all__ = sorted(_EXPORTS)

__version__ = "0.1.0"


def __getattr__(name: str) -> Any:
    try:
        module_name = _EXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    value = getattr(importlib.import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_EXPORTS))
