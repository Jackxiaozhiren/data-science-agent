from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Data Science Agent API"
    version: str = "1.8.0"
    debug: bool = False
    database_url: str = "sqlite+aiosqlite:///./data/dsa.db"

    model_config = {"env_prefix": "DSA_"}


settings = Settings()
