# Data Science Agent v4.2.10

> Released 2026-08-27 · Evidence-grounded autonomous data science, from natural-language questions to reproducible analysis.

## Install or upgrade

```bash
pip install -U jack-data-science-agent
```

## Why this release matters

`v4.2.10` is the first fully working PyPI release through **Trusted Publishing (OIDC)** with publishing attestations attached.

The `jack-data-science-agent` umbrella package is now self-contained: the `dsa_*` modules are vendored into the wheel, so a normal `pip install jack-data-science-agent` does not require separately published `dsa-*` distributions.

## Verified release gates

- `pip install jack-data-science-agent` succeeds from PyPI;
- `Agent().analyze_sync()` runs end to end from the installed package and produces `COMPLETED` + evidence;
- wheel contains the `dsa` console script with no separate `dsa-*` `Requires-Dist` entries;
- `pytest`: **257 passed**;
- `mypy`: **104 clean**;
- Ruff: **pass**;
- MkDocs strict build: **pass**.

## Supply-chain provenance

The GitHub Release includes wheel/sdist publishing attestations. They can be inspected from the release page and verified with GitHub attestation tooling or PyPI provenance.

## Links

- [GitHub Release](https://github.com/Jackxiaozhiren/data-science-agent/releases/tag/v4.2.10)
- [PyPI](https://pypi.org/project/jack-data-science-agent/)
- [Changelog](../../CHANGELOG.md)

## Share-ready summary

> Data Science Agent v4.2.10 is available on PyPI — a self-contained, evidence-grounded data-science agent with reproducible reports, claim-level provenance, benchmarks, and Trusted Publishing attestations. https://github.com/Jackxiaozhiren/data-science-agent/releases/tag/v4.2.10

---

The canonical GitHub Release remains the source of truth for artifacts and detailed release notes.
