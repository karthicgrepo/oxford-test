"""Application configuration sourced from environment variables / .env."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="oxford-economics-api")
    app_env: Literal["local", "dev", "staging", "prod"] = Field(default="local")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO")

    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1, le=65535)

    oe_api_base_url: HttpUrl = Field(
        default="https://model.oxfordeconomics.com/api",  # type: ignore[arg-type]
        description="Base URL of the Oxford Economics GMWO API.",
    )
    oe_api_token: SecretStr = Field(
        ...,
        description="Bearer token used to authenticate against the Oxford Economics API.",
    )
    oe_api_timeout_seconds: float = Field(default=60.0, gt=0)
    oe_api_max_retries: int = Field(default=3, ge=0, le=10)

    @property
    def oe_api_base_url_str(self) -> str:
        return str(self.oe_api_base_url).rstrip("/")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance.

    Cached so that env parsing happens once per process; tests can call
    ``get_settings.cache_clear()`` to force a refresh.
    """
    return Settings()  # type: ignore[call-arg]
