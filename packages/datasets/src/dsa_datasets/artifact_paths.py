"""One rule for where run artefacts land (§122, D-L4-07).

Six writers used to derive that rule from their own installed location, with
`Path(__file__).resolve().parents[4] / "artifacts"`. The expression is layout-sensitive, and this
project ships four layouts, so one function returned four different directories: the repo root for
the agent module, `<root>/packages/artifacts` for the tool modules (one level deeper),
`<root>/src/artifacts` for the vendored tools, and the interpreter's own `site-packages` tree for an
installed wheel. The two readers -- `dsa_mcp.resources` and the time-series plugin -- resolved the
same logical directory against the working directory instead, so a run started anywhere but the repo
root wrote a report the MCP server could not find.

The rule now: `$DSA_ARTIFACT_ROOT` if it is set, otherwise `<cwd>/artifacts`. The process decides,
not the module. Every caller passes one path component per argument, and a component that is not a
single safe segment is refused here rather than concatenated into a write path -- `run_id` arrives
from tool input, and it used to be interpolated raw (§122's D-L4-09).

This lives in the datasets layer because that is the only shipped package all eight call sites
already load: measured, `import dsa_tools` costs 2791 ms and drags matplotlib and sklearn in behind
its registry, so importing the rule from there would have made `import dsa_agent.report` (294 ms
before) and `import dsa_mcp.server` (420 ms) pay for plotting libraries they do not use.
`dsa_datasets` is already resident on the agent and tool paths, and the MCP reader imports it inside
the one function that needs it for the same reason.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

ENV_ROOT = "DSA_ARTIFACT_ROOT"

# One path component: no separators, no traversal, must not start with a dot (so ".." and hidden
# escape shapes are both refused), bounded so an absurdly long tool argument cannot name a path.
_SEGMENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


def _checked(part: str) -> str:
    if not _SEGMENT.fullmatch(part):
        raise ValueError(
            f"unsafe artefact path component {part!r}: expected one path segment of "
            "[A-Za-z0-9._-], no separators and no '..'"
        )
    return part


def is_safe_segment(value: str) -> bool:
    """Whether `value` may name one artefact directory, without raising.

    Tool boundaries ask first and raise their own error type, so that refusing a caller's argument
    stays one `if` rather than a try/except -- the debt ratchet counts handlers, and a policy check
    is not debt (`AUDIT_LEDGER.md` §122).
    """
    return _SEGMENT.fullmatch(value) is not None


def artifact_root(*parts: str) -> Path:
    """Return the artefact directory, with each argument as one validated sub-component."""
    override = os.getenv(ENV_ROOT, "").strip()
    base = Path(override).expanduser() if override else Path.cwd() / "artifacts"
    if not base.is_absolute():
        base = Path.cwd() / base
    return base.joinpath(*(_checked(part) for part in parts))
