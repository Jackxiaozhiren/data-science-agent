"""Lane A (R-09 + R-02): the build a page names and the reasoning that produced a run must be the real ones.

Two premises measured before this file was written, both re-checkable:

``apps/api/src/dsa_api/core/config.py`` declared ``version: str = "1.8.0"`` while ``pyproject.toml``
declared the ``4.5.0`` line, and the live demo answered ``{"version":"1.8.0"}`` on ``/version``. So a
reviewer reading a release note could not prove the demo they were handed was that release (R-09).

No ``/health``-family route reported ``DSA_LLM_MODE`` at all, while ``render.yaml`` pins the demo to
``heuristic``, so a visitor could not see that no model planned anything (R-02).

The invariant both requirements share is *one owner per reported fact*: the version comes from the
installed distribution's metadata, the mode comes from the same resolution the provider performs, and a
surface that displays either reads the API rather than the environment. A second copy of the version is
how a stale constant survives a bump; a mode computed in a component is how the UI ends up claiming more
than the runtime did.

Checked as pure functions over captured payloads and sources rather than by asserting single values, so
the falsification half is real: each planted defect below must be reported by the same function that
passes on the shipped one.
"""

from __future__ import annotations

import ast
import asyncio
import re
import tomllib
from importlib.metadata import PackageNotFoundError
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WEB_APP = ROOT / "apps/web/app"

#: The keys ``/version`` must publish for the reasoning mode. ``stub`` is the boolean the UI branches on;
#: ``error`` carries why a configured real provider cannot actually run.
MODE_KEYS = ("mode", "stub", "provider", "model", "error")

#: The one module that fetches build provenance, and the surfaces that must render its values.
PROVENANCE_SOURCE = "lib/buildProvenance.ts"
PROVENANCE_CONSUMERS = (
    "app/components/layout/ProvenanceStatus.tsx",
    "app/components/analysis/ReasoningModeBadge.tsx",
)
RUN_INSPECTOR = "app/analysis/[runId]/RunInspector.tsx"

VERSION_OWNER = "apps/api/src/dsa_api/core/config.py"
API_SURFACES = (ROOT / "apps/api/src/dsa_api/routers", ROOT / "apps/api/src/dsa_api/core")

VERSION_LIKE = re.compile(r"^\d+\.\d+\.\d+$")


def _distribution_name() -> str:
    """The distribution the running build belongs to -- read, never typed into this file."""
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["name"]


def _installed_version() -> str:
    from importlib.metadata import version

    return version(_distribution_name())


def _version_payload() -> dict:
    """The ``/version`` body, from the handler itself.

    Called directly instead of through ``TestClient``: the app's lifespan runs ``init_db()``, which
    would create SQLite inside the working tree (the same reason ``test_health_contract_doc.py``
    refuses to issue requests). ``version()`` takes no dependency and touches no database.
    """
    from dsa_api.routers.health import version as version_route

    return asyncio.run(version_route())


def _provider_resolution() -> dict:
    """What the provider resolves right now -- the reference the reported mode must equal."""
    from dsa_llm.providers import EnvLLMProvider

    provider = EnvLLMProvider()
    return {
        "mode": provider.mode,
        "stub": provider.active_provider == "stub",
        "provider": provider.active_provider,
        "model": provider.active_model,
    }


def provenance_issues(
    payload: dict, *, expected_version: str, expected_mode: dict, runnable: bool = True
) -> list[str]:
    """Every way a ``/version`` body disagrees with the build and provider it is supposed to describe."""
    issues: list[str] = []

    reported = payload.get("version")
    if reported is None:
        issues.append("/version: no `version` key -- the footer has nothing truthful to render")
    elif reported != expected_version:
        issues.append(
            f"/version: reports {reported!r} but the installed {_distribution_name()} "
            f"distribution is {expected_version!r}"
        )

    mode = payload.get("reasoning_mode")
    if mode is None:
        issues.append(
            "/version: no `reasoning_mode` key -- no surface can label what did the thinking"
        )
        return issues
    absent = [key for key in MODE_KEYS if key not in mode]
    if absent:
        issues.append(f"/version: reasoning_mode is missing {sorted(absent)}")
    for key in ("mode", "stub", "provider", "model"):
        if key in mode and mode[key] != expected_mode.get(key):
            issues.append(
                f"/version: reasoning_mode.{key} reports {mode[key]!r} while the provider "
                f"resolves {expected_mode.get(key)!r}"
            )
    if not runnable and mode.get("stub") is False and mode.get("error") is None:
        issues.append(
            "/version: a real-mode provider that cannot be constructed is reported with no `error` "
            "-- the UI would claim a model runs when every call would raise"
        )
    return issues


