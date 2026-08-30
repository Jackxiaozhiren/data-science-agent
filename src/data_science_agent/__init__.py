__version__ = "4.3.0"

# Importing this package makes the vendored dsa_* sub-packages importable as
# top-level names (they ship inside data_science_agent/_vendor). Must run before
# any dsa_* lazy import below / in the SDK.
from data_science_agent import _vendor  # noqa: F401
from data_science_agent.sdk import (
    Agent,
    Analysis,
    Artifact,
    Benchmark,
    BenchmarkResult,
    Dataset,
    Evidence,
    Insight,
    Report,
    Reproduction,
    ReproductionResult,
)

__all__ = [
    "Agent",
    "Analysis",
    "Artifact",
    "Benchmark",
    "BenchmarkResult",
    "Dataset",
    "Evidence",
    "Insight",
    "Report",
    "Reproduction",
    "ReproductionResult",
    "__version__",
]
