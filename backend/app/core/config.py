"""
OpsPulse Backend — Application Settings

Uses pydantic-settings to load configuration from environment variables
(and optionally a .env file). Every secret is loaded from env vars only;
nothing is hardcoded here.

Why pydantic-settings?
- Type-safe configuration with automatic validation.
- Reads from environment variables or .env file without custom parsing code.
- Easy to test by overriding env vars in fixtures.
"""

from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # ignore unknown env vars silently
    )

    # --- Application ---
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    TESTING: bool = False
    LOG_LEVEL: str = "INFO"

    # --- CORS ---
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: object) -> object:
        """Allow comma-separated string from environment."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # --- PostgreSQL ---
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "opspulse"
    POSTGRES_USER: str = "opspulse"
    POSTGRES_PASSWORD: str = "CHANGE_ME"

    @property
    def async_database_url(self) -> str:
        """Async DSN for SQLAlchemy + asyncpg (FastAPI handlers)."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def sync_database_url(self) -> str:
        """Sync DSN for SQLAlchemy + psycopg2 (Celery workers, Alembic)."""
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # --- Redis / Celery ---
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # --- Security ---
    SECRET_KEY: str = "CHANGE_ME_AT_LEAST_32_RANDOM_CHARS"

    # --- JWT ---
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"

    # --- Metric retention ---
    METRIC_RAW_RETENTION_DAYS: int = 7
    METRIC_AGGREGATE_RETENTION_DAYS: int = 30

    # --- Agent heartbeat thresholds ---
    AGENT_DEGRADED_AFTER_SECONDS: int = 60
    AGENT_OFFLINE_AFTER_SECONDS: int = 120


# Single global settings instance used throughout the application.
# Import this in other modules: `from app.core.config import settings`
settings = Settings()
