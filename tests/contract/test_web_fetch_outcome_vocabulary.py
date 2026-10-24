"""Contract: the web fetch-outcome vocabulary is complete, and no page collapses a failed request again.

Audit §160 item 6, §164 (the maintainer picked option (i)) and §166. The defect was that every non-2xx
response rendered as "there is no data", while `docs/api.md:13-15` tells operators to set
`DSA_AUTH_TOKEN` -- which makes `/api/*` answer 401 and leaves `/health` public, so
`apps/web/app/components/layout/ApiStatusDot.tsx` painted "API connected" beside pages claiming the
product was empty. The closing paragraph of *Troubleshooting the browser demo* in `docs/hosted-demo.md`
already promised transport failures and 4xx/5xx would be told apart from absence.

Two properties are pinned, in both directions, for the reason
`tests/contract/test_web_analysis_status_vocabulary.py` pins the run-status vocabulary: the kinds are owned in
`apps/web/lib/api.ts`, the words in `apps/web/lib/locale.ts`, their consumers are scattered across pages, and
nothing else connects them.

1. `API_FAILURE_KINDS`, the literals `classifyResponse` can return, the keys `failurePresentation` builds, and
   the `fail.*` dictionary entries in *both* locales are one set. A kind the classifier emits but the renderer
   does not name would show a reader the missing-key marker; an entry no branch produces is dead copy.
2. `!response.ok` sites are accounted for by owner, not by line number, because a line number moves the
   moment anyone edits a file and a rename of the response variable must not redden this:
   - pages converted in §166 may hold only the declared best-effort or POST-error sites;
   - a site that `throw`s is not a collapse and is allowed anywhere;
   - pages another session holds uncommitted (audit §164's fence) are pending, and this file names them
     so the debt stays visible instead of becoming a silent carve-out;
   - anywhere else, a new collapse site fails this test.

The last clause is what a later session must clear: converting a pending page means deleting it from
PENDING_SITES in the same commit, and the test then proves the page holds no collapse of its own.

A third property came with R-13. Five pages override the `transport` line with a sentence of their own --
naming the fallback the reader is actually looking at -- and each of those sentences is a reader-facing line
like any other. So an override must name a dictionary key; an inline English string here would put the
vocabulary back in two owners and render English under the 中文 switch.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API_MODULE = ROOT / "apps/web/lib/api.ts"
LOCALE_MODULE = ROOT / "apps/web/lib/locale.ts"
WEB_APP = ROOT / "apps/web/app"

VOCABULARY = {"unauthorized", "notFound", "serverError", "clientError", "transport"}

#: Pages that classify their fetch outcomes (audit §166). Relative to apps/web/app.
CONVERTED_PAGES = [
    "page.tsx",
    "analysis/page.tsx",
    "analysis/[runId]/page.tsx",
    "analysis/[runId]/RunInspector.tsx",
    "datasets/page.tsx",
    "datasets/[id]/page.tsx",
    "failures/page.tsx",
    "mcp/page.tsx",
    "reports/page.tsx",
    "research/page.tsx",
    "runs/page.tsx",
    "runs/[id]/page.tsx",
]

#: Declared non-collapse uses inside a converted page: a POST's own error branch, or a best-effort
#: secondary request whose absence is already disclosed by the page. Keyed by normalised source line.
DECLARED_WITHIN_CONVERTED: dict[str, dict[str, int]] = {
    "failures/page.tsx": {"if (!RESP.ok) return;": 1},
    "analysis/page.tsx": {"if (!RESP.ok) return;": 1, "if (!RESP.ok) {": 1},
    "datasets/page.tsx": {"if (!RESP.ok) {": 1},
    # The two POST branches report the API's own detail into `err` and render it; the poll keeps the last
    # good progress and retries on the next tick, which the live card above it discloses as a phase.
    "analysis/[runId]/RunInspector.tsx": {
        "if (!RESP.ok || stop) return;": 1,
        "if (!RESP.ok) {": 2,
    },
}

#: Closed on 2026-10-15: the last two pages that collapsed a failed request into an empty shape now classify
#: it (audit §179's download work carried `analysis/[runId]/*` over). The set is kept as an empty inventory
#: rather than deleted, because `test_no_other_page_collapses_or_waits_unlisted` compares the pages it finds
#: collapsing against exactly this list -- an absent name there is a page that regressed quietly.
PENDING_SITES: set[str] = set()

RAISES = "throw"


def _api_source() -> str:
    assert API_MODULE.is_file(), (
        f"{API_MODULE.relative_to(ROOT)} is missing -- the vocabulary has no owner"
    )
    return API_MODULE.read_text(encoding="utf-8")


def _classifier_body(source: str) -> str:
    match = re.search(
        r"export function classifyResponse\(res: Response\)[^\n]*\{(.*?)\n\}", source, re.DOTALL
    )
    assert match is not None, "classifyResponse is gone from the vocabulary module"
    return match.group(1)


def _kind_literals(source: str, name: str) -> set[str]:
    match = re.search(
        rf"export const {re.escape(name)}\s*=\s*\[(.*?)\]\s*as const", source, re.DOTALL
    )
    assert match is not None, f"{name} is gone from {API_MODULE.relative_to(ROOT)}"
    return {
        single or double for single, double in re.findall(r"'([^']*)'|\"([^\"]*)\"", match.group(1))
    }


def _presentation_keys(source: str) -> set[str]:
    """The kinds `failurePresentation` names a line for -- read from its object literal, not its type."""
    match = re.search(
        r"export function failurePresentation\(locale: Locale\): Record<ApiFailure, string> "
        r"\{\s*return \{(.*?)\n  \};",
        source,
        re.DOTALL,
    )
    assert match is not None, (
        "failurePresentation is gone, or it no longer returns a Record<ApiFailure, string> literal built per "
        "kind -- a computed record would drop the compile-time check that every kind has a line"
    )
    return set(re.findall(r"^\s{4}([A-Za-z][A-Za-z0-9]*):", match.group(1), re.MULTILINE))


def _dictionary_keys(locale: str, prefix: str) -> set[str]:
    """One locale's `prefix.*` keys, after folding the line break a long value is wrapped onto.

    Same reason as in `test_web_locale_parity.py`: without the fold, an entry whose string sits on its own
    line is silently invisible, and an empty result would make every assertion below vacuously true.
    """
    folded = re.sub(r":\s+", ": ", LOCALE_MODULE.read_text(encoding="utf-8"))
    parts = folded.split(f"{locale}: {{", 1)
    assert len(parts) == 2, f"UI_STRINGS has no {locale} block written the way this guard parses it"
    body = parts[1].split("\n  },", 1)[0]
    found = set(re.findall(rf'"{re.escape(prefix)}([^"]+)":', body))
    assert found, f"no {prefix}* key parsed from the {locale} block -- the pattern went blind"
    return found


def _collapse_lines(text: str) -> list[str]:
    """Every `!response.ok` line, with the variable name normalised away."""
    out: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if re.search(r"!\s*[A-Za-z_][A-Za-z0-9_]*\.ok", stripped):
            out.append(re.sub(r"!\s*[A-Za-z_][A-Za-z0-9_]*\.ok", "!RESP.ok", stripped))
    return out


def _sources(root: Path) -> dict[str, str]:
    files = sorted(root.rglob("*.tsx")) + sorted(root.rglob("*.ts"))
    assert len(files) >= 20, f"only {len(files)} web source files -- the walk broke"
    return {str(p.relative_to(root)): p.read_text(encoding="utf-8") for p in files}


#: Kinds `classifyResponse` can produce. `transport` is not among them: it is the outcome of a request
#: that never produced a Response, so it is returned by the callers' `catch`, and the test below checks
#: it is reachable that way rather than pretending the classifier can see it.
STATUS_DERIVED = {"unauthorized", "notFound", "serverError", "clientError"}


def test_vocabulary_is_the_measured_shape() -> None:
    """The premise of everything below: five kinds, and no sixth appears unannounced."""
    assert _kind_literals(_api_source(), "API_FAILURE_KINDS") == VOCABULARY


def test_classifier_and_presentation_agree_with_the_vocabulary() -> None:
    source = _api_source()
    emitted = set(re.findall(r'return\s+"([A-Za-z][A-Za-z0-9]*)"', _classifier_body(source)))
    assert emitted == STATUS_DERIVED, (
        f"classifyResponse emits {sorted(emitted)}, not the status-derived kinds"
    )
    assert _presentation_keys(source) == VOCABULARY, (
        "a kind has no reader-facing line, or the copy is dead"
    )
    assert VOCABULARY - emitted == {"transport"}, "only transport may live outside the classifier"
    for locale in ("en", "zh"):
        keys = _dictionary_keys(locale, "fail.")
        assert keys == VOCABULARY, (
            f"the {locale} fail.* entries {sorted(keys)} are not the vocabulary {sorted(VOCABULARY)} -- "
            "a kind with no line renders ⟨fail.kind⟩, an extra entry is a sentence no page can reach"
        )


def test_transport_is_reachable_where_a_response_never_arrives() -> None:
    """A kind nothing can produce is dead vocabulary; transport must be what the catch branches return."""
    produced = [
        rel
        for rel, text in _sources(WEB_APP).items()
        if re.search(r"failure:\s*\"transport\"", text)
    ]
    assert len(produced) >= 9, (
        f"only {len(produced)} pages can produce transport (9 as of 2026-10-12) -- a shared line no code "
        f"can emit: {sorted(produced)}"
    )


def test_every_kind_maps_to_its_own_status_class() -> None:
    """Guards the actual bug: a 401 must read as `unauthorized`, never as an empty payload."""
    body = _classifier_body(_api_source())
    assert re.search(
        r"res\.status === 401 \|\| res\.status === 403\)\s*\n?\s*return \"unauthorized\";", body
    )
    assert re.search(r"res\.status === 404\)\s*\n?\s*return \"notFound\";", body)
    assert re.search(r"res\.status >= 500\)\s*\n?\s*return \"serverError\";", body)
    assert "if (res.ok) return null;" in body, (
        "a 2xx must not be classified, or success reads as failure"
    )


def test_converted_pages_hold_only_declared_non_collapse_sites() -> None:
    sources = _sources(WEB_APP)
    for rel in CONVERTED_PAGES:
        assert rel in sources, (
            f"{rel} disappeared from the web app -- update CONVERTED_PAGES deliberately"
        )
        actual = Counter(_collapse_lines(sources[rel]))
        allowed = Counter(DECLARED_WITHIN_CONVERTED.get(rel, {}))
        unaccounted = actual - allowed
        assert not unaccounted, (
            f"{rel} collapses a failed request: {sorted(unaccounted.elements())}"
        )


def test_no_other_page_collapses_or_waits_unlisted() -> None:
    """A new page cannot collapse quietly, and a pending page cannot vanish from the list unannounced."""
    sources = _sources(WEB_APP)
    accounted = set(CONVERTED_PAGES)
    unexpected: list[str] = []
    for rel, text in sources.items():
        if rel in accounted:
            continue
        lines = _collapse_lines(text)
        if not lines:
            continue
        raising_only = all(RAISES in line for line in lines)
        if raising_only:
            continue  # a guard that throws is handled by the caller, not collapsed
        assert rel in PENDING_SITES, (
            f"{rel} collapses a non-2xx into an empty shape and is not in the inventory"
        )
        unexpected.append(rel)
    assert set(unexpected) == PENDING_SITES, (
        f"pending pages moved without this file moving: pending-now={sorted(unexpected)}, listed={sorted(PENDING_SITES)}"
    )


def test_pages_that_classify_import_the_vocabulary() -> None:
    """Consumers must take their kinds from the owner rather than hand-copying names.

    R-13 moved the words into the string owner, so the only shared name a page may reference is
    `failurePresentation()`, which builds one view per language. What is still refused is a page writing its
    own sentence for a kind.
    """
    for rel, text in _sources(WEB_APP).items():
        if "classifyResponse(" not in text:
            continue
        assert 'from "@/lib/api"' in text, f"{rel} calls classifyResponse without importing it"
        assert "failurePresentation(" in text, (
            f"{rel} classifies a failure but renders no shared line for it"
        )


def test_a_page_override_names_a_dictionary_key() -> None:
    """A page may replace the transport line, but not own its wording.

    The override exists because "no response arrived" is not the whole disclosure: a reader looking at an
    empty report list needs to know the list is a fallback. That sentence is still a reader-facing line, so it
    lives in the dictionary and the page only names it. An inline string here is the two-owner split back
    again, and it would keep reading English after the visitor switched to 中文.
    """
    overrides: list[tuple[str, str]] = []
    inline: list[tuple[str, str]] = []
    for rel, text in _sources(WEB_APP).items():
        inline += [(rel, found) for found in re.findall(r'transport:\s*"[^"]*"', text)]
        overrides += [
            (rel, key) for key in re.findall(r'transport:\s*t\(locale,\s*"([^"]+)"\)', text)
        ]
    assert not inline, (
        f"{inline} own a transport sentence in the page: two owners, and English only"
    )
    assert len(overrides) >= 5, (
        f"only {len(overrides)} pages override the transport line (5 as of 2026-10-18) -- the pattern went "
        "blind, or the fallback disclosures were dropped from the pages that had them"
    )
    defined = {locale: _dictionary_keys(locale, "") for locale in ("en", "zh")}
    for rel, key in overrides:
        assert key.endswith(".transport"), (
            f"{rel} overrides transport with {key!r}, which is not a *transport key"
        )
        for locale, keys in defined.items():
            assert key in keys, (
                f"{rel} asks for {key!r}, which {locale} does not define -- the reader sees ⟨{key}⟩"
            )


def test_the_presentation_is_derived_from_the_string_owner_in_both_languages() -> None:
    """One owner per line, including the language layer's own.

    The record used to carry the English sentences and `lib/locale.ts` carried nothing for failures; that split
    is how a reworded line ends up in two places and disagrees with itself. So the renderer must build every
    kind by key name through `t(locale, ...)`, and the English constant it used to hold must stay gone -- an
    `en`-only record beside a bilingual function is the same split wearing a different hat.
    """
    source = _api_source()
    for kind in sorted(VOCABULARY):
        assert re.search(rf'{kind}:\s*t\(locale, "fail\.{kind}"\)', source), (
            f"{kind} is no longer derived from the string owner -- an inline English sentence here would be a "
            "second copy of the line, and the zh view would drift from it silently"
        )
    assert "FAILURE_PRESENTATION" not in source, (
        "the English-only record is back: with a page per language nothing imports it, and the sentences it "
        "held would stop being the ones readers see"
    )


def test_the_inventory_check_can_fail(tmp_path: Path) -> None:
    """A guard that cannot fail is decoration, so this proves it fires -- on a copy, never on the tree."""
    target = WEB_APP / "mcp" / "page.tsx"
    assert target.is_file(), "the control target vanished"
    original = target.read_text(encoding="utf-8")
    assert "classifyResponse(res)" in original, (
        "the control target no longer classifies; pick another page"
    )
    mutated = original.replace(
        "const failure = classifyResponse(res);",
        "const failure = classifyResponse(res);\n    if (!res.ok) return { tools: [], failure: null };",
        1,
    )
    assert mutated != original, "the control mutation did not land"
    staging = tmp_path / "mcp"
    staging.mkdir()
    (staging / "page.tsx").write_text(mutated, encoding="utf-8")

    # The collapse appears in the converted page's own accounting...
    added = Counter(_collapse_lines((staging / "page.tsx").read_text(encoding="utf-8")))
    allowed = Counter(DECLARED_WITHIN_CONVERTED.get("mcp/page.tsx", {}))
    assert added - allowed, (
        "the mutated page produced no unaccounted collapse, so the check is decorative"
    )

    # ...and the walk itself still enumerates the real tree, so the guard is not reading a stale list.
    live = Counter(_collapse_lines(target.read_text(encoding="utf-8")))
    assert not (live - allowed), (
        "the unmutated page already fails its own allowance, so the control proves nothing"
    )
