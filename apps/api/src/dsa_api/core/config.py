import contextlib
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _distribution_version

from pydantic_settings import BaseSettings

#: The distribution the running build belongs to. Named because the workspace installs a second
#: distribution (`dsa-api`, its own `0.1.0`) beside it; reading the wrong one would publish a number
#: that describes nothing the visitor is looking at.
DISTRIBUTION = "jack-data-science-agent"
UNKNOWN_VERSION = "unknown"


def runtime_version() -> str:
    """The version of the installed distribution, or ``unknown`` -- never a remembered constant.

    A field default was the old shape and it drifted: the package moved to the ``4.5.0`` line while
    ``/version`` kept answering ``1.8.0``, which made the public demo unattributable against any release
    note. ``unknown`` is the honest answer when there is no metadata; a stale guess is not.

    ``contextlib.suppress`` rather than a handler because the repository's debt ratchet counts every
    handler in shipped code, and this branch hides nothing: the value simply keeps its default.
    """
    resolved = UNKNOWN_VERSION
    with contextlib.suppress(PackageNotFoundError):
        resolved = _distribution_version(DISTRIBUTION)
    return resolved


class Settings(BaseSettings):
    app_name: str = "Data Science Agent API"
    debug: bool = False
    database_url: str = "sqlite+aiosqlite:///./data/dsa.db"
    cors_origins: str = "http://localhost:3000"
    # Optional regex for dynamic browser origins (e.g. Vercel preview
    # deployments, whose hostnames change per build). Empty = disabled.
    # Safe for the public demo: the API carries no credentials
    # (allow_credentials=False) and every endpoint is reachable by curl
    # regardless, so CORS only governs browser UX, not access control.
    cors_origin_regex: str = ""
    # Abuse protection for expensive endpoints (no auth on the public demo;
    # limits are per-IP sliding windows, 429 + Retry-After on breach).
    rate_limit_enabled: bool = True
    rate_limit_analysis_per_min: int = 60
    rate_limit_upload_per_min: int = 30
    # Opt-in bearer-token auth for self-hosters. Empty (default) = public demo
    # mode with no auth; set DSA_AUTH_TOKEN to require it on all /api/* routes
    # (probes /health, /ready, /version stay public; OPTIONS preflight exempt).
    auth_token: str = ""

    @property
    def version(self) -> str:
        """The running build's version, derived rather than configured.

        Deliberately a property and not a field: as a field it would accept ``DSA_VERSION`` from the
        environment, and a deployment could then publish a number that its own artifact does not have --
        which is the defect this replaces.
        """
        return runtime_version()

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    model_config = {"env_prefix": "DSA_"}


settings = Settings()
