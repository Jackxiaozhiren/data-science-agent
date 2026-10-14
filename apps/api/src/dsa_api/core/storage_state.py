"""Which kind of storage this process writes to, stated without saying where it is.

The fact exists already and is honest about itself -- `is_ephemeral_database()` is what makes the server log
"use a persistent volume or managed DB for anything beyond demos" -- but it only ever reaches the log. A
visitor to the hosted demo cannot see it, so a run that disappears after an idle spin-down reads as an
application that loses data by design rather than as a property of a free instance whose container is
recreated. That distinction is the difference between a limitation and a defect, and the reviewer has no way
to make it from the outside.

Two deliberate omissions. Absolute paths are not published: `/version` is unauthenticated, and a private
deployment's layout is not information a caller needs in exchange for a warning the caller does. And
``durable`` means exactly what the name says and nothing more -- no configured root sits on a path the
platform documents as throwaway. It is not a guarantee about the volume behind a mount, which is a thing the
operator configures and this process cannot observe.

No path is re-derived here. Each root comes from the same accessor the writer uses, so the disclosure cannot
drift from the behaviour it describes.
"""

from __future__ import annotations

from typing import Any

from dsa_api.core.config import settings

#: Path prefixes that name storage the platform is allowed to throw away. `/private/...` is not a second
#: opinion about `/tmp`: on macOS `/tmp` and `/var/folders` are symlinks into `/private/...`, so a path
#: resolved through `Path.resolve()` arrives in the second spelling and a single-spelling check reports
#: throwaway storage as durable.
EPHEMERAL_PREFIXES = (
    "/tmp/",  # noqa: S108 - this is a name being matched, not a directory being written to
    "/private/tmp/",
    "/var/folders/",
    "/private/var/folders/",
)

#: Not a path at all: a database that never touches a disk.
EPHEMERAL_MARKERS = (":memory:",)


def is_ephemeral_path(value: str) -> bool:
    """True when ``value`` names storage that does not survive a restart, a redeploy, or a spin-down."""
    low = value.lower()
    return any(marker in low for marker in EPHEMERAL_MARKERS) or any(
        prefix in low for prefix in EPHEMERAL_PREFIXES
    )


def storage_report() -> dict[str, Any]:
    """The disclosure `/version` publishes: which roots are throwaway, and therefore whether state persists.

    Imported inside rather than at module scope because the dataset and artifact accessors live in layers
    this module is allowed to describe but not to pull into its import graph.
    """
    from dsa_api.services.dataset_service import storage_dir
    from dsa_datasets.artifact_paths import artifact_root

    roots = {
        "database": settings.database_url,
        "datasets": str(storage_dir()),
        "artifacts": str(artifact_root()),
    }
    ephemeral = sorted(name for name, value in roots.items() if is_ephemeral_path(value))
    return {"durable": not ephemeral, "ephemeral_roots": ephemeral}
