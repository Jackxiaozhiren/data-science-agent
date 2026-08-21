# External Validation — W8 §48-50

> See full `EXTERNAL_DEVELOPER_VALIDATION.md` (§50).

**Fresh Clone (§48):** `git clone --depth 1 file://` (0.6s) → `uv sync --dev` (192 pkgs) → `dsa doctor` (1.3s, warn LLM) → `dsa demo` (1.2s cached) — PASS without `developer-specific path/secret/private dataset/internal service/manual patch` (§5). Fix: `e27ae7f` unignored `packages/reports` + `uv.lock`.

**Developer A 7 Tasks (§49):** `Install` 0.2s, `Run demo` 1.2s, `Use SDK` 1.0s (`Agent.analyze` COMPLETED 4), `Create analysis` 1.1s (`dsa analyze --json`), `Install Plugin` 0.4s (`dsa-time-series`), `Run benchmark` 10.5s (`limit 1` 1.0), `Generate report` 1.0s (`report_markdown`) — **7/7 PASS**.

**Time to First Success:** Clone 0.6s + Install 4s/0s + Setup 1.3s + Demo 1.2s/38s → **2s cached / 44s cold**.

**Friction:** Low (uv, LLM warn, plugin local, pip vs uv, MCP URL, report path).

**Recommendations:** 5 (uv install, LLM warn, pip vs uv, MCP URL, lock) — see `EXTERNAL_DEVELOPER_VALIDATION.md`.
