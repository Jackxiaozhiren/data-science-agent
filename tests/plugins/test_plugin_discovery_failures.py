"""§94: a plugin whose manifest cannot be parsed currently vanishes without a trace.

`discover_plugins` scanned `manifest.yaml` and `plugin.yaml` and put `except Exception:
continue` around each, so a broken manifest produced an empty result the user read as
"no plugins installed". Its sibling `validate_plugin` already reports the same failure
as `manifest parse failed: <cause>` -- this file makes discovery use that existing
convention instead of inventing a second one, without changing what the default call
returns.
"""

from __future__ import annotations

from pathlib import Path

import pytest

VALID = """\
name: ok-plugin
version: 1.0.0
license: MIT
entrypoint:
  python: ok:run
permissions:
  - dataset.read
"""

BROKEN = """\
name: broken-plugin
version: 1.0.0
license: MIT
entrypoint:
  python: [this is not a mapping
permissions: []
"""


def _root(tmp_path: Path, *, with_broken: bool) -> Path:
    root = tmp_path / "registry" / ("with-broken" if with_broken else "clean")
    good = root / "ok"
    good.mkdir(parents=True)
    (good / "manifest.yaml").write_text(VALID, encoding="utf-8")
    if with_broken:
        bad = root / "bad"
        bad.mkdir()
        (bad / "manifest.yaml").write_text(BROKEN, encoding="utf-8")
    return root


def test_the_default_call_stays_lenient(tmp_path: Path) -> None:
    """Green-on-arrival pin: today a broken manifest is skipped, and callers rely on that.

    Recorded before adding strict mode so the change is additive. If this goes red,
    `dsa plugin list` behaviour changed and that is a contract decision, not a fix.
    """
    from dsa_plugins.registry import discover_plugins

    root = _root(tmp_path, with_broken=True)
    found = discover_plugins(root)
    assert [m.name for m in found] == ["ok-plugin"]


def test_strict_discovery_names_the_manifest_it_could_not_parse(tmp_path: Path) -> None:
    from dsa_plugins.registry import PluginDiscoveryError, discover_plugins

    root = _root(tmp_path, with_broken=True)
    with pytest.raises(PluginDiscoveryError) as caught:
        discover_plugins(root, strict=True)

    message = str(caught.value)
    assert "manifest.yaml" in message, message
    assert "bad" in message, message
    assert "ok-plugin" not in message, "the good manifest was reported as a failure"


def test_strict_discovery_stays_quiet_when_everything_parses(tmp_path: Path) -> None:
    from dsa_plugins.registry import discover_plugins

    root = _root(tmp_path, with_broken=False)
    found = discover_plugins(root, strict=True)
    assert [m.name for m in found] == ["ok-plugin"]


def test_strict_discovery_covers_the_second_scheme_too(tmp_path: Path) -> None:
    """`plugin.yaml` is scanned by its own loop with its own swallow; both must speak."""
    from dsa_plugins.registry import PluginDiscoveryError, discover_plugins

    root = tmp_path / "registry" / "plugin-yaml"
    bad = root / "bad"
    bad.mkdir(parents=True)
    (bad / "plugin.yaml").write_text(BROKEN, encoding="utf-8")

    with pytest.raises(PluginDiscoveryError, match="plugin.yaml"):
        discover_plugins(root, strict=True)


def test_the_failure_carries_the_underlying_cause(tmp_path: Path) -> None:
    """A wrapped reason is the difference between 'skipped' and 'skipped because'."""
    from dsa_plugins.registry import PluginDiscoveryError, discover_plugins

    root = _root(tmp_path, with_broken=True)
    with pytest.raises(PluginDiscoveryError) as caught:
        discover_plugins(root, strict=True)

    assert caught.value.__cause__ is not None, "the parse error was dropped on the way out"
