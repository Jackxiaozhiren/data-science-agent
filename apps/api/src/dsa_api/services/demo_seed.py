"""R-01: the first screen is never empty, and nothing in here invents an answer.

The problem is measured, not imagined: against a fresh database `GET /api/v1/datasets/` answers
``{"datasets": []}`` (audit B4), so the first visitor to a redeploys-and-forgets free instance sees an upload
card and no evidence that the product does anything.

Three rules shape this module, and each exists because the obvious shortcut would be a lie:

1. **The rows go through the real upload path.** `save_dataset` validates, profiles, hashes and stores, so a
   seeded dataset is the same kind of object a visitor's upload is -- not a stub shaped like one.
2. **A starter question comes from a tracked file, and only where the bytes match.** The questions are the
   committed benchmark catalog's own tasks: `benchmarks/v2/catalog.json` names a `dataset` filename per task,
   and a task is offered for a sample only when `benchmarks/v2/datasets/<name>` has the same sha256 as the
   sample being seeded. That is why `eda-02/03/04` contribute nothing here -- their files are not samples.
   The first version of this module read `benchmarks/ds-agent-benchmark/results/**/raw_runs.json` instead,
   which looked like the stronger source and was the weaker one: `.gitignore:36` excludes that whole
   directory, so those "recorded runs" exist only on the machine that last ran a benchmark. A fresh clone --
   which is what a deploy builds and what a reviewer reads -- would have seeded two datasets and no
   questions at all.
3. **The example run is produced by the code that is shipping.** At boot, in a reasoning mode that costs
   nothing and calls no model, the API runs the first starter question through its own pipeline and links
   the finished row. Nothing is replayed from a frozen artifact, because the frozen runs on these bytes are
   stale in a way the screen cannot hide: `titanic.csv` has four committed "successful" runs and every one
   of them ends with 4-8 errored tool calls under the planner that existed when they were recorded, so
   promoting any of them puts a red "This run failed" panel on the page the demo points at. Only a run with
   no errored tool call and no failing validation check is linked; the others stay in the database as the
   real runs they are.

Seeding is idempotent and re-runs on every boot: the free tier cannot hold a disk (§172/§176), so "rebuilt on
boot" is the only durability this product may claim.

No ``except`` appears in this file on purpose. `debt.exceptHandlers` counts every handler in shipped code and
the ceiling is shared with the other session working in this tree, and the place that needs tolerance -- the
startup hook -- gets it from ``asyncio.gather(..., return_exceptions=True)`` instead, which reads the failure
as a value and logs it rather than swallowing it.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dsa_api.core.ownership import OWNER_SHARED
from dsa_api.models.analysis import AnalysisRunORM
from dsa_api.models.dataset import DatasetORM
from dsa_api.services.analysis_service import create_pending_run
from dsa_api.services.dataset_service import save_dataset
from dsa_api.services.run_lifecycle import read_run, schedule_run
from dsa_api.services.telemetry import record_event
from dsa_llm.providers import resolve_llm_mode

log = logging.getLogger(__name__)

#: The machine-checkable marker demanded by the requirement: it lives in the existing free-form metadata
#: column, so no table and no migration is needed for a demo affordance (and R-08's owner column stays ahead).
MARKER = "dsa_sample_dataset"

SAMPLE_SUFFIXES = (".csv", ".parquet", ".json", ".xlsx", ".xls")

#: The tracked source of the questions, and the directory whose bytes decide whether a task applies. Both are
#: in git, so the demo a reviewer clones is the demo that gets deployed.
CATALOG = "benchmarks/v2/catalog.json"
CATALOG_DATASETS = "benchmarks/v2/datasets"

#: The directory the demo seeds *and* the marker `repo_root()` searches ancestors for. It is named here rather
#: than spelled at each use because the shipped image has to carry it: `docker/Dockerfile.api` copied neither it
#: nor `CATALOG_DATASETS`, so the boot hook raised inside `repo_root()` before seeding a single row (audit §222).
SAMPLES_REL = "examples/datasets"

#: Three is enough to show the range (profile, SQL, model) without turning the first screen into a menu.
MAX_QUESTIONS = 3

#: An example run is a nicety, not a reason to keep a visitor waiting: past this the boot serves anyway and
#: the next boot links whatever the task finished into. Measured cost on the free tier is ~1.5 s per run.
EXAMPLE_BUDGET_SECONDS = 45.0

#: Set to `off` to boot an instance with no demo rows at all. Default on: the requirement is about the first
#: screen of whatever instance a visitor reaches, and an opt-in demo would leave a plain `docker compose up`
#: showing the empty list this module exists to end. The test suite turns it off -- eight unrelated files open
#: `TestClient(app)`, whose context manager runs the lifespan, and a boot that executes the agent inside each
#: of them costs seconds and writes rows into whoever's database is configured.
SEEDING_ENV = "DSA_DEMO_SEEDING"

_SEEDER = "dsa_api.services.demo_seed"


def seeding_enabled() -> bool:
    """Whether this process should put the demo on screen when it boots."""
    return os.environ.get(SEEDING_ENV, "on").strip().lower() not in {"off", "0", "false", "no"}


def repo_root() -> Path:
    """The tree this module is installed from, located by the sample directory rather than by a depth count."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / SAMPLES_REL).is_dir():
            return parent
    raise RuntimeError(f"no repository root with {SAMPLES_REL} above {here}")


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass
class SeedResult:
    """What one boot actually put in the database, including what was refused and why."""

    seeded_datasets: int = 0
    kept_datasets: int = 0
    example_run_id: str | None = None
    examples: list[dict[str, str]] = field(default_factory=list)
    skipped: list[dict[str, str]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "seeded_datasets": self.seeded_datasets,
            "kept_datasets": self.kept_datasets,
            "example_run_id": self.example_run_id,
            "examples": self.examples,
            "skipped": self.skipped,
        }