def env_rereads(source: str) -> list[str]:
    """Sites inside the API that read ``DSA_LLM_MODE`` themselves instead of asking the provider."""
    hits: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        if not (isinstance(node.func, ast.Attribute) and node.func.attr == "getenv"):
            continue
        first = node.args[0] if node.args else None
        if isinstance(first, ast.Constant) and first.value == "DSA_LLM_MODE":
            hits.append(f"line {node.lineno}")
    return hits


def rendered_provenance_issues(source: str, consumers: dict[str, str]) -> list[str]:
    """Whether each provenance surface reads the API's value through its one owner.

    Three shapes are failures: a surface that renders provenance without importing the owner (so it
    must be typing it), an owner that does not ask ``/version`` (so the number it publishes is a
    guess), and any file carrying a version-shaped literal (the UI inventing a figure the backend
    never produced -- the defect class commit ``32ee4b2`` is named for).
    """
    issues: list[str] = []
    if 'apiUrl("/version")' not in source:
        issues.append(
            f"{PROVENANCE_SOURCE}: does not fetch /version, so the provenance it exports is typed"
        )
    for relative, text in consumers.items():
        if "@/lib/buildProvenance" not in text:
            issues.append(f"{relative}: renders provenance without importing {PROVENANCE_SOURCE}")
        if 'apiUrl("/version")' in text:
            issues.append(
                f"{relative}: fetches /version itself, so the owner is no longer one module"
            )
    for relative, text in [(PROVENANCE_SOURCE, source), *consumers.items()]:
        for literal in re.findall(r'"([^"\n]{1,40})"', text):
            if VERSION_LIKE.match(literal):
                issues.append(f"{relative}: renders a version-shaped literal {literal!r}")
    return issues


def _read(relative: str) -> str:
    path = ROOT / relative
    assert path.is_file(), f"{relative} is missing -- this check would pass on nothing"
    return path.read_text(encoding="utf-8")


@pytest.fixture
def stub_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DSA_LLM_MODE", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def test_the_api_reports_the_installed_distribution_version(stub_env: None) -> None:
    """R-09 Accept: ``/version`` equals the installed distribution's own version."""
    payload = _version_payload()
    assert payload["version"] == _installed_version(), payload
    assert payload["version"] != "1.8.0", "the stale hardcoded constant is still being served"


def test_the_installed_metadata_and_the_manifest_agree(declared_version: str) -> None:
    """Close the pair the SDK contract test already pins, so ``/version`` cannot be self-consistent and wrong.

    ``/version`` reads installed metadata, and installed metadata is what a running process really is, so
    comparing the two alone would certify only transcription: a stale editable install would report its
    own outdated number and pass. The manifest is the other witness, and ``tests/sdk/test_sdk_contract.py``
    already holds ``declared_version`` as the one owner of that claim -- this reuses it rather than
    restating the rule.
    """
    assert _installed_version() == declared_version, (
        f"the installed {_distribution_name()} distribution reports {_installed_version()!r} while "
        f"pyproject.toml declares {declared_version!r}; re-sync the environment before trusting "
        "any version the API publishes"
    )
    assert _version_payload()["version"] == declared_version


