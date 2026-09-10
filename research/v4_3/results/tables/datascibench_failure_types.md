# DataSciBench — step-level failure types (Phase C §27, execution lane)

| Step outcome | Count | Meaning |
|---|---|---|
| Tool executed / returned | 193 | successful tool invocation |
| Tool error | 84 | tool raised during execution on real data |
| `UnsupportedFormatError` (empty-input dir) | 44 | task dir has no data file |

> Counts from the full 45-task run (`research/external/DATASCIBENCH_REPORT.md` §3);
> GT-lane task success/failure classification lands with the original evaluator (Phase F).
