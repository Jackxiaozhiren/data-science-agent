from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Data Science Agent API"
    version: str = "1.8.0"
    debug: bool = False
    database_url: str = "sqlite+aiosqlite:///./data/dsa.db"
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    model_config = {"env_prefix": "DSA_"}


settings = Settings()