def test_the_version_is_derived_and_an_absent_distribution_says_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R-09 Guard: no literal in the owner module, and the fallback is reachable.

    The fallback is exercised by making metadata refuse the distribution, not by reading a default: a
    branch no test can enter is a second stale constant waiting to become true.
    """
    literals = {
        node.value
        for node in ast.walk(ast.parse(_read(VERSION_OWNER)))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    hard = {value for value in literals if VERSION_LIKE.match(value)}
    assert not hard, f"{VERSION_OWNER} still hardcodes {sorted(hard)}"

    from dsa_api.core import config

    def _missing(_name: str) -> str:
        raise PackageNotFoundError(_name)

    monkeypatch.setattr(config, "_distribution_version", _missing, raising=False)
    assert config.runtime_version() == "unknown"

    monkeypatch.setattr(
        config, "_distribution_version", lambda name: f"{name}==9.9.9", raising=False
    )
    assert config.runtime_version() == f"{_distribution_name()}==9.9.9", (
        "runtime_version() is not returning what the distribution reports"
    )


def test_stub_configuration_is_reported_as_the_provider_resolves_it(stub_env: None) -> None:
    """R-02 Guard, direction one: heuristic/stub deployments are labelled as they really are."""
    payload = _version_payload()
    assert (
        provenance_issues(
            payload, expected_version=_installed_version(), expected_mode=_provider_resolution()
        )
        == []
    )
    assert payload["reasoning_mode"]["stub"] is True
    assert payload["reasoning_mode"]["model"] is None, (
        "a stub deployment published a model name; no model runs here"
    )


def test_real_configuration_is_reported_as_the_provider_resolves_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R-02 Guard, direction two: the same payload flips when the mode flips."""
    monkeypatch.setenv("DSA_LLM_MODE", "real")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-a-real-credential")
    payload = _version_payload()
    assert (
        provenance_issues(
            payload, expected_version=_installed_version(), expected_mode=_provider_resolution()
        )
        == []
    )
    assert payload["reasoning_mode"]["stub"] is False
    assert payload["reasoning_mode"]["provider"] == "openai", payload["reasoning_mode"]


