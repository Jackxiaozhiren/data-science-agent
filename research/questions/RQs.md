# Research Questions — Data Science Agent V2

RQ1 · Does tool augmentation improve statistical correctness? (LLM-only vs LLM+Tools)
RQ2 · Does Critic verification reduce unsupported claims? (without vs with critic)
RQ3 · Does Evidence Graph improve traceability? (evidence coverage / unsupported rate / reproducibility)
RQ4 · Does explicit statistical validation improve reliability? (LLM analysis vs statistics-aware agent)
RQ5 · How does model choice affect reliability? (local / small API / frontier — only when available, never fabricated)

Ablation: A=LLM only, B=LLM+Tools, C=+Planner, D=+Critic, E=+Evidence, F=Full. Compare Task Success / Statistical Accuracy / Evidence Coverage / Unsupported Claims / Reproducibility / Latency / Token Cost (V2 §57).

Significance: bootstrap CI / McNemar / Wilcoxon signed-rank / paired bootstrap; avoid iid assumption over tasks (§58). Store results as JSON/CSV/Parquet under research/results/ with experiment_id/git_commit/dataset_version/prompt_version/model/config/seed/timestamp (§59).

Limitations to log: LLM stochasticity, model dependence, benchmark leakage, dataset bias, evaluation bias, tool selection bias, cost constraints, local model limits (§62).
