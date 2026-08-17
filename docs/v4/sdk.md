# SDK — V4 W2 (§15–20)

Stable facade `src/data_science_agent` (§15):

```python
from data_science_agent import Agent, Dataset, Benchmark
agent = Agent()
result = await agent.analyze(Dataset.from_path("sales.csv"), "Analyze revenue decline")
# or sync: agent.analyze_sync("sales.csv", "Analyze revenue")
profile = agent.profile("sales.csv")
bench = Benchmark().run(limit=5)
```

Stability (§18): all exports marked `Stable` in `API_STABILITY` — `Experimental/Internal/Deprecated` to be added as needed. Public API is `data_science_agent.*`; internal `dsa_agent/*` is `Internal`.

Compat tests: `tests/api/compatibility/test_sdk_compat.py` — input/output schema + version + breaking-change gate (§20).
