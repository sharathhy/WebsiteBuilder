"""Application settings. Secrets come only from environment variables (see .env.example)."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: Literal["dev", "test", "prod"] = "dev"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://leadforge:leadforge@localhost:5432/leadforge"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: SecretStr = SecretStr("dev-only-change-me-dev-only-change-me")
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_days: int = 7

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    login_rate_limit: str = "10/minute"

    # When true, every external API (Places, PSI, LLM, Vercel, email) is served from fixtures.
    mock_apis: bool = True

    config_dir: Path = REPO_ROOT / "config"

    sentry_dsn: SecretStr | None = None

    # External API keys. Unused in Phase 1; listed so .env.example stays the single source of truth.
    google_places_api_key: SecretStr | None = None
    google_psi_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None
    vercel_token: SecretStr | None = None
    resend_api_key: SecretStr | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        if isinstance(v, str) and not v.startswith("["):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @field_validator("jwt_secret")
    @classmethod
    def _secret_length(cls, v: SecretStr) -> SecretStr:
        if len(v.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        return v

    def assert_safe_for_prod(self) -> None:
        if self.env == "prod" and self.jwt_secret.get_secret_value().startswith("dev-only"):
            raise RuntimeError("Refusing to start in prod with the default JWT_SECRET")


@lru_cache
def get_settings() -> Settings:
    return Settings()
