#!/usr/bin/env python3
"""Generate benchmark v2: extend v1 (20 CSVs / 50 tasks) to 30 datasets / 100+ tasks.

V2 spec §14–18: 10 categories (Data Profiling, EDA, Statistical Testing, Regression,
Classification, Clustering, Time Series, Data Quality, Visualization, Evidence Validation)
with difficulty {easy, medium, hard, expert} + gold standard per task.

We keep the 20 v1 datasets verbatim (determinism), add 10 new synthetic CSVs,
and emit benchmarks/v2/catalog.json mirroring v1 schema plus:
  - difficulty
  - gold_method / required_tools / gold_metrics / required_evidence / forbidden_claims per V2 §17
  - 6-level lens is via evaluation_framework level_scores
"""
from __future__ import annotations

import csv
import json
import math
import random
from pathlib import Path

R = random.Random(42)  # student wants seed 42 deterministic per V2 §98

V1_ROOT = Path(__file__).resolve().parents[1] / "benchmarks" / "ds-agent-benchmark" / "datasets"
V2_ROOT = Path(__file__).resolve().parents[1] / "benchmarks" / "v2"
V2_DATASETS = V2_ROOT / "datasets"
V2_DATASETS.mkdir(parents=True, exist_ok=True)

def write_csv(path: Path, header: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

# Mirror v1 datasets into v2 for self-contained runs (copy, not regenerate to avoid drift)
if V1_ROOT.exists():
    for p in V1_ROOT.glob("*.csv"):
        data = p.read_bytes()
        (V2_DATASETS / p.name).write_bytes(data)

# 10 new datasets (21-30) — deterministic, synthetic, no external data
# 21 clustering.csv — 3 well-separated blobs (k-means friendly)
rows = []
for i in range(450):
    k = R.choice([0, 1, 2])
    cx, cy = [(0, 0), (10, 10), (0, 10)][k]
    rows.append([round(R.gauss(cx, 1.2), 3), round(R.gauss(cy, 1.2), 3), k])
write_csv(V2_DATASETS / "clustering.csv", ["x", "y", "true_label"], rows)

# 22 imbalanced.csv — 90/10 binary (tests stratified CV / F1 / PR-AUC)
rows = []
for i in range(600):
    x1 = R.gauss(0 if i % 10 else 2, 1)
    x2 = R.gauss(0 if i % 10 else 2, 1)
    y = 1 if i % 10 == 0 else 0
    if i < 60 and R.random() < 0.15:
        y = 0
    rows.append([round(x1, 3), round(x2, 3), y])
write_csv(V2_DATASETS / "imbalanced.csv", ["x1", "x2", "label"], rows)

# 23 time_series_long.csv — 600 steps, trend + weekly seasonality (forecast 30d)
rows = []
for t in range(600):
    trend = t * 0.08
    weekly = 12 * math.sin(2 * math.pi * t / 7)
    rows.append([f"2024-01-{(t % 28)+1:02d}", round(100 + trend + weekly + R.gauss(0, 4), 2)])
write_csv(V2_DATASETS / "time_series_long.csv", ["date", "value"], rows)

# 24 mixed_types.csv — numeric + categorical + datetime (profiling stress)
rows = []
for i in range(400):
    rows.append([i, round(R.uniform(0, 100), 2), R.choice(["A", "B", "C"]), f"2024-{(i%12)+1:02d}-{(i%28)+1:02d}", None if R.random() < 0.07 else R.randint(1, 10)])
write_csv(V2_DATASETS / "mixed_types.csv", ["id", "score", "group", "date", "maybe_null"], rows)

# 25 high_cardinality.csv — 800 unique keys out of 1000 rows
rows = []
for i in range(1000):
    rows.append([f"key_{R.randint(0, 799)}", round(R.gauss(50, 10), 1)])
write_csv(V2_DATASETS / "high_cardinality.csv", ["key", "value"], rows)

# 26 leakage.csv — target leakage column for leakage detector
rows = []
for i in range(400):
    y = R.choice([0, 1])
    leaked = y  # pure leakage
    x = R.gauss(y * 2, 1)
    rows.append([round(x, 3), leaked, y])
write_csv(V2_DATASETS / "leakage.csv", ["x", "x_leaked", "target"], rows)

# 27 missing_heavy.csv — 30% missing pattern
rows = []
for i in range(500):
    a = "" if R.random() < 0.3 else R.randint(1, 10)
    b = "" if R.random() < 0.3 else round(R.uniform(0, 1), 3)
    rows.append([a, b, R.choice(["X", "Y"])])
write_csv(V2_DATASETS / "missing_heavy.csv", ["a", "b", "cat"], rows)

# 28 unicode.csv — unicode, emoji-ish and quotes (format edge)
rows = [["id", "text", "value"]]
rows += [[i, R.choice(["café", "naïve", "résumé", "北京", "hello, world", "a\"b", "x\ny"]), R.randint(1, 100)] for i in range(120)]
write_csv(V2_DATASETS / "unicode.csv", ["id", "text", "value"], rows[1:])

# 29 wide_table.csv — 40 numeric cols (projection stress)
header = [f"f{i}" for i in range(40)] + ["target"]
rows = [[round(R.gauss(0, 1), 3) for _ in range(40)] + [R.choice([0, 1])] for _ in range(300)]
write_csv(V2_DATASETS / "wide_table.csv", header, rows)

# 30 causal_toy.csv — x -> y with confounder z (association not causation)
rows = []
for i in range(600):
    z = R.gauss(0, 1)
    x = round(z * 0.7 + R.gauss(0, 1), 3)
    y = round(0.5 * x + 0.8 * z + R.gauss(0, 0.7), 3)
    rows.append([x, y, round(z, 3)])
write_csv(V2_DATASETS / "causal_toy.csv", ["x", "y", "z"], rows)

print(f"Datasets: {len(list(V2_DATASETS.glob('*.csv')))} at {V2_DATASETS}")

# Build catalog: start from v1 50 tasks (preserving ids), add 50 new tasks (51-100)
v1_catalog_path = Path(__file__).resolve().parents[1] / "benchmarks" / "ds-agent-benchmark" / "catalog.json"
v1 = json.loads(v1_catalog_path.read_text(encoding="utf-8"))
v1_tasks = v1["tasks"]

# Annotate v1 tasks with difficulty + gold fields (non-breaking: add optional keys)
CATEGORY_DIFFICULTY = {
    "EDA": "easy",
    "SQL": "easy",
    "Statistics": "medium",
    "Regression": "medium",
    "Classification": "medium",
    "Time Series": "medium",
    "Visualization": "easy",
    "Data Quality": "easy",
}
for t in v1_tasks:
    t.setdefault("difficulty", CATEGORY_DIFFICULTY.get(t["category"], "medium"))
    gt = t.setdefault("ground_truth", {})
    t.setdefault("gold_method", gt.get("expected_tool", ""))
    t.setdefault("required_tools", [gt.get("expected_tool")] if gt.get("expected_tool") else [])
    t.setdefault("gold_metrics", {})
    t.setdefault("required_evidence", [])
    t.setdefault("forbidden_claims", [])

# 50 new tasks across the 10 V2 categories (§15); include Evidence Validation + Data Profiling + Clustering
new_tasks = [
    # Data Profiling (6)
    {"id": "prof-01", "category": "Data Profiling", "dataset": "mixed_types.csv", "question": "Profile mixed_types.csv: infer types, missing, duplicates, potential targets.", "expected_analysis": "Schema + missing + duplicates + dtype inference", "ground_truth": {"expected_tool": "profile_dataset"}, "criteria": {"task_success": True, "evidence_coverage": True}, "difficulty": "easy", "gold_method": "profile_dataset", "required_tools": ["profile_dataset"], "gold_metrics": {}, "required_evidence": ["schema"], "forbidden_claims": []},
    {"id": "prof-02", "category": "Data Profiling", "dataset": "unicode.csv", "question": "Handle unicode/quoted CSV and infer correct dtypes.", "expected_analysis": "Unicode-safe profiling", "ground_truth": {"expected_tool": "profile_dataset"}, "criteria": {"task_success": True}, "difficulty": "easy", "gold_method": "profile_dataset", "required_tools": ["profile_dataset"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    {"id": "prof-03", "category": "Data Profiling", "dataset": "wide_table.csv", "question": "Profile a 40-column table and report cardinality per column.", "expected_analysis": "Wide-table cardinality", "ground_truth": {"expected_tool": "profile_dataset"}, "criteria": {"task_success": True}, "difficulty": "hard", "gold_method": "profile_dataset", "required_tools": ["profile_dataset"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    {"id": "prof-04", "category": "Data Profiling", "dataset": "high_cardinality.csv", "question": "Report high-cardinality key distribution and suggest handling.", "expected_analysis": "High-cardinality assessment", "ground_truth": {"expected_tool": "profile_dataset"}, "criteria": {"task_success": True}, "difficulty": "medium", "gold_method": "profile_dataset", "required_tools": ["profile_dataset"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    {"id": "prof-05", "category": "Data Profiling", "dataset": "time_series_long.csv", "question": "Detect datetime column and propose time index.", "expected_analysis": "Datetime detection", "ground_truth": {"expected_tool": "profile_dataset"}, "criteria": {"task_success": True}, "difficulty": "easy", "gold_method": "profile_dataset", "required_tools": ["profile_dataset"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    {"id": "prof-06", "category": "Data Profiling", "dataset": "leakage.csv", "question": "Detect target leakage by comparing x vs x_leaked correlation with target.", "expected_analysis": "Leakage signal via correlation", "ground_truth": {"expected_tool": "correlation_analysis"}, "criteria": {"task_success": True}, "difficulty": "hard", "gold_method": "correlation_analysis", "required_tools": ["correlation_analysis"], "gold_metrics": {}, "required_evidence": ["correlation"], "forbidden_claims": []},
    # Clustering (6)
    {"id": "clus-01", "category": "Clustering", "dataset": "clustering.csv", "question": "Cluster clustering.csv (k=3) and evaluate silhouette or inertia.", "expected_analysis": "KMeans k=3", "ground_truth": {"expected_tool": "train_model"}, "criteria": {"task_success": True}, "difficulty": "medium", "gold_method": "train_model", "required_tools": ["train_model"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    {"id": "clus-02", "category": "Clustering", "dataset": "clustering.csv", "question": "Compare k=2 vs k=3 and pick best by silhouette.", "expected_analysis": "Model selection for clustering", "ground_truth": {"expected_tool": "evaluate_model"}, "criteria": {"task_success": True}, "difficulty": "hard", "gold_method": "evaluate_model", "required_tools": ["evaluate_model"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    {"id": "clus-03", "category": "Clustering", "dataset": "correlation.csv", "question": "Cluster correlation.csv group column and visualize clusters.", "expected_analysis": "Clustering + viz", "ground_truth": {"expected_tool": "create_chart"}, "criteria": {"task_success": True, "visualization": True}, "difficulty": "medium", "gold_method": "create_chart", "required_tools": ["create_chart"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    {"id": "clus-04", "category": "Clustering", "dataset": "wide_table.csv", "question": "Reduce wide_table.csv (PCA heuristic or feature selection) then cluster.", "expected_analysis": "Dimensionality-aware clustering", "ground_truth": {"expected_tool": "train_model"}, "criteria": {"task_success": True}, "difficulty": "expert", "gold_method": "train_model", "required_tools": ["train_model"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    {"id": "clus-05", "category": "Clustering", "dataset": "high_cardinality.csv", "question": "Cluster high-cardinality keys by value distribution.", "expected_analysis": "Aggregation + cluster", "ground_truth": {"expected_tool": "run_sql"}, "criteria": {"task_success": True, "sql_accuracy": True}, "difficulty": "hard", "gold_method": "run_sql", "required_tools": ["run_sql"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    {"id": "clus-06", "category": "Clustering", "dataset": "imbalanced.csv", "question": "Check whether imbalanced.csv clusters align with label before classification.", "expected_analysis": "Pre-clustering check", "ground_truth": {"expected_tool": "profile_dataset"}, "criteria": {"task_success": True}, "difficulty": "expert", "gold_method": "profile_dataset", "required_tools": ["profile_dataset"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    # Extra EDA / SQL / Stats / Regression / Classification / TS / Viz / DQ to reach 100
    {"id": "eda-09", "category": "EDA", "dataset": "clustering.csv", "question": "Summarize clustering.csv true_label balance and numeric spread.", "expected_analysis": "Label balance + spread", "ground_truth": {"expected_tool": "profile_dataset"}, "criteria": {"task_success": True}, "difficulty": "easy", "gold_method": "profile_dataset", "required_tools": ["profile_dataset"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    {"id": "eda-10", "category": "EDA", "dataset": "imbalanced.csv", "question": "Report class imbalance and propose handling (stratified split / F1 over accuracy).", "expected_analysis": "Imbalance report", "ground_truth": {"expected_tool": "profile_dataset"}, "criteria": {"task_success": True}, "difficulty": "medium", "gold_method": "profile_dataset", "required_tools": ["profile_dataset"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    {"id": "sql-08", "category": "SQL", "dataset": "clustering.csv", "question": "COUNT rows per true_label.", "expected_analysis": "GROUP BY label", "ground_truth": {"expected_tool": "run_sql", "sql_contains": ["GROUP BY", "COUNT"]}, "criteria": {"task_success": True, "sql_accuracy": True}, "difficulty": "easy", "gold_method": "run_sql", "required_tools": ["run_sql"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    {"id": "sql-09", "category": "SQL", "dataset": "wide_table.csv", "question": "AVG of f0 by target.", "expected_analysis": "Conditional avg", "ground_truth": {"expected_tool": "run_sql", "sql_contains": ["AVG", "GROUP BY"]}, "criteria": {"task_success": True, "sql_accuracy": True}, "difficulty": "easy", "gold_method": "run_sql", "required_tools": ["run_sql"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    {"id": "sql-10", "category": "SQL", "dataset": "high_cardinality.csv", "question": "Which key has the highest total value?", "expected_analysis": "Top key by SUM", "ground_truth": {"expected_tool": "run_sql", "sql_contains": ["GROUP BY", "SUM", "ORDER BY", "LIMIT"]}, "criteria": {"task_success": True, "sql_accuracy": True}, "difficulty": "medium", "gold_method": "run_sql", "required_tools": ["run_sql"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    {"id": "stats-09", "category": "Statistics", "dataset": "causal_toy.csv", "question": "Is x associated with y? Test and do not claim causation (report association).", "expected_analysis": "Correlation + do not claim causal", "ground_truth": {"expected_tool": "correlation_analysis"}, "criteria": {"task_success": True, "evidence_coverage": True}, "difficulty": "hard", "gold_method": "correlation_analysis", "required_tools": ["correlation_analysis"], "gold_metrics": {}, "required_evidence": ["correlation"], "forbidden_claims": ["cause", "causes", "caused"]},
    {"id": "stats-10", "category": "Statistics", "dataset": "imbalanced.csv", "question": "Compare x1 distribution between label groups (Welch t-test appropriate?).", "expected_analysis": "Welch or Mann-Whitney", "ground_truth": {"expected_tool": "hypothesis_test"}, "criteria": {"task_success": True, "evidence_coverage": True}, "difficulty": "medium", "gold_method": "hypothesis_test", "required_tools": ["hypothesis_test"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    {"id": "stats-11", "category": "Statistics", "dataset": "wide_table.csv", "question": "Multiple testing awareness: test f0..f4 against target without inflating false positives.", "expected_analysis": "5 tests + note multiplicity", "ground_truth": {"expected_tool": "hypothesis_test"}, "criteria": {"task_success": True}, "difficulty": "expert", "gold_method": "hypothesis_test", "required_tools": ["hypothesis_test"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    {"id": "reg-07", "category": "Regression", "dataset": "leakage.csv", "question": "Regress target on x; do NOT use x_leaked (leakage). Compare with and without leaked feature.", "expected_analysis": "Leakage-aware regression", "ground_truth": {"expected_tool": "regression_analysis"}, "criteria": {"task_success": True, "evidence_coverage": True}, "difficulty": "hard", "gold_method": "regression_analysis", "required_tools": ["regression_analysis"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    {"id": "reg-08", "category": "Regression", "dataset": "imbalanced.csv", "question": "Train logistic regression on imbalanced.csv and report PR-AUC / F1 rather than accuracy alone.", "expected_analysis": "Imbalance-aware eval", "ground_truth": {"expected_tool": "train_model"}, "criteria": {"task_success": True}, "difficulty": "medium", "gold_method": "train_model", "required_tools": ["train_model"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    {"id": "clf-07", "category": "Classification", "dataset": "imbalanced.csv", "question": "Classify imbalanced.csv with stratified CV; report confusion matrix.", "expected_analysis": "Stratified CV classification", "ground_truth": {"expected_tool": "train_model"}, "criteria": {"task_success": True}, "difficulty": "hard", "gold_method": "train_model", "required_tools": ["train_model"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    {"id": "clf-08", "category": "Classification", "dataset": "wide_table.csv", "question": "Classify wide_table.csv handling high dimensionality.", "expected_analysis": "High-dim classification", "ground_truth": {"expected_tool": "train_model"}, "criteria": {"task_success": True}, "difficulty": "expert", "gold_method": "train_model", "required_tools": ["train_model"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    {"id": "ts-06", "category": "Time Series", "dataset": "time_series_long.csv", "question": "Forecast next 30 days of time_series_long.csv (trend + weekly seasonality).", "expected_analysis": "30-day forecast", "ground_truth": {"expected_tool": "forecast"}, "criteria": {"task_success": True}, "difficulty": "hard", "gold_method": "forecast", "required_tools": ["forecast"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    {"id": "ts-07", "category": "Time Series", "dataset": "time_series_long.csv", "question": "Compare naive vs moving average forecast on time_series_long.csv.", "expected_analysis": "Forecast comparison", "ground_truth": {"expected_tool": "forecast"}, "criteria": {"task_success": True}, "difficulty": "medium", "gold_method": "forecast", "required_tools": ["forecast"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    {"id": "viz-06", "category": "Visualization", "dataset": "clustering.csv", "question": "Scatter x vs y colored by true_label.", "expected_analysis": "Scatter with hue", "ground_truth": {"expected_tool": "create_chart", "chart_type": "scatter"}, "criteria": {"task_success": True, "visualization": True}, "difficulty": "easy", "gold_method": "create_chart", "required_tools": ["create_chart"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    {"id": "viz-07", "category": "Visualization", "dataset": "causal_toy.csv", "question": "Scatter y vs x with best-fit line (association, not causation).", "expected_analysis": "Scatter + trend", "ground_truth": {"expected_tool": "create_chart", "chart_type": "scatter"}, "criteria": {"task_success": True, "visualization": True}, "difficulty": "medium", "gold_method": "create_chart", "required_tools": ["create_chart"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": ["cause"]},
    {"id": "dq-06", "category": "Data Quality", "dataset": "missing_heavy.csv", "question": "Quantify missing rate and recommend imputation.", "expected_analysis": "Heavy missing report", "ground_truth": {"expected_tool": "profile_dataset"}, "criteria": {"task_success": True}, "difficulty": "medium", "gold_method": "profile_dataset", "required_tools": ["profile_dataset"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    {"id": "dq-07", "category": "Data Quality", "dataset": "unicode.csv", "question": "Validate unicode CSV parses without error; report any encoding issues.", "expected_analysis": "Unicode robustness", "ground_truth": {"expected_tool": "profile_dataset"}, "criteria": {"task_success": True}, "difficulty": "easy", "gold_method": "profile_dataset", "required_tools": ["profile_dataset"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    # Evidence Validation (10) — the research-critical gap
    {"id": "ev-01", "category": "Evidence Validation", "dataset": "sales.csv", "question": "Claim with evidence: total revenue by region must be grounded in SQL result.", "expected_analysis": "GROUP BY + evidence trace", "ground_truth": {"expected_tool": "run_sql", "sql_contains": ["GROUP BY", "SUM"]}, "criteria": {"task_success": True, "sql_accuracy": True, "evidence_coverage": True}, "difficulty": "easy", "gold_method": "run_sql", "required_tools": ["run_sql"], "gold_metrics": {}, "required_evidence": ["sql", "evidence"], "forbidden_claims": []},
    {"id": "ev-02", "category": "Evidence Validation", "dataset": "correlation.csv", "question": "Every insight about x vs y must cite a correlation result with r and p.", "expected_analysis": "Evidence-grounded correlation", "ground_truth": {"expected_tool": "correlation_analysis"}, "criteria": {"task_success": True, "evidence_coverage": True}, "difficulty": "medium", "gold_method": "correlation_analysis", "required_tools": ["correlation_analysis"], "gold_metrics": {}, "required_evidence": ["correlation"], "forbidden_claims": []},
    {"id": "ev-03", "category": "Evidence Validation", "dataset": "causal_toy.csv", "question": "Do NOT claim x causes y; any causal language without causal evidence must be rewritten as association.", "expected_analysis": "Unsupported claim guard", "ground_truth": {"expected_tool": "correlation_analysis"}, "criteria": {"task_success": True, "evidence_coverage": True}, "difficulty": "hard", "gold_method": "correlation_analysis", "required_tools": ["correlation_analysis"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": ["cause", "causes", "caused", "impact", "effect"]},
    {"id": "ev-04", "category": "Evidence Validation", "dataset": "titanic.csv", "question": "Survival rate by sex: evidence must include SQL rows and evidence graph links.", "expected_analysis": "Evidence trace end-to-end", "ground_truth": {"expected_tool": "run_sql", "sql_contains": ["GROUP BY", "AVG"]}, "criteria": {"task_success": True, "evidence_coverage": True}, "difficulty": "medium", "gold_method": "run_sql", "required_tools": ["run_sql"], "gold_metrics": {}, "required_evidence": ["sql", "evidence"], "forbidden_claims": []},
    {"id": "ev-05", "category": "Evidence Validation", "dataset": "groups.csv", "question": "Group comparison must have evidence: statistic, p_value, effect_size preserved in evidence graph.", "expected_analysis": "Statistical evidence graph", "ground_truth": {"expected_tool": "hypothesis_test"}, "criteria": {"task_success": True, "evidence_coverage": True}, "difficulty": "medium", "gold_method": "hypothesis_test", "required_tools": ["hypothesis_test"], "gold_metrics": {}, "required_evidence": ["statistical_test"], "forbidden_claims": []},
    {"id": "ev-06", "category": "Evidence Validation", "dataset": "leakage.csv", "question": "Insight mentioning x_leaked as feature must be flagged (leakage evidence is required before claim).", "expected_analysis": "Leakage evidence check", "ground_truth": {"expected_tool": "regression_analysis"}, "criteria": {"task_success": True, "evidence_coverage": True}, "difficulty": "expert", "gold_method": "regression_analysis", "required_tools": ["regression_analysis"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    {"id": "ev-07", "category": "Evidence Validation", "dataset": "sales.csv", "question": "Visualization claims must reference artifact id (chart exists and is embedded in report).", "expected_analysis": "Chart evidence", "ground_truth": {"expected_tool": "create_chart", "chart_type": "histogram"}, "criteria": {"task_success": True, "visualization": True, "evidence_coverage": True}, "difficulty": "easy", "gold_method": "create_chart", "required_tools": ["create_chart"], "gold_metrics": {}, "required_evidence": ["visualization"], "forbidden_claims": []},
    {"id": "ev-08", "category": "Evidence Validation", "dataset": "retail_sales.csv", "question": "Reproducibility: report must list dataset hash, code, and seed so a fresh run reproduces the same totals.", "expected_analysis": "Repro bundle present", "ground_truth": {"expected_tool": "run_sql"}, "criteria": {"task_success": True, "evidence_coverage": True}, "difficulty": "hard", "gold_method": "run_sql", "required_tools": ["run_sql"], "gold_metrics": {}, "required_evidence": ["sql"], "forbidden_claims": []},
    {"id": "ev-09", "category": "Evidence Validation", "dataset": "imbalanced.csv", "question": "Accuracy-only reporting when F1 is required is insufficient evidence; F1/ROC-AUC must be present.", "expected_analysis": "Metric evidence check", "ground_truth": {"expected_tool": "train_model"}, "criteria": {"task_success": True}, "difficulty": "hard", "gold_method": "train_model", "required_tools": ["train_model"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    {"id": "ev-10", "category": "Evidence Validation", "dataset": "time_series_long.csv", "question": "Forecast insight must cite MAE on holdout (no unsupported performance claim).", "expected_analysis": "Forecast with MAE evidence", "ground_truth": {"expected_tool": "forecast"}, "criteria": {"task_success": True, "evidence_coverage": True}, "difficulty": "medium", "gold_method": "forecast", "required_tools": ["forecast"], "gold_metrics": {}, "required_evidence": ["model"], "forbidden_claims": []},
    # Fill to 100 (10 more mixed expert)
    {"id": "exp-01", "category": "Regression", "dataset": "causal_toy.csv", "question": "Regress y on x controlling for z (do not claim x causes y after adjusting).", "expected_analysis": "Controlled regression, association only", "ground_truth": {"expected_tool": "regression_analysis"}, "criteria": {"task_success": True, "evidence_coverage": True}, "difficulty": "expert", "gold_method": "regression_analysis", "required_tools": ["regression_analysis"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": ["cause"]},
    {"id": "exp-02", "category": "Statistics", "dataset": "causal_toy.csv", "question": "Test x->y controlling for confounder z (partial correlation).", "expected_analysis": "Partial correlation / adjustment", "ground_truth": {"expected_tool": "correlation_analysis"}, "criteria": {"task_success": True, "evidence_coverage": True}, "difficulty": "expert", "gold_method": "correlation_analysis", "required_tools": ["correlation_analysis"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": ["cause"]},
    {"id": "exp-03", "category": "Clustering", "dataset": "wide_table.csv", "question": "Cluster wide_table.csv after standardizing numeric columns.", "expected_analysis": "Standardize + k-means", "ground_truth": {"expected_tool": "train_model"}, "criteria": {"task_success": True}, "difficulty": "hard", "gold_method": "train_model", "required_tools": ["train_model"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    {"id": "exp-04", "category": "Classification", "dataset": "leakage.csv", "question": "Classify leakage.csv without using x_leaked.", "expected_analysis": "Leakage-aware classification", "ground_truth": {"expected_tool": "train_model"}, "criteria": {"task_success": True, "evidence_coverage": True}, "difficulty": "expert", "gold_method": "train_model", "required_tools": ["train_model"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    {"id": "exp-05", "category": "Data Quality", "dataset": "missing_heavy.csv", "question": "Handle heavy missing (impute vs drop) and compare downstream classification.", "expected_analysis": "Missing handling comparison", "ground_truth": {"expected_tool": "profile_dataset"}, "criteria": {"task_success": True}, "difficulty": "hard", "gold_method": "profile_dataset", "required_tools": ["profile_dataset"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    {"id": "exp-06", "category": "Visualization", "dataset": "wide_table.csv", "question": "Heatmap of correlations among f0..f5 (handle wide schema).", "expected_analysis": "Correlation heatmap", "ground_truth": {"expected_tool": "create_chart", "chart_type": "heatmap"}, "criteria": {"task_success": True, "visualization": True}, "difficulty": "medium", "gold_method": "create_chart", "required_tools": ["create_chart"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    {"id": "exp-07", "category": "Time Series", "dataset": "time_series_long.csv", "question": "Decompose time_series_long.csv seasonality (period 7) and visualize.", "expected_analysis": "Seasonal decomposition + chart", "ground_truth": {"expected_tool": "create_chart", "chart_type": "line"}, "criteria": {"task_success": True, "visualization": True}, "difficulty": "medium", "gold_method": "create_chart", "required_tools": ["create_chart"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    {"id": "exp-08", "category": "Statistics", "dataset": "high_cardinality.csv", "question": "Test whether top key mean differs from others (Welch).", "expected_analysis": "Welch per-key compare", "ground_truth": {"expected_tool": "hypothesis_test"}, "criteria": {"task_success": True, "evidence_coverage": True}, "difficulty": "hard", "gold_method": "hypothesis_test", "required_tools": ["hypothesis_test"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    {"id": "exp-09", "category": "EDA", "dataset": "unicode.csv", "question": "EDA of unicode.csv: missing, text length, outlier value.", "expected_analysis": "Text-aware EDA", "ground_truth": {"expected_tool": "profile_dataset"}, "criteria": {"task_success": True}, "difficulty": "medium", "gold_method": "profile_dataset", "required_tools": ["profile_dataset"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
    {"id": "exp-10", "category": "SQL", "dataset": "unicode.csv", "question": "Average value where text contains 'café' (Unicode predicate).", "expected_analysis": "Unicode WHERE", "ground_truth": {"expected_tool": "run_sql", "sql_contains": ["WHERE", "AVG"]}, "criteria": {"task_success": True, "sql_accuracy": True}, "difficulty": "medium", "gold_method": "run_sql", "required_tools": ["run_sql"], "gold_metrics": {}, "required_evidence": [], "forbidden_claims": []},
]

catalog_v2 = {
    "name": "DS-Agent-Benchmark-v2",
    "version": "0.2.0",
    "datasets": 30,
    "tasks": v1_tasks + new_tasks,
}
V2_ROOT.mkdir(parents=True, exist_ok=True)
(V2_ROOT / "catalog.json").write_text(json.dumps(catalog_v2, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"V2 catalog: {len(catalog_v2['tasks'])} tasks ({len(v1_tasks)} v1 + {len(new_tasks)} new) → {V2_ROOT / 'catalog.json'}")
print(f"Categories: {sorted(set(t['category'] for t in catalog_v2['tasks']))}")

# Quick bench sanity on 5 sample new tasks
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "evaluation" / "src"))
sys.path.insert(0, str(ROOT / "packages" / "agent" / "src"))
sys.path.insert(0, str(ROOT / "packages" / "tools" / "src"))
sys.path.insert(0, str(ROOT / "packages" / "datasets" / "src"))