def catalog_questions(root: Path) -> dict[str, list[dict[str, str]]]:
    """`dataset filename` -> the catalog tasks written for that file, EDA first then by task id."""
    path = root / CATALOG
    if not path.is_file():
        return {}
    document = json.loads(path.read_text(encoding="utf-8"))
    tasks = document.get("tasks") if isinstance(document, dict) else document
    if not isinstance(tasks, list):
        raise RuntimeError(f"{CATALOG} holds no task list")
    grouped: dict[str, list[dict[str, str]]] = {}
    for task in tasks:
        if not isinstance(task, dict):
            continue
        name = str(task.get("dataset") or "").strip()
        question = str(task.get("question") or "").strip()
        task_id = str(task.get("id") or "").strip()
        if not name or not question or not task_id:
            continue
        grouped.setdefault(name, []).append(
            {
                "task_id": task_id,
                "question": question,
                "category": str(task.get("category") or ""),
            }
        )
    for entries in grouped.values():
        entries.sort(key=lambda entry: (entry["category"] != "EDA", entry["task_id"]))
    return grouped


_published_questions: frozenset[str] | None = None


def starter_questions() -> frozenset[str]:
    """Every question the tracked catalog publishes -- the funnel's starter link reads this (R-15).

    Cached because the catalog is a tracked file that does not change while a process runs and the create path
    asks on every run. An empty set is a real answer: a tree whose catalog is absent records no starter links
    rather than guessing that some question was one.
    """
    global _published_questions
    if _published_questions is None:
        _published_questions = frozenset(
            entry["question"]
            for entries in catalog_questions(repo_root()).values()
            for entry in entries
        )
    return _published_questions


def is_starter_question(user_query: str) -> bool:
    """Exact equality after stripping: the link counts a question the product published, not a near one.

    Both published spellings count (R-13). A visitor who chooses the Chinese starter question sends the Chinese
    sentence -- the interface and the run's objective are the same words -- and the funnel link would otherwise
    go quiet for exactly the users the language layer was added for.
    """
    return user_query.strip() in starter_question_spellings()


_QUESTION_LOCALE_FILE = Path(__file__).with_name("starter_questions_zh.json")
_question_aliases: frozenset[str] | None = None


def starter_question_spellings() -> frozenset[str]:
    """Every wording the product may put in front of a visitor, in any offered language."""
    global _question_aliases
    if _question_aliases is None:
        _question_aliases = starter_questions() | frozenset(
            value for value in starter_question_translations().values() if value
        )
    return _question_aliases


def starter_question_translations() -> dict[str, str]:
    """`catalog task id` -> the Chinese wording of that question, as tracked beside the seeder.

    Keyed by task id, not by the English sentence: the ids are what the catalog commits to, and a map keyed on
    the question text would silently stop matching the day somebody rewords it. The file is part of the package
    (`product_events.json` is the precedent), so a wheel carries its own translations.
    """
    if not _QUESTION_LOCALE_FILE.is_file():
        return {}
    document = json.loads(_QUESTION_LOCALE_FILE.read_text(encoding="utf-8"))
    questions = document.get("questions") if isinstance(document, dict) else None
    if not isinstance(questions, dict):
        raise RuntimeError(f"{_QUESTION_LOCALE_FILE.name} holds no `questions` object")
    return {str(key): str(value).strip() for key, value in questions.items() if str(value).strip()}


