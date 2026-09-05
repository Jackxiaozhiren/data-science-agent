from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

# §23 Permissions — deny by default, allowlist
ALLOWED_PERMISSIONS: set[str] = {
    "filesystem.read",
    "filesystem.write",
    "network",
    "process",
    "dataset.read",
    "dataset.write",
    "artifact.write",
    # legacy short forms kept for compat, mapped to granular
    "read",
    "compute",
    "write",
}
# Map legacy to granular for validation reporting
PERMISSION_CANONICAL = {
    "read": "dataset.read",
    "compute": "process",
    "write": "artifact.write",
}

ALLOWED_LICENSES = {"MIT", "Apache-2.0", "BSD-3-Clause", "ISC", "Proprietary"}
ALLOWED_CAPABILITIES = {
    "forecast",
    "backtest",
    "metrics",
    "visualization",
    "evidence",
    "forecasting",
    "time_series",
}

# §45 supply-chain: popular packages for typosquatting detection
POPULAR_PYPI = {
    "numpy",
    "pandas",
    "polars",
    "scikit-learn",
    "sklearn",
    "matplotlib",
    "scipy",
    "requests",
    "urllib3",
    "pyyaml",
    "yaml",
    "pydantic",
    "fastapi",
    "duckdb",
    "pyarrow",
    "openpyxl",
    "langgraph",
    "langchain",
    "dsa-time-series",
    "data-science-agent",
    "jack-data-science-agent",
}
WORKSPACE_PACKAGES = {
    "dsa-agent",
    "dsa-api",
    "dsa-datasets",
    "dsa-evaluation",
    "dsa-evidence",
    "dsa-execution",
    "dsa-llm",
    "dsa-mcp",
    "dsa-ml",
    "dsa-plugins",
    "dsa-reports",
    "dsa-statistics",
    "dsa-tools",
    "dsa-visualization",
    "dsa-jupyter",
    "dsa-vscode",
    "data-science-agent",
    "jack-data-science-agent",
}

CURRENT_DSA_VERSION = "4.3.2"


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
        prev = cur
    return prev[-1]


def _is_typosquat(name: str) -> str | None:
    for popular in POPULAR_PYPI:
        if name == popular:
            return None
        if _levenshtein(name, popular) <= 2 and len(name) >= 4:
            return popular
    return None


def _is_suspicious_entrypoint(ep: str) -> str | None:
    suspicious = [
        "..",
        "/",
        "os.",
        "subprocess",
        "eval",
        "exec(",
        "__import__",
        "open(",
        "socket",
        "requests.",
    ]
    for s in suspicious:
        if s in ep:
            return s
    return None


def _is_dependency_confusion(dep: str) -> str | None:
    # dep may be "package>=1.0" — extract name
    base = re.split(r"[<>=!~\[]", dep, maxsplit=1)[0].strip()
    if base.startswith("dsa-") and base not in WORKSPACE_PACKAGES:
        return f"workspace confusion: {base} not in {WORKSPACE_PACKAGES}"
    # typosquat for deps
    typo = _is_typosquat(base)
    if typo:
        return f"typosquat: {base} ~ {typo}"
    return None


def _semver_ok(v: str) -> bool:
    return bool(re.match(r"^\d+\.\d+\.\d+([-.].+)?$", v))


