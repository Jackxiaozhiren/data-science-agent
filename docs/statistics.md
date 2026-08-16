# Statistics

## Methods
- Correlation: Pearson / Spearman / Kendall (Fisher CI, interpretation).
- Tests: Welch / Student t, Mann-Whitney U, ANOVA / Kruskal-Wallis, Chi-square — with effect size (Cohen d) and assumption notes.
- Regression: OLS / Ridge / Lasso / Elastic Net / Logistic; grouped train/test + metrics.
- Model training (CV): Stratified / KFold + mean R²/accuracy, `evaluate_model` for confusion + ROC/PR downstream.

## Guardrails
- Unsupported causal language rewritten (`causes` → `is associated with`, see `packages/execution/guardrails.py`).
- Prompt-injection markers: dataset content is **untrusted data**, agent instructions are never derived from dataset cells.

All numeric tools return typed outputs and, where applicable, an Evidence stub for `Insight → Evidence → ToolCall`.
