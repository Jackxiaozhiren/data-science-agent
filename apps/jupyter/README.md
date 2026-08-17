# Jupyter Integration — V4 W6 (§38–41)

`from data_science_agent import Agent` renders `Analysis` (evidence + artifacts) inline.

```python
from data_science_agent import Agent
agent = Agent()
result = await agent.analyze("sales.csv", "Analyze revenue")
result  # displays evidence + report in notebook
```

`%dsa` magic (stub, §40):

```
%dsa analyze revenue.csv --task "Analyze revenue"
```

Reproducibility: notebook retains `dataset_hash/tool_version/prompt_version/agent_version/experiment_id` (§41).
