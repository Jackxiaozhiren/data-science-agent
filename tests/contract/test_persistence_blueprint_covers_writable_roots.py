"""Stage-1 persistence: every root the process can write to must sit on the declared disk.

Measured while preparing this, not inherited from the document it fixes. `docs/production-hardening.md`
Stage 1 listed two settings -- `DSA_DATABASE_URL` and `DSA_DATASET_DIR` -- while charts are written by
`dsa_datasets.artifact_paths.artifact_root()`, which reads `DSA_ARTIFACT_ROOT` and otherwise falls back to
`<cwd>/artifacts`. In the API image (`WORKDIR /app`) that fallback is `/app/artifacts`, outside any mount,
so an operator who copied the documented block got a demo that kept its metadata and its datasets and lost
every chart PNG on the next deploy. Worse, nothing said so: the startup warning behind the Render log line
comes from `is_ephemeral_database()`, which inspects the database URL only.

The live blueprint is checked from the other side too. It is `plan: free` with a `/tmp` database, and
`docs/hosted-demo.md` says the storage is ephemeral; if either drifts -- a `/var/data` URL without a disk,
or prose claiming durability the service does not have -- this file fails rather than letting the claim and
the configuration disagree.

Assertions are functions over parsed documents so the planted-defect half is real: each mutation below has
to be reported by the same checker that passes on the shipped files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml  # declared by dsa-plugins (packages/plugins/pyproject.toml), a workspace member in both dev and the image

ROOT = Path(__file__).resolve().parents[2]
LIVE = ROOT / "render.yaml"
EXAMPLE = ROOT / "deploy" / "render-persistent.example.yaml"
HOSTED_DOC = ROOT / "docs" / "hosted-demo.md"

#: Environment variables that name a directory or file the running process writes.
WRITABLE_ENV = ("DSA_DATABASE_URL", "DSA_DATASET_DIR", "DSA_ARTIFACT_ROOT")

#: Fields that must agree between the live blueprint and the paid example, because the operator's action
#: is "copy the plan/disk/persistence keys into the existing service" -- anything else that differs would
#: silently change the deployment rather than only its durability.
SHARED_SERVICE_FIELDS = (
    "runtime",
    "region",
    "branch",
    "dockerfilePath",
    "dockerContext",
    "healthCheckPath",
)


def _load(path: Path) -> dict[str, Any]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(document, dict) and "services" in document, f"{path} has no services list"
    return document


def _service(document: dict[str, Any]) -> dict[str, Any]:
    services = [s for s in document["services"] if s.get("name") == "data-science-agent-api"]
    assert len(services) == 1, f"expected exactly one API service, found {len(services)}"
    return services[0]


def _env(service: dict[str, Any]) -> dict[str, str]:
    return {str(item["key"]): str(item["value"]) for item in service.get("envVars") or []}


def _sqlite_file(url: str) -> str:
    """The path half of a SQLAlchemy sqlite URL: `sqlite+aiosqlite:////var/data/dsa.db` -> `/var/data/dsa.db`."""
    _, _, tail = url.partition(":///")
    return tail


def writable_roots(env: dict[str, str]) -> dict[str, str]:
    roots: dict[str, str] = {}
    if "DSA_DATABASE_URL" in env:
        roots["DSA_DATABASE_URL"] = _sqlite_file(env["DSA_DATABASE_URL"])
    for key in ("DSA_DATASET_DIR", "DSA_ARTIFACT_ROOT"):
        if key in env:
            roots[key] = env[key]
    return roots


def persistence_issues(service: dict[str, Any]) -> list[str]:
    """Every way a paid Stage-1 blueprint declares a disk but does not actually persist all of its state."""
    issues: list[str] = []
    env = _env(service)
    disk = service.get("disk")

    if not disk:
        return ["no `disk:` block -- nothing here is a durable configuration"]

    mount = str(disk.get("mountPath") or "")
    if not mount.startswith("/"):
        issues.append(f"disk.mountPath {mount!r} is not an absolute path")
    if not str(disk.get("name") or "").strip():
        issues.append("disk.name is empty")
    if not (disk.get("sizeGB") or 0):
        issues.append("disk.sizeGB is missing or zero")

    if str(service.get("plan") or "") == "free":
        issues.append("plan is `free`, and Render attaches disks to paid web services only")

    missing = [key for key in WRITABLE_ENV if key not in env]
    if missing:
        issues.append(
            f"writable roots not configured at all: {missing} (unset paths fall back to the image)"
        )

    for key, path in writable_roots(env).items():
        if not path.startswith(f"{mount.rstrip('/')}/"):
            issues.append(f"{key} writes to {path!r}, outside the {mount!r} mount")

    from dsa_api.core.database import is_ephemeral_database

    url = env.get("DSA_DATABASE_URL", "")
    if url and is_ephemeral_database(url):
        issues.append(
            f"DSA_DATABASE_URL {url!r} is still reported ephemeral by the app's own predicate"
        )

    return issues


def live_configuration_issues(service: dict[str, Any], doc_text: str) -> list[str]:
    """The live blueprint and its documentation must describe the same storage as the code sees it."""
    issues: list[str] = []
    env = _env(service)
    url = env.get("DSA_DATABASE_URL", "")
    has_disk = bool(service.get("disk"))

    from dsa_api.core.database import is_ephemeral_database

    ephemeral = is_ephemeral_database(url)
    if ephemeral == has_disk:
        issues.append(
            f"plan says {'disk attached' if has_disk else 'no disk'} while the app calls the URL "
            f"{'ephemeral' if ephemeral else 'durable'}: {url!r}"
        )
    claims_durable = "durable object storage" not in doc_text and "is now persistent" in doc_text
    if claims_durable and not has_disk:
        issues.append("docs/hosted-demo.md claims persistence the blueprint does not configure")
    if ephemeral and "ephemeral" not in doc_text:
        issues.append("the live database is ephemeral but docs/hosted-demo.md no longer says so")
    return issues


def example_drift_issues(example: dict[str, Any], live: dict[str, Any]) -> list[str]:
    """What the operator would break by copying the example into the live service."""
    issues: list[str] = []
    ex_svc, live_svc = _service(example), _service(live)
    ex_env, live_env = _env(ex_svc), _env(live_svc)

    for field in SHARED_SERVICE_FIELDS:
        if ex_svc.get(field) != live_svc.get(field):
            issues.append(f"{field}: example {ex_svc.get(field)!r} != live {live_svc.get(field)!r}")

    dropped = sorted(set(live_env) - set(ex_env))
    if dropped:
        issues.append(f"the example drops live env keys: {dropped}")
    return issues


# ---------------------------------------------------------------- live blueprint (free + ephemeral)


def test_the_live_blueprint_is_free_ephemeral_and_honestly_documented():
    service = _service(_load(LIVE))
    assert service.get("plan") == "free", (
        "the live demo was moved to a paid plan; re-read this file's intent"
    )
    assert not service.get("disk"), (
        "a disk appeared on the live blueprint -- update docs and this test together"
    )
    assert _env(service)["DSA_DATABASE_URL"].startswith("sqlite+aiosqlite:////tmp/"), (
        "live DB URL moved off /tmp"
    )
    assert live_configuration_issues(service, HOSTED_DOC.read_text(encoding="utf-8")) == []


# ---------------------------------------------------------------- paid example (Stage 1)


def test_the_paid_example_puts_every_writable_root_on_the_disk():
    example = _load(EXAMPLE)
    assert persistence_issues(_service(example)) == []


def test_the_paid_example_does_not_change_anything_except_durability():
    assert example_drift_issues(_load(EXAMPLE), _load(LIVE)) == []


def test_the_documented_stage_one_block_matches_the_example():
    """The page an operator actually reads must list the same three roots the file declares."""
    text = (ROOT / "docs" / "production-hardening.md").read_text(encoding="utf-8")
    env = _env(_service(_load(EXAMPLE)))
    for key in WRITABLE_ENV:
        assert f"{key}=" in text, (
            f"docs/production-hardening.md never sets {key} in its Stage-1 block"
        )
        assert env[key] in text, (
            f"{key}'s value in the example ({env[key]!r}) is not the one the page shows"
        )


# ---------------------------------------------------------------- the checker can fail


@pytest.mark.parametrize(
    "mutate,expected_fragment",
    [
        (
            lambda s: s["envVars"].append({"key": "DSA_ARTIFACT_ROOT", "value": "/app/artifacts"}),
            "outside",
        ),
        (lambda s: s.__setitem__("plan", "free"), "paid web services"),
        (
            lambda s: s.__setitem__("disk", {"name": "d", "mountPath": "/var/data", "sizeGB": 0}),
            "sizeGB",
        ),
        (lambda s: s.__setitem__("disk", None), "no `disk:` block"),
    ],
)
def test_each_persistence_defect_is_reported(mutate: Any, expected_fragment: str) -> None:
    """Negative control: the shipped example passes, and each planted variant is caught by name.

    The artifact-root case is the one that was actually wrong in the documentation: the mutation moves
    `DSA_ARTIFACT_ROOT` to the image-local default, which is exactly what an unset variable produces.
    """
    service = _service(_load(EXAMPLE))
    assert persistence_issues(service) == [], (
        "the shipped example must pass before any mutation is meaningful"
    )

    import copy

    mutated = copy.deepcopy(service)
    mutate(mutated)
    issues = persistence_issues(mutated)
    assert issues, f"the planted defect went unreported: {expected_fragment}"
    assert any(expected_fragment in issue for issue in issues), issues


def test_the_live_side_checker_reports_disk_and_url_mismatches() -> None:
    """Both shipped documents are self-consistent today; each one-sided drift must be named.

    The property is agreement, not a fixed answer: a disk with a `/tmp` URL and a `/var/data` URL with no
    disk are the two ways the blueprint can lie, and dropping the word "ephemeral" from the hosted-demo page
    while the live URL still points at `/tmp` is the documentation half of the same lie.
    """
    import copy

    doc = HOSTED_DOC.read_text(encoding="utf-8")
    live, example = _service(_load(LIVE)), _service(_load(EXAMPLE))
    assert live_configuration_issues(live, doc) == []
    assert live_configuration_issues(example, doc) == [], "the paid example is durable and says so"

    diskless = copy.deepcopy(example)
    diskless["disk"] = None
    assert any("durable" in issue for issue in live_configuration_issues(diskless, doc)), (
        "a /var/data URL with no disk went unreported"
    )

    tmp_with_disk = copy.deepcopy(live)
    tmp_with_disk["disk"] = {"name": "dsa-data", "mountPath": "/var/data", "sizeGB": 1}
    assert any("ephemeral" in issue for issue in live_configuration_issues(tmp_with_disk, doc)), (
        "a disk attached to a /tmp database went unreported"
    )

    silent = doc.replace("ephemeral", "temporary")
    assert any("no longer says" in issue for issue in live_configuration_issues(live, silent)), (
        "the page stopped naming the ephemerality the blueprint still has"
    )
