from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Data Science Agent API"
    version: str = "1.8.0"
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
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    model_config = {"env_prefix": "DSA_"}


settings = Settings()