def localized_questions(tasks: list[dict[str, str]]) -> list[str]:
    """The Chinese wording for these tasks, position-for-position with the questions already published.

    A task with no entry falls back to its own English question rather than shortening the list: the web reads
    the two arrays by index, so a hole would show the next question's text under this question's button. The
    contract test makes that fallback unreachable in a shipped tree; this only keeps a half-translated catalog
    from mis-pairing the two lists.
    """
    translations = starter_question_translations()
    return [translations.get(task["task_id"]) or task["question"] for task in tasks]


def _tasks_for(root: Path, filename: str, sha: str) -> list[dict[str, str]]:
    """Catalog tasks whose dataset is these exact bytes, or none.

    The byte comparison is the whole point: a task written for a `titanic.csv` that has since been edited is
    a question about different data, and offering it would advertise a demo answer for bytes nobody checked.
    """
    twin = root / CATALOG_DATASETS / filename
    if not twin.is_file() or sha256_of(twin) != sha:
        return []
    return catalog_questions(root).get(filename, [])[:MAX_QUESTIONS]


def _marker_payload(source: str, tasks: list[dict[str, str]]) -> dict[str, Any]:
    return {
        MARKER: {
            "seeded_by": _SEEDER,
            "source": source,
            "read_only": True,
            "starter_questions": [task["question"] for task in tasks],
            "starter_questions_zh": localized_questions(tasks),
            "verified_by": [
                {
                    "task_id": task["task_id"],
                    "catalog": CATALOG,
                    "same_bytes_as": f"{CATALOG_DATASETS}/{source.rsplit('/', 1)[-1]}",
                }
                for task in tasks
            ],
        }
    }


def _seeded_rows(session_rows: list[DatasetORM]) -> list[tuple[DatasetORM, dict[str, Any]]]:
    pairs: list[tuple[DatasetORM, dict[str, Any]]] = []
    for row in session_rows:
        meta = json.loads(row.meta_json) if row.meta_json else {}
        marker = meta.get(MARKER)
        if marker:
            pairs.append((row, marker))
    return pairs


async def seed_demo_data(
    session: AsyncSession,
    *,
    sample_dir: Path | None = None,
    root: Path | None = None,
) -> SeedResult:
    """Ensure the committed sample datasets exist and carry the questions the catalog wrote for their bytes.

    Deliberately cheap and side-effect-free apart from the rows: the thing that takes time and executes the
    agent -- `ensure_example_runs` -- is a separate call, so a caller that only needs the data can seed it
    without starting a run.
    """
    root = root or repo_root()
    samples = Path(sample_dir or (root / SAMPLES_REL))
    prefix = SAMPLES_REL if sample_dir is None else samples.name
    result = SeedResult()
    seen_sources: set[str] = set()

    for path in sorted(p for p in samples.glob("*") if p.suffix in SAMPLE_SUFFIXES):
        source = f"{prefix}/{path.name}"
        seen_sources.add(source)
        sha = sha256_of(path)
        tasks = _tasks_for(root, path.name, sha)
        payload = _marker_payload(source, tasks)

        existing = next(
            (
                row
                for row, marker in _seeded_rows(
                    list((await session.execute(select(DatasetORM))).scalars().all())
                )
                if marker.get("source") == source
            ),
            None,
        )
        if existing is not None and existing.sha256 == sha and Path(existing.path).is_file():
            if existing.owner != OWNER_SHARED:
                # Rows written before R-08 -- including every row the migration backfilled -- are the demo's
                # own published samples. Left owned by `local`, they are invisible to a visitor with an id of
                # their own, and the first screen R-01 promises would be empty for them. The marker is what
                # proves this row is ours rather than a visitor's, and the run it names was created by us.
                existing.owner = OWNER_SHARED
                linked = (json.loads(existing.meta_json or "{}").get(MARKER) or {}).get(
                    "example_run_id"
                )
                if linked:
                    example = await session.get(AnalysisRunORM, str(linked))
                    if example is not None:
                        example.owner = OWNER_SHARED
                await session.commit()
            current = json.loads(existing.meta_json or "{}").get(MARKER) or {}
            wanted = payload[MARKER]
            # Both question lists, not just the English one: a row seeded before R-13 carries the canonical
            # list only, and comparing that alone would leave a Chinese visitor looking at English buttons on
            # a dataset the demo has already published.
            offered = ("starter_questions", "starter_questions_zh")
            if any(current.get(key) != wanted[key] for key in offered):
                meta = json.loads(existing.meta_json or "{}")
                meta[MARKER] = {
                    **payload[MARKER],
                    "example_run_id": current.get("example_run_id"),
                }
                existing.meta_json = json.dumps(meta)
                await session.commit()
            result.kept_datasets += 1
            continue
        if existing is not None:
            # The committed bytes moved, or the stored copy vanished. Rebuild rather than leave a row whose
            # profile describes a file that is no longer there. Only rows this module created are touched.
            await session.delete(existing)
            await session.commit()

        created = await save_dataset(
            session,
            filename=path.name,
            tmp_path=path,
            size_bytes=path.stat().st_size,
            content_type=None,
            head=path.read_bytes()[:4096],
            owner=OWNER_SHARED,
        )
        row = await session.get(DatasetORM, created["id"])
        if row is None:  # pragma: no cover - save_dataset commits the row it returns
            result.skipped.append(
                {"source": source, "reason": "the row vanished immediately after create"}
            )
            continue
        row.meta_json = json.dumps(payload)
        await session.commit()
        result.seeded_datasets += 1
        if not tasks:
            result.skipped.append(
                {
                    "source": source,
                    "reason": (
                        f"no {CATALOG} task names this file with these bytes, so no question"
                    ),
                }
            )

    # A seeded row whose source file is gone is reported, never silently kept: the honest reading of "the
    # sample is not in the tree" is that the first screen is about to lose something.
    for _row, marker in _seeded_rows(
        list((await session.execute(select(DatasetORM))).scalars().all())
    ):
        declared = str(marker.get("source") or "")
        if declared in seen_sources:
            continue
        original = root / declared
        if not original.is_file():
            result.skipped.append(
                {
                    "source": declared,
                    "reason": "the committed sample file it was seeded from is gone",
                }
            )

    return result