class PluginManifest(BaseModel):
    """Plugin manifest per §22 (name/version/dsa/license/permissions/dependencies/entrypoint/capabilities)."""

    name: str
    version: str
    type: list[str] = Field(default_factory=list)
    requires: dict[str, str] = Field(default_factory=dict)
    # §22 dsa min/max
    dsa: dict[str, str] | None = None
    license: str = "MIT"
    entrypoint: dict[str, str] = Field(default_factory=dict)
    permissions: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    # §24 supply-chain
    hash: str | None = None
    signature: str | None = None
    description: str | None = None

    @field_validator("name")
    @classmethod
    def _check_name(cls, v: str) -> str:
        if not v or not re.match(r"^[a-z0-9][a-z0-9-_]*$", v):
            raise ValueError("name must be kebab-case [a-z0-9-_]")
        return v

    @field_validator("version")
    @classmethod
    def _check_version(cls, v: str) -> str:
        if not _semver_ok(v):
            raise ValueError("version must be semver x.y.z")
        return v

    @classmethod
    def from_yaml(cls, path: Path | str) -> PluginManifest:
        import yaml

        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PluginManifest:
        return cls.model_validate(data)

    def effective_dsa_requirement(self) -> str | None:
        if self.dsa and ("min_version" in self.dsa or "max_version" in self.dsa):
            parts: list[str] = []
            if self.dsa.get("min_version"):
                parts.append(f">={self.dsa['min_version']}")
            if self.dsa.get("max_version"):
                parts.append(f"<{self.dsa['max_version']}")
            return ",".join(parts) if parts else None
        return self.requires.get("dsa")

    def validate_manifest(self) -> list[str]:
        """Validate per §24 — return list of errors (empty = PASS). Does not raise."""
        errors: list[str] = []
        # name/version already pydantic-validated; check extra
        if not self.entrypoint.get("python"):
            errors.append("entrypoint.python required (§22)")
        elif ":" not in self.entrypoint["python"]:
            errors.append("entrypoint.python must be 'module:attr'")
        if not self.license:
            errors.append("license required (§22)")
        elif self.license not in ALLOWED_LICENSES:
            errors.append(f"license {self.license!r} not in allowed {sorted(ALLOWED_LICENSES)}")
        # permissions — default DENY (§23)
        if not self.permissions:
            errors.append("permissions required — default DENY (§23)")
        else:
            for p in self.permissions:
                if p not in ALLOWED_PERMISSIONS:
                    errors.append(
                        f"permission {p!r} not allowed (§23) — allowed {sorted(ALLOWED_PERMISSIONS)}"
                    )
        # capabilities
        if not self.capabilities and not self.type:
            errors.append("capabilities or type required (§22)")
        else:
            for c in self.capabilities:
                if c not in ALLOWED_CAPABILITIES and c not in self.type:
                    # allow custom but warn
                    pass
        # dsa compatibility
        req = self.effective_dsa_requirement()
        if req and not self._check_dsa_compat(req):
            errors.append(
                f"dsa compatibility failed: requires {req!r} but current is {CURRENT_DSA_VERSION} (§24)"
            )
        # hash format if present
        if self.hash and not re.match(r"^[a-f0-9]{8,64}$", self.hash):
            errors.append("hash must be hex 8..64 chars if present")
        # §45 supply-chain: entrypoint, typosquatting, dependency confusion
        ep = self.entrypoint.get("python", "")
        susp = _is_suspicious_entrypoint(ep)
        if susp:
            errors.append(f"suspicious entrypoint pattern {susp!r} (§45 arbitrary code)")
        typo = _is_typosquat(self.name)
        if typo:
            errors.append(f"typosquat risk: plugin name {self.name!r} ~ popular {typo!r} (§45)")
        for dep in self.dependencies:
            conf = _is_dependency_confusion(dep)
            if conf:
                errors.append(f"dependency {dep!r} flagged: {conf} (§45)")
            # also check dependency typosquat
            base = re.split(r"[<>=!~\[]", dep, maxsplit=1)[0].strip()
            # arbitrary code via dependency name with suspicious chars
            if ".." in dep or "/" in dep or " " in dep:
                errors.append(f"dependency {dep!r} contains suspicious path (§45)")
        return errors

    def _check_dsa_compat(self, req: str) -> bool:
        # simple spec: ">=4.0,<5.0" style
        try:
            from packaging.specifiers import SpecifierSet
            from packaging.version import Version

            return Version(CURRENT_DSA_VERSION) in SpecifierSet(req)
        except Exception:
            # fallback: if contains CURRENT version string
            return CURRENT_DSA_VERSION in req or ">=4.0" in req

    def is_valid(self) -> bool:
        return len(self.validate_manifest()) == 0

    def compute_hash(self, root: Path | None = None) -> str:
        """Compute hash of plugin manifest + entrypoint files for supply-chain (§45)."""
        h = hashlib.sha256()
        h.update(f"{self.name}@{self.version}".encode())
        h.update(self.entrypoint.get("python", "").encode())
        if root and root.exists():
            for p in sorted(root.rglob("*.py")):
                try:
                    h.update(p.read_bytes())
                except Exception:
                    continue
        return h.hexdigest()[:16]
