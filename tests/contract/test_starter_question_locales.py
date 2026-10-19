"""R-13: the demo's starter questions exist in both languages the interface offers, and the funnel still links.

The product asks a first question on the visitor's behalf. When the interface is Chinese that question is sent
in Chinese -- the run's objective and the button the visitor pressed are the same words, which is what R-13
asks for and what a translated label over an English payload would not be.

Two consequences, both guarded here rather than assumed:

* the wording has one owner. `starter_questions_zh.json` sits beside the seeder and is keyed by catalog task
  id, because the ids are what `benchmarks/v2/catalog.json` commits to. A map keyed on the English sentence
  would stop matching the day somebody rewords it, and it would fail quietly -- the visitor would simply be
  back to English with nothing red anywhere.
* `is_starter_question` has to know both spellings. It is the link that turns a click into the funnel's
  ``starter_question_used`` event (R-15); matching only the English text means the language layer silences the
  measurement for exactly the users it was added for.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from dsa_api.services.demo_seed import (
    SAMPLE_SUFFIXES,
    _tasks_for,
    catalog_questions,
    is_starter_question,
    localized_questions,
    repo_root,
    sha256_of,
    starter_question_spellings,
    starter_question_translations,
)

ROOT = Path(__file__).resolve().parents[2]
LOCALE_FILE = ROOT / "apps/api/src/dsa_api/services/starter_questions_zh.json"


def _offered_tasks() -> list[dict[str, str]]:
    """The tasks the demo can actually put in front of a visitor.

    Walked with the seeder's own `_tasks_for`, not a restatement of its rule: the offer depends on the sample
    bytes matching the catalog twin, and some catalog datasets are not samples at all. A test that re-derives
    that from filenames checks a set the product never publishes.
    """
    root = repo_root()
    samples = root / "examples" / "datasets"
    offered: list[dict[str, str]] = []
    for path in sorted(p for p in samples.glob("*") if p.suffix in SAMPLE_SUFFIXES):
        offered.extend(_tasks_for(root, path.name, sha256_of(path)))
    return offered


def test_locale_file_is_parseable_and_named_in_the_seeder() -> None:
    assert LOCALE_FILE.is_file(), (
        f"{LOCALE_FILE.relative_to(ROOT)} is missing -- where did the wording go?"
    )
    document = json.loads(LOCALE_FILE.read_text(encoding="utf-8"))
    assert document.get("locale") == "zh", document.get("locale")
    assert document.get("catalog") == "benchmarks/v2/catalog.json", (
        "the file no longer names the catalog its ids come from, so the coverage assertion below is unchecked"
    )
    assert isinstance(document.get("questions"), dict) and document["questions"], (
        "empty `questions` object"
    )


def test_every_offered_question_has_chinese_wording() -> None:
    translations = starter_question_translations()
    offered = _offered_tasks()
    assert offered, (
        "no offered tasks resolved -- the seeder's catalog or sample list moved and this guard is blind"
    )
    missing = sorted(
        {
            f"{task['task_id']} ({task['dataset']}): {task['question'][:48]!r}"
            for task in offered
            if task["task_id"] not in translations
        }
    )
    assert not missing, (
        f"{len(missing)} offered starter question(s) have no Chinese wording; a Chinese interface would show "
        "English buttons and the seeder's fallback would publish the English text twice:\n  "
        + "\n  ".join(missing)
    )


def test_translation_ids_name_a_real_catalog_task() -> None:
    translations = starter_question_translations()
    known = {
        task["task_id"] for entries in catalog_questions(repo_root()).values() for task in entries
    }
    orphans = sorted(set(translations) - known)
    assert not orphans, (
        f"{orphans} name no catalog task: the question was renamed or deleted and the wording is now dead text"
    )


def test_each_translation_is_actually_in_the_other_language() -> None:
    """A copy-paste of the English string satisfies the coverage test and delivers nothing.

    So the check is on the value: it must carry CJK and must not be byte-equal to its catalog question.
    """
    translations = starter_question_translations()
    by_id = {task["task_id"]: task["question"] for task in _offered_tasks()}
    for task_id, text in sorted(translations.items()):
        if task_id not in by_id:
            continue
        assert re.search(r"[\u4e00-\u9fff]", text), f"{task_id} is not Chinese: {text!r}"
        assert text != by_id[task_id], f"{task_id} repeats the English question"


def test_the_link_counts_either_spelling_and_neither_a_near_miss() -> None:
    for task in _offered_tasks()[:12]:
        english = task["question"]
        chinese = localized_questions([task])[0]
        assert is_starter_question(english), f"{english!r} is published but not recognised"
        assert is_starter_question(chinese), f"{chinese!r} is published but not recognised"
        assert not is_starter_question(english + " (edited)"), (
            "the link matched a question nobody published"
        )
        assert not is_starter_question(chinese + "（改写）"), (
            "the link matched a question nobody published"
        )


def test_the_two_published_lists_stay_the_same_length() -> None:
    """The web reads them by index, so a hole would show one question's text under another's button."""
    offered = _offered_tasks()
    english = [task["question"] for task in offered]
    chinese = localized_questions(offered)
    assert len(english) == len(chinese), f"{len(english)} vs {len(chinese)}"
    assert chinese[:3] != english[:3], (
        "the whole list fell back to English -- the alias table is not loading"
    )


def test_the_spelling_set_actually_adds_the_second_language() -> None:
    """`is_starter_question` reads this set, so a union that is just the English list restated is the bug."""
    spellings = starter_question_spellings()
    offered = _offered_tasks()
    english = {task["question"] for task in offered}
    chinese = set(localized_questions(offered))
    assert english | chinese <= spellings, (
        f"published spellings missing from the link set: {sorted((english | chinese) - spellings)[:3]}"
    )
    assert chinese - english, (
        "the alias table adds no wording: every Chinese question equals its English text, so the link set "
        "was never widened and a Chinese click goes uncounted"
    )


def test_only_the_seeder_reads_the_published_lists() -> None:
    """§9 naming discipline: the marker's question lists have one owner, and it is not a component.

    Production code is enumerated (tests are free to read the marker shape -- that is how they check it). A
    second reader would go red here instead of drifting into a screen that offers a question the funnel does
    not recognise.
    """
    readers: list[str] = []
    for directory in ("apps", "packages", "scripts"):
        for path in (ROOT / directory).rglob("*.py"):
            if "_vendor" in path.parts or path.name == "demo_seed.py":
                continue
            if re.search(
                r"""["']starter_questions(?:_zh)?["']""", path.read_text(encoding="utf-8")
            ):
                readers.append(path.relative_to(ROOT).as_posix())
    vendored = [
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "src").rglob("*.py")
        if re.search(r"""["']starter_questions(?:_zh)?["']""", path.read_text(encoding="utf-8"))
        and "_vendor/dsa_api/services/demo_seed.py" not in path.as_posix()
    ]
    assert not readers, (
        f"the published question lists are being read outside their owner: {sorted(readers)}"
    )
    assert not vendored, f"the vendored copy has a second reader of its own: {sorted(vendored)}"
