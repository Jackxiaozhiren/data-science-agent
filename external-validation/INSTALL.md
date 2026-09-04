# INSTALL — External Reviewer Setup (V4.3 W8 §76)

> Audience: an independent reviewer with **no prior knowledge of this project**.
> Time: ≈5-10 minutes. No project-internal credentials are needed.

## 0. Prerequisites

- Python **3.12** (check: `python3 --version`)
- macOS, Linux, or Windows; ~500 MB free disk
- Optional: [GitHub CLI](https://cli.github.com/) (`gh`) for provenance verification (Task 6)

## 1. Install the published package

```bash
python3 -m venv .dsa-review-venv
source .dsa-review-venv/bin/activate        # Windows: .dsa-review-venv\Scripts\activate
pip install --upgrade pip
pip install jack-data-science-agent
```

Record the installed version — you will need it in your feedback:

```bash
pip show jack-data-science-agent | grep -E "^(Name|Version)"
```

## 2. Verify the CLI works

```bash
dsa doctor
```

Expected: a diagnostic report (an LLM-configuration `warn` line is expected — the
demo runs fully offline with a deterministic local pipeline and needs **no API key**).

## 3. (Optional, alternative source) Run from source instead of PyPI

```bash
git clone https://github.com/Jackxiaozhiren/data-science-agent.git
cd data-science-agent
uv sync          # or: pip install -e .
uv run dsa doctor
```

Source installs are acceptable for review; note in your feedback which install path
you used, so results are attributable.

## 4. (Optional) Provenance pre-check before Task 6

The maintainer-documented verification procedure lives at
`docs/security/VERIFY_RELEASE.md` in the repository. You do not need it to complete
Tasks 1-5; Task 6 walks you through the check.

## 5. Housekeeping

All reviewer work happens in your own machine and your own scratch directory. The
agent writes runs under `demo/runs/` (or a workspace you point it at); nothing is
uploaded anywhere by the tool itself.
