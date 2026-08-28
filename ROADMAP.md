# Data Science Agent Roadmap

This roadmap communicates project direction so contributors can see **what matters next and where a contribution can have leverage**.

> Roadmap items are directional, not promises or deadlines. Reliability, reproducibility evidence, maintainer capacity, and real user feedback can change priorities.

## Guiding priorities

1. **Evidence before claims** — analytical conclusions should remain traceable to executed computation and data.
2. **Reproducibility before demos** — a result should be rerunnable, not only visually convincing.
3. **Real failures stay visible** — tool failures and benchmark gaps are inputs to improvement, not artifacts to hide.
4. **One runtime, many interfaces** — CLI, SDK, API, Jupyter, MCP, VS Code, and plugins should reuse the same core contracts.
5. **Community work should be verifiable** — benchmark results, datasets, plugins, and case studies need clear acceptance criteria.

## Now

### Reliability & release quality

- Keep CI, CodeQL, dependency review, secret scanning, type checking, tests, docs, and release verification green.
- Preserve PyPI Trusted Publishing and release attestations.
- Treat reproducibility regressions as release-quality issues.

### Contributor onboarding

- [#8 — Verified Windows quickstart](https://github.com/Jackxiaozhiren/data-science-agent/issues/8)
- [#9 — Benchmark-task contribution walkthrough](https://github.com/Jackxiaozhiren/data-science-agent/issues/9)
- [#10 — Hello-world plugin walkthrough](https://github.com/Jackxiaozhiren/data-science-agent/issues/10)
- Maintain structured bug, benchmark-gap, reproducibility, feature, and plugin issue routes.

### Public evaluation surface

- Keep the [benchmark leaderboard](benchmarks/leaderboard/) generated from structured data rather than hand-edited scores.
- Require exact version / commit / benchmark / model metadata for public benchmark submissions.
- Keep the eight [verified case studies](case-studies/) reproducible and explicit about limitations.

## Next

### Benchmark contribution pipeline

- Make it easier to contribute one benchmark task or dataset without learning internal version-spec history.
- Attach raw evaluation artifacts and evidence to leaderboard submissions.
- Add stronger automated checks for benchmark provenance, licensing, and reproducibility.

### Plugin ecosystem

- Publish a minimal plugin tutorial and reference implementation.
- Clarify compatibility, evidence contracts, and plugin validation expectations.
- Grow integrations only when they can reuse the same typed/evidence-aware runtime contracts.

### Cross-platform developer experience

- Verify install / demo / analyze flows across macOS, Linux, Windows, and clean-container environments.
- Reduce setup steps for first-time contributors.
- Keep local-first workflows functional without requiring paid services.

### Community feedback loop

- Enable GitHub Discussions and use the prepared Q&A / Ideas / Show & Tell forms.
- Route recurring questions back into documentation, benchmark tasks, or reproducibility tests.
- Recognize contributors automatically while keeping contribution counts distinct from contribution value.

## Later / under consideration

These are exploration areas rather than committed releases:

- broader externally sourced, clearly licensed case-study datasets;
- cross-model and cross-runtime evaluation with comparable provenance;
- stronger portable reproduction bundles across machines and environments;
- richer benchmark visualization and historical trend reporting;
- expanded plugin and MCP interoperability;
- research packaging that makes raw result → script → artifact provenance easier to audit.

## Non-goals

The project should not optimize for growth metrics by weakening its evidence standard. In particular, the roadmap does **not** prioritize:

- benchmark scores without reproducible artifacts;
- mock or hard-coded success metrics presented as real evaluation;
- hiding failed tool calls from case studies;
- adding integrations that duplicate the core runtime without clear value;
- claims of causal or statistical certainty that exceed the executed evidence.

## How to influence the roadmap

- Pick a [good first issue](https://github.com/Jackxiaozhiren/data-science-agent/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22).
- File a structured [feature request](https://github.com/Jackxiaozhiren/data-science-agent/issues/new/choose).
- Report a benchmark or reproducibility gap with the dedicated issue templates.
- Contribute a validated benchmark result through [`benchmarks/leaderboard/`](benchmarks/leaderboard/).
- Review [`CONTRIBUTORS.md`](CONTRIBUTORS.md) and [`CONTRIBUTING.md`](CONTRIBUTING.md) for contribution paths and recognition.

The best roadmap signal is a reproducible problem, a clear use case, or a well-scoped contribution.