def test_real_mode_without_a_credential_is_not_reported_as_a_working_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Product principle 2: the payload must not describe a runtime that raises on the first call.

    ``EnvLLMProvider`` cannot be constructed in this configuration -- that refusal is the fact being
    reported -- so the reference is the published vocabulary instead of a provider instance.
    """
    monkeypatch.setenv("DSA_LLM_MODE", "real")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    payload = _version_payload()
    mode = payload["reasoning_mode"]
    assert mode["stub"] is False, "a real-mode configuration is not a stub, even when misconfigured"
    assert mode["provider"] == "unconfigured", mode
    assert mode["model"] is None, mode
    assert mode["error"], mode
    assert (
        provenance_issues(
            payload, expected_version=_installed_version(), expected_mode=mode, runnable=False
        )
        == []
    )

    silent_failure = dict(payload, reasoning_mode={**mode, "error": None})
    assert any(
        "cannot be constructed" in i
        for i in provenance_issues(
            silent_failure,
            expected_version=_installed_version(),
            expected_mode=mode,
            runnable=False,
        )
    ), silent_failure


def test_the_provenance_checks_fire_on_the_defects_they_exist_to_catch(stub_env: None) -> None:
    """Falsification: every planted regression is reported by the function that passes today."""
    shipped = _version_payload()
    expected = _installed_version()
    mode = _provider_resolution()
    assert provenance_issues(shipped, expected_version=expected, expected_mode=mode) == []

    stale = dict(shipped, version="1.8.0")
    assert any(
        "1.8.0" in i
        for i in provenance_issues(stale, expected_version=expected, expected_mode=mode)
    ), stale

    no_version = {k: v for k, v in shipped.items() if k != "version"}
    assert any(
        "no `version` key" in i
        for i in provenance_issues(no_version, expected_version=expected, expected_mode=mode)
    ), no_version

    no_mode = {k: v for k, v in shipped.items() if k != "reasoning_mode"}
    assert any(
        "no `reasoning_mode` key" in i
        for i in provenance_issues(no_mode, expected_version=expected, expected_mode=mode)
    ), no_mode

    flipped = dict(shipped, reasoning_mode=dict(shipped["reasoning_mode"], stub=False))
    assert any(
        "reasoning_mode.stub" in i
        for i in provenance_issues(flipped, expected_version=expected, expected_mode=mode)
    ), flipped

    partial = dict(shipped, reasoning_mode={"mode": mode["mode"], "stub": True})
    assert any(
        "is missing" in i
        for i in provenance_issues(partial, expected_version=expected, expected_mode=mode)
    ), partial

    unrunnable = dict(
        shipped,
        reasoning_mode={
            **shipped["reasoning_mode"],
            "stub": False,
            "provider": "openai",
            "model": "m",
            "error": None,
        },
    )
    assert any(
        "cannot be constructed" in i
        for i in provenance_issues(
            unrunnable,
            expected_version=expected,
            expected_mode={"mode": "real", "stub": False, "provider": "openai", "model": "m"},
            runnable=False,
        )
    ), unrunnable


def test_no_api_surface_re_reads_the_mode_environment() -> None:
    """R-02 Spec 1: routers ask the owner function; a second ``os.getenv`` is a second owner."""
    scanned = 0
    for directory in API_SURFACES:
        for path in sorted(directory.rglob("*.py")):
            scanned += 1
            found = env_rereads(path.read_text(encoding="utf-8"))
            assert found == [], f"{path.relative_to(ROOT)} reads DSA_LLM_MODE itself at {found}"
    assert scanned >= 6, f"only {scanned} API modules scanned -- the walk broke, not a clean pass"


def test_the_reread_probe_fires_on_a_router_that_inlines_the_env_lookup() -> None:
    """And reports nothing on an unrelated env read, so the guard is not a match-anything scan."""
    planted = "import os\n\n\nasync def health():\n    return {'mode': os.getenv('DSA_LLM_MODE', 'stub')}\n"
    assert env_rereads(planted) == ["line 5"], env_rereads(planted)
    assert env_rereads("import os\nasync def h():\n    return os.getenv('DSA_AUTH_TOKEN')\n") == []


def _provenance_sources() -> tuple[str, dict[str, str]]:
    return (
        _read(f"apps/web/{PROVENANCE_SOURCE}"),
        {relative: _read(f"apps/web/{relative}") for relative in PROVENANCE_CONSUMERS},
    )


def test_provenance_surfaces_render_the_api_value_through_one_owner() -> None:
    """R-02/R-09 Guard: the label exists because the API said so, not because a component typed it."""
    source, consumers = _provenance_sources()
    assert rendered_provenance_issues(source, consumers) == []


def _planted(text: str, before: str) -> str:
    """Mutate a source and prove the mutation landed -- a plant that changes nothing tests nothing."""
    assert text != before, (
        "the planted copy is byte-identical to the shipped one; the anchor missed"
    )
    return text


def test_the_rendering_probe_fires_on_each_shape_it_would_miss() -> None:
    """Falsification: a detached consumer, a second fetcher, a silent owner, and a typed version."""
    source, consumers = _provenance_sources()
    first = PROVENANCE_CONSUMERS[0]

    detached = dict(
        consumers,
        **{
            first: _planted(
                consumers[first].replace("@/lib/buildProvenance", "@/lib/api"), consumers[first]
            )
        },
    )
    assert any("without importing" in i for i in rendered_provenance_issues(source, detached)), (
        detached
    )

    second_owner = dict(
        consumers,
        **{
            first: _planted(
                f'{consumers[first]}\nconst PULSE = apiUrl("/version");\n', consumers[first]
            )
        },
    )
    assert any(
        "fetches /version itself" in i for i in rendered_provenance_issues(source, second_owner)
    )

    silent = _planted(source.replace('apiUrl("/version")', 'apiUrl("/health")'), source)
    assert any(
        "does not fetch /version" in i for i in rendered_provenance_issues(silent, consumers)
    )

    typed = dict(
        consumers,
        **{first: _planted(f'{consumers[first]}\nconst STAMP = "9.9.9";\n', consumers[first])},
    )
    assert any("version-shaped literal" in i for i in rendered_provenance_issues(source, typed)), (
        typed
    )


def test_the_run_report_page_mounts_the_mode_label() -> None:
    """R-02 Spec 2 and 3: the badge sits by the status, and the exclusion is in body text."""
    inspector = _read(f"apps/web/{RUN_INSPECTOR}")
    for name in ("ReasoningModeBadge", "ReasoningModeNotice"):
        assert name in inspector, f"the run report page no longer mounts {name}"


def test_the_header_keeps_the_mode_beside_the_api_indicator() -> None:
    """R-02 Spec 2, first of two places: persistent, next to the existing API dot."""
    header = _read("apps/web/app/components/layout/SiteHeader.tsx")
    assert "ProvenanceStatus" in header, (
        "the persistent status area no longer carries the reasoning mode"
    )