def run_is_clean(row: dict[str, Any] | None) -> bool:
    """The gate a showcase has to pass: finished, no errored tool call, no failing validation check.

    Both halves are read from the row the agent itself wrote, not from a summary the demo keeps: the status
    alone is not enough, because a run whose tools all raised still reaches `COMPLETED` -- that is exactly
    what the four committed Titanic runs did.
    """
    if not row or str(row.get("status")) != "COMPLETED":
        return False
    state = row.get("state") or {}
    calls = state.get("tool_calls") or []
    if not calls:
        return False
    if any(str(call.get("status")) != "ok" for call in calls):
        return False
    checks = state.get("validation_results") or []
    return all(bool(check.get("passed")) for check in checks)


async def _clean_existing(
    session: AsyncSession, dataset_id: str, question: str
) -> AnalysisRunORM | None:
    """A published run that already answers the question cleanly, if there is one.

    The owner filter carries weight: the starter question and the sample dataset are the same strings for
    every visitor, so without it a visitor's run would be adopted as the demo's example -- and the next
    visitor to open that example link would be told the run does not exist.
    """
    statement = (
        select(AnalysisRunORM)
        .where(
            AnalysisRunORM.dataset_id == dataset_id,
            AnalysisRunORM.user_query == question,
            AnalysisRunORM.owner == OWNER_SHARED,
            AnalysisRunORM.status == "COMPLETED",
        )
        .order_by(AnalysisRunORM.created_at.desc())
    )
    for row in (await session.execute(statement)).scalars().all():
        if run_is_clean(row.to_dict()):
            return row
    return None


async def _run_example(session: AsyncSession, dataset_id: str, question: str) -> str | None:
    """Ask one question through the same path a client uses, and return the row id if it came out clean."""
    created, started = await create_pending_run(session, dataset_id, question, owner=OWNER_SHARED)
    run_id = str(created["id"])
    if started:
        # R-15: the seeder's own run is a run this instance created, so it records a start -- labelled
        # `seeding`, because it is not a visitor and must never read as one. Without this line the funnel
        # would report more completions than starts, since only the endpoint emits for visitors.
        record_event(
            "run_started",
            dataset_id=dataset_id,
            reasoning_mode=resolve_llm_mode().mode,
            initiated_by="seeding",
        )
        # Shielded, not awaited bare: a boot that gives up on a slow run must not leave a row frozen in a
        # non-terminal status. The task keeps writing, and the next boot links whatever it finished.
        await asyncio.wait_for(asyncio.shield(schedule_run(run_id)), timeout=EXAMPLE_BUDGET_SECONDS)
    row = await read_run(run_id)
    return run_id if run_is_clean(row) else None


