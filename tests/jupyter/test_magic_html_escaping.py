"""The %dsa magic renders run- and file-derived text into ``display(HTML(...))``, which notebook frontends insert
unsanitised -- so every sink must escape, and a test that never feeds markup in cannot tell whether it does.

Found by asking which surface had no instrument: `apps/jupyter` is linted and type-checked by CI, but nothing ever
put an HTML metacharacter through it. The reachable source was a CSV's own header row -- `pl.read_csv` keeps it
verbatim (`packages/datasets/src/dsa_datasets/loader.py:66`), the SDK publishes it as `"columns"`
(`src/data_science_agent/sdk.py:444`), and the profile block interpolated the joined list. A user-typed dataset path
and an exception message quoting a bad file reached the same kind of sink. `dsa_jupyter/display.py` escaped every
field it renders; `magic.py` escaped none until this file existed.
"""

from __future__ import annotations

import html
from pathlib import Path

PAYLOAD = "<img src=x onerror=alert(1)>"


def _shell():
    from IPython.testing.globalipapp import get_ipython

    ip = get_ipython()
    try:
        ip.run_line_magic("load_ext", "dsa_jupyter")
    except Exception:
        pass  # already registered by another test in this session
    return ip


def _capture(monkeypatch) -> list[str]:
    """Replace the magic module's `display` with a recorder, and keep only what it renders as HTML.

    The magic also displays plain objects (a polars table, whose repr legitimately quotes a column name), and those
    go to the frontend as `text/plain` where quoting is not a defect. Mixing them in would assert about the wrong
    medium -- and pass or fail for reasons unrelated to escaping.
    """
    import dsa_jupyter.magic as magic

    seen: list[str] = []

    def record(*objs, **kwargs):
        for obj in objs:
            # `HTML(...)` carries the markup in `.data` as a string; a plain object (a polars frame) would only
            # reach the frontend as text/plain, where quoting a column name is not a defect, so it is ignored.
            data = getattr(obj, "data", None)
            if type(obj).__name__ == "HTML" and isinstance(data, str):
                seen.append(data)
            elif isinstance(data, dict) and "text/html" in data:
                seen.append(str(data["text/html"]))

    monkeypatch.setattr(magic, "display", record)
    return seen


def test_a_csv_header_cannot_put_live_markup_in_the_profile_html(
    tmp_path: Path, monkeypatch
) -> None:
    """The header row is data the user supplied, and it reached the rich profile block raw before this."""
    csv = tmp_path / "hostile.csv"
    csv.write_text(f"a,{PAYLOAD}\n1,2\n", encoding="utf-8")

    # The fixture's own proof: interpolated raw, this *is* live markup -- so a green below is not an inert payload.
    assert "<img " in f"<h4>Profile: {PAYLOAD}</h4>", "the fixture string stopped being markup"

    ip = _shell()
    seen = _capture(monkeypatch)
    prof = ip.run_line_magic("dsa", f"profile {csv}")
    assert isinstance(prof, dict) and prof["rows"] == 1, f"profile did not run: {prof!r}"
    document = "".join(seen)
    assert document, "the magic displayed nothing, so nothing about escaping was observed"
    assert PAYLOAD not in document, "a CSV header reached the notebook document verbatim"
    assert "&lt;img" in document, f"the header never reached the document at all: {document[:240]}"
    assert "<img " not in document, "a live tag reached the rendered document"


def test_the_json_view_of_a_profile_escapes_the_dict_it_prints(tmp_path: Path, monkeypatch) -> None:
    """`--json` prints the profile inside <pre>; a dict's repr is not an escape."""
    csv = tmp_path / "hostile2.csv"
    csv.write_text(f"a,{PAYLOAD}\n1,2\n", encoding="utf-8")
    ip = _shell()
    seen = _capture(monkeypatch)
    ip.run_line_magic("dsa", f"profile {csv} --json")
    document = "".join(seen)
    assert document, "the json branch displayed nothing"
    assert PAYLOAD not in document, f"the raw header sits inside the <pre> block: {document[:240]}"
    assert "&lt;img" in document, f"the payload never reached the document: {document[:240]}"


def test_a_failing_path_reports_its_error_escaped(tmp_path: Path, monkeypatch) -> None:
    """The failure message quotes the file the user named, and a filename can carry markup.

    Recorded rather than changed: the magic checks only a dataset path's extension (`detect_format`), so unlike an
    upload it does not run `packages/datasets`' filename validator. Escaping is what keeps that harmless in the
    notebook, and rejecting names the user typed is a behaviour change this test does not presume.
    """
    hostile = tmp_path / "<img/src=x>.csv"
    ip = _shell()
    seen = _capture(monkeypatch)
    result = ip.run_line_magic("dsa", f"profile {hostile}")
    assert result is None, (
        "profiling a file that does not exist should fail, and the failure is the surface here"
    )
    document = "".join(seen)
    assert "Profile failed" in document, f"no failure was displayed: {document[:240]}"
    assert "<img/" not in document, "the requested path reached the notebook as markup"
    assert "&lt;img/" in document, (
        f"the path never reached the document, so the sink was not observed: {document[:240]}"
    )


def test_the_escape_owner_accepts_what_the_sinks_pass() -> None:
    """`escape_html` is the package's single escaper, so it must not raise on the values callers hand it."""
    from dsa_jupyter.display import escape_html

    assert escape_html(None) == "", "a missing value must render as nothing, not abort the cell"
    assert escape_html(5) == "5"
    assert escape_html({"a": "<b>"}) == html.escape("{'a': '<b>'}")
    try:
        html.escape(None)  # type: ignore[arg-type]
    except AttributeError:
        pass  # the stdlib call is str-only, which is exactly why the owner coerces
    else:
        raise AssertionError("html.escape accepted None, so the coercion above guards nothing")
