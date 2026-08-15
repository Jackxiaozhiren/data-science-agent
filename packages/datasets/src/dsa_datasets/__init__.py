"""Dataset layer: registry, validation, loader, profiler, hash."""

from dsa_datasets.errors import (
    DatasetError,
    FileTooLargeError,
    UnsupportedFormatError,
    ValidationError,
)
from dsa_datasets.hash_utils import sha256_bytes, sha256_file
from dsa_datasets.loader import load_dataframe
from dsa_datasets.models import (
    ColumnKind,
    ColumnProfile,
    DatasetFormat,
    DatasetProfile,
    DatasetRecord,
)
from dsa_datasets.profiler import build_profile, quick_profile_for_path
from dsa_datasets.validate import detect_format, validate_file, validate_filename, validate_size

__all__ = [
    "ColumnKind",
    "ColumnProfile",
    "DatasetError",
    "DatasetFormat",
    "DatasetProfile",
    "DatasetRecord",
    "FileTooLargeError",
    "UnsupportedFormatError",
    "ValidationError",
    "build_profile",
    "detect_format",
    "load_dataframe",
    "quick_profile_for_path",
    "sha256_bytes",
    "sha256_file",
    "validate_file",
    "validate_filename",
    "validate_size",
]

__version__ = "0.1.0"
