"""R-13: two locales, one key set, and no string with a second owner.

A language layer fails in four quiet ways, and each gets a guard here rather than a promise in a comment:

1. **A key exists in one locale only.** The page then renders the fallback and nobody notices in English.
2. **A Chinese value that is actually English.** Pasting the English column into the `zh` block passes every
   rendering test -- so the guard asks the `zh` strings to contain CJK, which is the only property that
   distinguishes a translation from a copy.
3. **A typo in a call site.** `t(locale, "home.cta.askSampl")` renders `⟨home.cta.askSampl⟩` on the page (the
   function is deliberately loud about a missing key), so the guard checks every key referenced in the corpus
   against the dictionary instead of trusting a run to notice.
4. **A page that keeps its own copy.** The strings this requirement covers must live in one place; a hard-coded
   second copy would keep showing English after the switch, so the guard asserts those sentences appear in the
   dictionary and in no other file.

The deliverables themselves are out of scope by the plan's rule: a run's report renders in the language the run
produced, and nothing here translates analysis text.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "apps/web"
LOCALE_TS = WEB / "lib/locale.ts"

#: The first-run strings R-13 names. Each must have exactly one owner: this dictionary.
OWNED_ENGLISH = [
    "The AI data scientist that shows its work.",
    "Ask this of the sample data",
    "Try with your data",
    "Open a finished example",
    "Start with the business question",
    "Inspect where each claim came from",
    "No analysis runs yet in this environment",
]


def _source() -> str:
    return LOCALE_TS.read_text(encoding="utf-8")


def _block(locale: str) -> str:
    """One locale's dictionary body, sliced on the next top-level key."""
    source = _source()
    start = source.index("  " + locale + ": {")
    end = source.index("\n  },", start)
    return source[start:end]


def _keys(locale: str) -> dict[str, str]:
    """`key: "value"` pairs, after folding the line break a long value is wrapped onto.

    The dictionary is written one pair per entry, but a formatter may move the string onto its own line;
    parsing without folding silently drops those keys, and the first version of this helper did exactly that.
    """
    folded = re.sub(r":\s+", ": ", _block(locale))
    return dict(re.findall(r'"([^"]+)": "((?:[^"\\]|\\.)*)"', folded))


def test_both_locales_define_the_same_keys() -> None:
    en, zh = _keys("en"), _keys("zh")
    assert en and zh, f"one of the dictionaries parsed empty (en={len(en)}, zh={len(zh)})"
    assert set(en) == set(zh), (
        f"the locales disagree on keys -- en-only {sorted(set(en) - set(zh))}, zh-only {sorted(set(zh) - set(en))}"
    )
    empty = [key for key, value in {**en, **zh}.items() if not value.strip()]
    assert not empty, f"{empty} have no text, so the page would show a bare key marker"


def test_the_chinese_block_is_actually_chinese() -> None:
    """The failure this prevents is an English string pasted into the `zh` column and shipping green."""
    english_too = sorted(
        key
        for key, value in _keys("zh").items()
        if value and not re.search(r"[\u3400-\u9fff]", value)
    )
    assert not english_too, (
        f"{english_too} carry no CJK character, so switching to 中文 would change nothing on screen"
    )


def test_every_key_a_page_asks_for_exists() -> None:
    wanted: set[str] = set()
    prefixes: set[str] = set()
    for path in list(WEB.glob("app/**/*.tsx")) + list(WEB.glob("lib/**/*.ts")):
        text = path.read_text(encoding="utf-8")
        wanted |= set(re.findall(r'(?<![\w.])t\(\s*\w+\s*,\s*"([^"]+)"\s*\)', text))
        # Template calls are one key per prefix plus a suffix, so the prefixes are checked instead.
        prefixes |= set(re.findall(r"(?<![\w.])t\(\s*\w+\s*,\s*`([^`$]*)\$\{", text))
    defined = set(_keys("en"))
    # A pattern that stopped matching leaves `wanted` empty and every assertion below vacuously true -- which is
    # exactly what the first version of this guard did, passing while collecting nothing. The floor is the fix.
    assert len(wanted) >= 20, f"only {len(wanted)} call sites parsed; the pattern has gone blind"
    assert prefixes, "no template call site parsed, so the numbered step keys are unchecked"
    for prefix in prefixes:
        assert any(key.startswith(prefix) for key in defined), (
            f"a component builds keys from {prefix!r} and the dictionary defines none of them"
        )
    missing = sorted(wanted - defined)
    assert not missing, (
        f"{missing} are referenced by a component but defined by neither locale; the page would render the "
        "missing-key marker rather than fall back quietly, which is the point of the guard"
    )


def test_a_owned_sentence_has_exactly_one_owner() -> None:
    """No page may keep its own copy of a string the dictionary owns, or the switch half-translates."""
    for sentence in OWNED_ENGLISH:
        elsewhere = [
            str(path.relative_to(ROOT))
            for path in list(WEB.glob("app/**/*.tsx"))
            if sentence in path.read_text(encoding="utf-8")
        ]
        assert not elsewhere, (
            f"{sentence!r} is hard-coded in {elsewhere} as well as in the dictionary"
        )
        assert sentence in _source(), f"{sentence!r} is owned by no locale at all"


def test_the_document_language_follows_the_choice() -> None:
    """`lang` is what tells a screen reader which pronunciation table to use; a static "en" lies to it."""
    layout = (WEB / "app/layout.tsx").read_text(encoding="utf-8")
    assert "lang={locale}" in layout, "the document language is hard-coded again"
    assert "await serverLocale()" in layout, "the layout no longer reads the choice off the request"
    header = (WEB / "app/components/layout/SiteHeader.tsx").read_text(encoding="utf-8")
    assert "LanguageToggle" in header, "nothing lets a visitor choose a language"
    toggle = (WEB / "app/components/layout/LanguageToggle.tsx").read_text(encoding="utf-8")
    assert "aria-pressed" in toggle, "the control never says which language is active"
    assert 'role="group"' in toggle and "aria-label" in toggle, (
        "two unlabelled buttons: a screen reader announces the control as nameless"
    )