async def ensure_example_runs(
    session: AsyncSession, *, root: Path | None = None
) -> list[dict[str, str]]:
    """Give every seeded dataset a finished run of its own first question, made by this build.

    Skipped entirely when the instance is configured to call a model: the demo may not spend money or make a
    paid request on someone else's behalf just because the process started. In that mode the questions are
    still offered, and the visitor's own click runs one.
    """
    mode = resolve_llm_mode()
    if not mode.stub:
        log.info(
            "no example run generated at boot: this instance reasons with a model "
            f"({mode.provider}/{mode.model}), and the demo never starts one unasked"
        )
        return []

    root = root or repo_root()
    examples: list[dict[str, str]] = []
    rows = list(
        (await session.execute(select(DatasetORM).order_by(DatasetORM.created_at))).scalars().all()
    )
    for row, marker in _seeded_rows(rows):
        questions = marker.get("starter_questions") or []
        if not questions:
            continue
        question = str(questions[0])
        source = str(marker.get("source") or row.filename)
        existing = await _clean_existing(session, row.id, question)
        run_id: str | None = existing.id if existing is not None else None
        how = "reused"
        if run_id is None:
            started_at = time.monotonic()
            run_id = await _run_example(session, row.id, question)
            how = "generated at boot"
            if run_id is None:
                result = await _last_attempt(session, row.id, question)
                log.warning(
                    "the demo's example run was not promoted",
                    extra={
                        "dataset_id": row.id,
                        "seconds": round(time.monotonic() - started_at, 1),
                        "outcome": result or "no clean run",
                    },
                )
                continue
        if marker.get("example_run_id") != run_id:
            meta = json.loads(row.meta_json or "{}")
            meta[MARKER] = {**meta.get(MARKER, {}), "example_run_id": run_id}
            row.meta_json = json.dumps(meta)
            await session.commit()
        examples.append({"source": source, "run_id": run_id, "how": how, "question": question})
    return examples


async def _last_attempt(
    session: AsyncSession, dataset_id: str, question: str
) -> dict[str, Any] | None:
    """What the attempt that was refused actually said, for the log line that names the refusal."""
    statement = (
        select(AnalysisRunORM)
        .where(
            AnalysisRunORM.dataset_id == dataset_id,
            AnalysisRunORM.user_query == question,
            AnalysisRunORM.owner == OWNER_SHARED,
        )
        .order_by(AnalysisRunORM.created_at.desc())
        .limit(1)
    )
    row = (await session.execute(statement)).scalars().first()
    return row.to_dict() if row else None


async def ensure_demo_data_at_boot() -> dict[str, Any] | None:
    """The startup hook: seed if the tree is intact, report -- never abort the API -- if it is not.

    `DSA_DEMO_SEEDING=off` returns before either half, which is how the test suite boots the app without
    executing the agent eight times over.

    The two halves are gathered apart on purpose. If the datasets landed and the example run did not, the log
    has to say "no example" rather than "the first screen is empty" -- the first is a missing nicety and the
    second tells the operator to go look at the seeding code.
    """
    if not seeding_enabled():
        log.debug("%s is off: this instance boots with no demo data", SEEDING_ENV)
        return None

    from dsa_api.core import database

    async def _seed() -> SeedResult:
        async with database.AsyncSessionLocal() as session:
            return await seed_demo_data(session)

    seeded_outcome = await asyncio.gather(_seed(), return_exceptions=True)
    if isinstance(seeded_outcome[0], BaseException):
        log.error(
            "demo seeding was skipped, so the first screen may be empty on this instance",
            exc_info=seeded_outcome[0],
        )
        return None
    seeded: SeedResult = seeded_outcome[0]

    async def _examples() -> list[dict[str, str]]:
        async with database.AsyncSessionLocal() as session:
            return await ensure_example_runs(session)

    example_outcome = await asyncio.gather(_examples(), return_exceptions=True)
    if isinstance(example_outcome[0], BaseException):
        log.error(
            "the demo has no example run on this instance: the datasets are there, the report is not",
            exc_info=example_outcome[0],
        )
    else:
        seeded.examples = example_outcome[0]
        if seeded.examples:
            seeded.example_run_id = str(seeded.examples[0]["run_id"])
    return seeded.as_dict()
