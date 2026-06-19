"""Runtime configuration, loaded from environment variables.

All settings are environment-driven so the same image runs in dev and CI without code
changes. Defaults target the local Docker Compose stack.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False, extra="ignore")

    # --- Postgres ---
    postgres_user: str = "naturascreen"
    postgres_password: str = "naturascreen"
    postgres_db: str = "naturascreen"
    postgres_host: str = "db"
    postgres_port: int = 5432

    # --- Redis (Celery broker + live frame pub/sub) ---
    redis_url: str = "redis://redis:6379/0"

    # --- API ---
    cors_origins: str = Field(default="http://localhost:3000", alias="NATURASCREEN_CORS_ORIGINS")
    log_level: str = Field(default="INFO", alias="NATURASCREEN_LOG_LEVEL")

    # --- COCONUT ingestion ---
    coconut_api_base: str = "https://coconut.naturalproducts.net/api"

    # --- Scientific adapter availability (real tooling; absence => `unavailable`) ---
    vina_binary: str = "vina"
    mhcflurry_ready: bool = False
    response_model_ready: bool = False

    # --- Storage ---
    data_dir: str = "/data"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
