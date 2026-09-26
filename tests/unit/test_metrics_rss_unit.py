"""`/metrics` must scale `ru_maxrss` by the platform's unit.

macOS reports `ru_maxrss` in bytes, Linux in kilobytes. The handler divided
by 1024 twice on both, so a Linux process under-reported RSS by 1024x, and an
`except Exception: pass` around the block kept any error in it invisible.
"""

from __future__ import annotations

import asyncio
import os
import resource

import pytest

from dsa_api.routers.health import metrics


_REAL = os.uname()


class _FakeUname:
    """ctypes also calls os.uname(), so every field has to stay real."""

    def __init__(self, sysname: str) -> None:
        self.sysname = sysname
        self.nodename = _REAL.nodename
        self.release = _REAL.release
        self.version = _REAL.version
        self.machine = _REAL.machine


@pytest.mark.parametrize(
    ("sysname", "divisor"),
    [("Darwin", 1024 * 1024), ("Linux", 1024)],
)
def test_rss_mb_uses_the_platform_unit(
    monkeypatch: pytest.MonkeyPatch, sysname: str, divisor: int
) -> None:
    monkeypatch.setattr(os, "uname", lambda: _FakeUname(sysname))

    before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    out = asyncio.run(metrics())
    after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    assert out["rss_mb"] is not None
    # ru_maxrss is a high-water mark, so the handler may read slightly more.
    assert (before / divisor) <= out["rss_mb"] <= (after / divisor) * 1.05
