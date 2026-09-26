"""A failed tool call must not be cached (D-L3-04 fix (i)).

`_run_tool` stored `(None, False, error)` under the same key a success uses, so
one transient miss — a file not yet written, a mount that lagged — made that
dataset unreadable for the lifetime of the process: every later retry replayed
the first error instead of running the tool.

The last assertion is the other half of the fix: successes must still be cached.
Dropping the cache altogether would also make this test pass.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import dsa_tools
from dsa_agent.graph import _TOOL_CACHE, _run_tool, _tool_cache_key


def _profile(path: str):
    return _run_tool("profile_dataset", {"path": path})


def test_a_failed_tool_call_is_not_replayed_after_the_data_appears(tmp_path: Path) -> None:
    dsa_tools.bootstrap()
    ds = tmp_path / "ds.csv"
    key = _tool_cache_key("profile_dataset", {"path": str(ds)})
    _TOOL_CACHE.pop(key, None)

    async def _run() -> None:
        _, ok_first, err_first = await _profile(str(ds))
        assert ok_first is False, "the missing dataset should have failed"
        assert key not in _TOOL_CACHE, f"failure was cached: {err_first!r}"

        ds.write_text("v\n100\n200\n300\n", encoding="utf-8")
        out_second, ok_second, err_second = await _profile(str(ds))
        assert ok_second is True, f"the first failure is still being replayed: {err_second!r}"
        assert out_second is not None

        assert key in _TOOL_CACHE, "successes must still be cached"
        out_third, ok_third, _ = await _profile(str(ds))
        assert ok_third is True and out_third is out_second

    try:
        asyncio.run(_run())
    finally:
        _TOOL_CACHE.pop(key, None)
