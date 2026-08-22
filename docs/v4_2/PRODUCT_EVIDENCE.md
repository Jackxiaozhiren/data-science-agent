# Product Evidence — V4.2 W11 §60 (Real Facts Only)

> **W11 §60 — Product Evidence** — Only real facts (`Installation / Demo / Case Studies / SDK / Plugin / MCP / Jupyter / VS Code / Performance / Reproducibility`) — per §64 no fabricated users/downloads/stars — all numbers from `Benchmark + Commit + Report` (§45)  
> **Date:** 2026-08-22  
> **Commit:** `b79610d` (v4.1.1) → `c6bccb9` (W9) — live  
> **Spec:** `DATA_SCIENCE_AGENT_V4_2.md` §60-64

---

## 1. Installation (§21, W2 §20-22)

| Fact | Evidence | Source |
|------|----------|--------|
| **Install (uv sync)** | `uv sync --dev` → `192 packages` in `2s` (cached) / `4s` (cold) | `reproduction/external/evaluator-A.json` `install_success: true` |
| **Install (pip)** | `pip install jack-data-science-agent==4.1.1` **FAIL** `dsa-agent not found` (14 `dsa-*` 0.1.0 not on PyPI) — honest per `QUANTITATIVE_CLAIMS.md:7` | `QUANTITATIVE_CLAIMS.md:7` clean env `/tmp/dsa-v42-audit` |
| **Import** | `python -c "import data_science_agent"` → `4.1.1` | `dsa verify-release` `12/12` |
| **Extras** | `jupyter` (`dsa-jupyter 0.1.0`) + `time-series` (`statsmodels`) — metadata correct, `pip` fails for `dsa-*` (use `uv sync`) | `pyproject.toml:60-63` |

---

## 2. Demo (§40, W6 §40)

| Fact | Evidence |
|------|----------|
| **dsa demo** | `COMPLETED` 6 evidence, 5 artifacts, `report.md` 3890 chars, `1.33s` (CS01) + `0.05s` (CS02) — `case-studies/01-sales/outputs/` + `artifacts/reports/<runId>/` |
| **External** | `3/3` `Demo Success` (A 30s, B 32s, C 33s) — `reproduction/external/summary.json` |

---

## 3. Case Studies (§28-33, W4)

| Case | Status | Evidence | Report |
|------|--------|----------|--------|
| CS01 Sales | ✅ Verified `COMPLETED` 1.33s | 6 | `case-studies/01-sales/outputs/report.md` 3890 chars |
| CS02 Churn | ✅ Verified `0.05s` | 3 | `2983 chars` |
| CS03-08 | 📝 Planned (dataset+plan ready) | — | `case-studies/*/README.md` |

All `500` rows synthetic `seed 42` `MIT/CC0` + `hash` (see `case-studies/README.md`).

---

## 4. SDK (§41, W6)

| Fact | Evidence |
|------|----------|
| **Stable API** | `Agent`, `Dataset`, `Benchmark`, `Reproduction` + 7 companions — `API_STABILITY` all `Stable` |
| **Test** | `tests/sdk 32` (`18` contract + `13` CLI + `2` compat) → `32 passed` |
| **Example** | `Agent().analyze_sync("sales.csv", "Analyze revenue")` → `COMPLETED` |

---

## 5. Plugin (§42, W6)

| Fact | Evidence |
|------|----------|
| **Flagship** | `dsa-time-series 1.0.0` (`>=4.1,<5`, `>=3.12`, Stable) |
| **Lifecycle** | `Discover→Validate→Load→Execute→Disable→Remove` **7/7 PASS** (`dsa plugin` + `tests/plugins 24`) |
| **Compat** | `docs/v4_2/PLUGIN_COMPATIBILITY.md` `1.0.0 / >=4.1,<5 / Stable` |

---

## 6. MCP (§36-40, W6)

| Fact | Evidence |
|------|----------|
| **Tools** | `18` (`profile_dataset` … `analyze`) — `dsa mcp --json` `len 18` |
| **Resources** | `5` (`dataset://` 50, `evidence://`, `report://`, `artifact://`, `analysis://`) |
| **App** | `/mcp-app/` HTML `Dataset→Question→Analysis→Evidence→Viz→Report` — `6` acceptance |
| **Test** | `tests/mcp 13` (7 conformance + 6 app) |

---

## 7. Jupyter (§28-32, W4)

| Fact | Evidence |
|------|----------|
| **Version** | `dsa-jupyter 0.1.0` (Experimental) |
| **Magic** | `%dsa` / `%%dsa` + `await Agent().analyze()` rich HTML |
| **Test** | `tests/jupyter 10` |

---

## 8. VS Code (§33-35, W4)

| Fact | Evidence |
|------|----------|
| **Version** | `dsa-vscode 0.1.0` (Experimental) |
| **Commands** | `7` (`openDataset`, `askAnalysis`, `runAnalysis`, `viewResult`, `viewEvidence`, `openReport`, `doctor`) |
| **Test** | `tests/vscode 7` |

---

## 9. Performance (§51-55, W9)

| Fact | Evidence |
|------|----------|
| **Latency** | `CS01 1.33s`, `CS02 0.05s`, `benchmark 3` `484ms` mean |
| **Concurrency** | `1/5/10` `P50` `13.6/48.1/90.5ms` `error_rate 0` ( `performance.md` §51) |
| **Large file** | `10MB supported`, `50MB supported`, `100MB degraded`, `500MB/1GB unsupported` (honest, §54) |
| **Overhead** | `Plugin 1.05×`, `SDK 85ms` |

---

## 10. Reproducibility (§31, W4)

| Fact | Evidence |
|------|----------|
| **Bundle** | `artifacts/reports/<runId>/` `report.md` + `experiment.json` + `reproduce.sh` + `analysis.ipynb` + `evidence_graph.json` — per `case-studies/01-sales/outputs/` |
| **Score** | `Reproduction` `L0-L5` + `ReproductionScore` 6-dim (see `reproduction/v2/comparison.json` `overall` ) |
| **Method** | `Agent` `Insight→Evidence→ToolCall→Dataset` hash `05e3...` |

---

## 11. No Fabricated Adoption (§64)

Per §64: 禁止虚构 `users/downloads/stars/contributors/plugins/customers/revenue` — **Current:** `0` `users`/`downloads`/`stars` fabricated, `1` flagship `dsa-time-series`, `0` external contributors (honest `Internal` sim per `COMMUNITY_CONTRIBUTION.md`), all numbers from `pytest 257`/`SBOM 192`/`benchmark 1.00`.

---

*Generated: 2026-08-22 live — `b79610d` — companion to `QUANTITATIVE_CLAIMS.md` + `case-studies/README.md` + `reproduction/external/`.*
