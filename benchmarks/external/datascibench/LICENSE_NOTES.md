# DataSciBench License Notes (V4.3 §23 / §29)

**Audited:** 2026-08-28 · **Upstream pinned commit:** `84ef3d4d94d7362a5149cf14a73dc168fc4f2f33`

## Findings

1. **Upstream code repository (THUDM/DataSciBench): NO LICENSE stated.**
   - No `LICENSE`/`COPYING` file in the repository; the About section names no license.
   - The README requests only a citation of [arXiv:2502.13897](https://arxiv.org/abs/2502.13897).
   - Legal default without a license: all rights reserved by the authors.
2. **Ground truth dataset (HuggingFace `zd21/DataSciBench`): GATED.**
   - Download requires a HuggingFace account and accepting displayed conditions;
     the terms are not visible before acceptance, so they are recorded as
     **unknown** here until a maintainer accepts and restates them.
3. **Paper**: arXiv preprint / ACL 2026 Findings — citation is the required
   attribution for the benchmark itself.

## Consequences for this repository (binding)

- **No redistribution:** no DataSciBench prompt, metric, GT, or code file may be
  committed into the DSA repository. The adapter clones upstream at the pinned
  commit into a git-ignored `.workspace/` at run time.
- **Use in place:** running the benchmark's original evaluator against the
  cloned checkout in our environment for research evaluation is the intended
  academic use and is what V4.3 §22-27 authorizes; results we publish are our
  own measurements, not redistributed benchmark content.
- **Attribution:** any published results must cite the paper (BibTeX in the
  upstream README).
- **Open question (tracked):** a polite upstream issue asking the authors to
  state an explicit license should be filed during Phase C; this file must be
  updated when they answer.
