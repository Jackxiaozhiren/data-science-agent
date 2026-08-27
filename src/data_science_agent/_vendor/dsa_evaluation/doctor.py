from __future__ import annotations

import platform
import shutil
import sys
from typing import Any


def run_doctor() -> dict[str, Any]:
    checks: list[dict[str, str]] = []

    def add(name: str, status: str, message: str = "") -> None:
        checks.append({"name": name, "status": status, "message": message})

    add("Python", "ok" if sys.version_info >= (3, 12) else "warn", sys.version.split()[0])
    add("Platform", "ok", platform.platform())
    # uv
    add("uv", "ok" if shutil.which("uv") else "warn", shutil.which("uv") or "not found")
    # Node
    add("Node", "ok" if shutil.which("node") else "warn", shutil.which("node") or "not found")
    # Docker
    add("Docker", "ok" if shutil.which("docker") else "warn", shutil.which("docker") or "not found")
    # LLM config
    import os

    has_llm = any(
        os.getenv(k)
        for k in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OLLAMA_HOST", "OPENROUTER_API_KEY"]
    )
    add("LLM", "ok" if has_llm else "warn", "no LLM key (stub/Ollama local fallback)")
    # Disk/memory heuristic
    try:
        import shutil as _sh

        du = _sh.disk_usage(".")
        free_gb = du.free / 1e9
        add("Disk", "ok" if free_gb > 1 else "warn", f"{free_gb:.1f}GB free")
    except Exception as e:
        add("Disk", "warn", str(e))

    status = (
        "fail"
        if any(c["status"] == "fail" for c in checks)
        else ("warn" if any(c["status"] == "warn" for c in checks) else "ok")
    )
    # Never fail doctor on missing optional deps
    if status == "fail":
        status = "warn"
    overall = "ok" if status == "ok" else "warn"
    return {"status": overall, "checks": checks}
