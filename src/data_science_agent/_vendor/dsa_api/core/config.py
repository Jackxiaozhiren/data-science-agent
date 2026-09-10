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

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    model_config = {"env_prefix": "DSA_"}


settings = Settings()
