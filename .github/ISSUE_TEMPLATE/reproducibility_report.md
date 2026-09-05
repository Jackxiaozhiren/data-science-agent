---
name: Reproducibility failure
about: Report a run that cannot be reproduced or whose evidence changes unexpectedly
labels: bug
---

## Reproduction failure

What failed to reproduce?

- [ ] execution
- [ ] numerical result
- [ ] statistical result
- [ ] evidence graph
- [ ] report semantics
- [ ] generated notebook / script
- [ ] environment / dependency resolution

## Original run

Please provide, when safe to share:

- DSA version / commit:
- command or SDK call:
- dataset hash (`sha256`):
- run / experiment ID:
- relevant `experiment.json` fields:

## Reproduction attempt

Describe the second environment and exact reproduction command.

```text
OS:
Python:
Install method:
DSA version / commit:
```

## Expected vs observed

State the smallest meaningful difference. Include numerical tolerances where applicable.

## Artifacts

Attach or link sanitized artifacts such as `reproduce.sh`, `experiment.json`, `evidence_graph.json`, logs, or report diffs.

> Do not attach private datasets, credentials, or secrets.
