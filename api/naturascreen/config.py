"""Runtime configuration, loaded from environment variables.

All settings are environment-driven so the same image runs in dev and CI without code
changes. Defaults target the local Docker Compose stack.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="", case_sensitive=False, extra="ignore", populate_by_name=True
    )

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

    # --- Security ---
    # Comma-separated API keys. When empty, the API runs in OPEN mode (local/dev) and write
    # endpoints are unguarded. Set keys in any public deployment to gate writes/compute.
    api_keys: str = Field(default="", alias="NATURASCREEN_API_KEYS")
    # Rate limit for expensive endpoints (slowapi syntax), e.g. "30/minute".
    rate_limit: str = Field(default="120/minute", alias="NATURASCREEN_RATE_LIMIT")
    # slowapi storage backend; defaults to in-process memory. Use the Redis URL in prod.
    rate_limit_storage: str = Field(default="memory://", alias="NATURASCREEN_RATE_LIMIT_STORAGE")

    # --- COCONUT ingestion ---
    coconut_api_base: str = "https://coconut.naturalproducts.net/api"

    # --- Scientific adapter availability (real tooling; absence => `unavailable`) ---
    vina_binary: str = "vina"
    mhcflurry_ready: bool = False
    response_model_ready: bool = False

    # --- Storage ---
    data_dir: str = "/data"

    # Full SQLAlchemy URL override (e.g. sqlite+aiosqlite:///./local.db for a no-service
    # local run). When unset, the Postgres URL is composed from the parts above.
    database_url_override: str | None = Field(default=None, alias="NATURASCREEN_DATABASE_URL")

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def api_key_list(self) -> list[str]:
        return [k.strip() for k in self.api_keys.split(",") if k.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
