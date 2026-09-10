# Phase D Pre-Implementation — DSAgentBench Feasibility Audit (V4.3 W4, §28-32)

> **Phase:** D (Inspect step)
> **Date:** 2026-08-28 · **Status:** audit complete — verdict below; no adapter built
> **Benchmark:** DSAgentBench — "Can Agents Automate End-to-End Data-Science Workflows in Real Computer Environments" ([arXiv:2608.10366](https://arxiv.org/abs/2608.10366), EMNLP Main; [OpenReview](https://openreview.net/forum?id=4fvgw3dquM))
> **Artifacts:** [GitHub vis-nlp/DSAgentBench](https://github.com/vis-nlp/DSAgentBench) (Apache-2.0) · paper CC BY 4.0

---

## 1. §29 Feasibility Matrix

| Dimension | Finding | Classification |
|-----------|---------|----------------|
| Benchmark identity | Real, peer-reviewed (EMNLP Main), evaluated on 15 closed/open models | ✅ verified |
| License | Code **Apache-2.0** (LICENSE at repo root); paper **CC BY 4.0** | ✅ integration/usage permitted |
| Task release | **Repo contains ONLY `LICENSE` + a title-only `README.md`** (1 commit, no releases, no packages). The 275 tasks, datasets, and evaluation harness are **not publicly available** | 🔴 **blocker** |
| Environment | Tasks require grounding in "notebooks, IDEs, terminals, browsers, and databases within real operating environments" (§30 boundary) | 🔴 DSA has **no computer-control surface** (no GUI/OS/IDE interaction) — §30 forbids replacing this with simplified internal API calls |
| Evaluator | Deterministic per-task evaluators checking analytical correctness, visual outputs, and model performance | ✅ original-evaluator integration (§16) is viable in principle |
| Scope | 275 tasks across wrangling/exploration/modeling/visualization/validation; long-horizon, intermediate-output-dependent | ⚠️ cost/runtime significant even once available |

## 2. Overall verdict (§29 vocabulary)

```text
NOT CURRENTLY SUPPORTED
```

Two independent blockers, either sufficient on its own:

1. **Benchmark artifacts unreleased** — there is nothing to integrate: no tasks, no datasets, no harness in the public repository. Integration today would be fabrication (§29: do not fake; §108: never fabricate benchmark results).
2. **Environment mismatch** — the benchmark's defining feature is operation inside real computer environments (notebooks/IDEs/terminals/browsers/OS). DSA's runtime exposes file/SQL/python-sandbox tools, not OS-level computer control. Per §30, substituting simplified internal API calls is not allowed; adding a computer-control layer would be a **major architecture change requiring an ADR** (§7) and is out of Phase D's audit scope.

**Disambiguation:** the in-repo `benchmarks/ds-agent-benchmark/` (v0.1.0, 5-task smoke catalog) is an **internal** DSA artifact and is unrelated to the external DSAgentBench benchmark audited here — the names collide; do not conflate them in reports.

## 3. Re-evaluation triggers (when to revisit)

1. **Upstream release:** `vis-nlp/DSAgentBench` publishes tasks + harness → re-run this audit against the released artifacts (pinned commit, license unchanged check).
2. **Architecture decision:** if released and the project wants real-computer credibility, an **ADR** must first decide whether DSA gains a computer-control layer (e.g., containerized agent OS). That is a V4.3-scope conversation per §7, not an adapter detail.
3. **Fallback candidates already covered elsewhere:** file/terminal-shaped data-science benchmarks without OS grounding (e.g., DSBench-style) can be audited as additional W4/W5 externals if DSAgentBench remains unreleased — each gets its own §29 audit.

## 4. Honest summary (§54 style)

> **DSAgentBench integration: NOT CONDUCTED — NOT CURRENTLY SUPPORTED.** The benchmark is real and well-licensed, but its artifacts are unreleased and its environment exceeds DSA's current surface. No adapter was built and no scores exist. Nothing about DSA's capability is claimed from this benchmark.
