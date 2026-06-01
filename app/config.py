"""Application settings loaded from environment / .env."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Pydantic-settings backed config.

    Required env: GOOGLE_API_KEY.
    All other fields have sensible defaults.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    google_api_key: str = Field(..., description="Google AI Studio API key for Gemini")
    log_level: str = Field("INFO", description="Logging level")
    session_ttl_seconds: int = Field(3600, ge=60, description="Session TTL in seconds")
    gemini_text_model: str = Field("gemini-3.5-flash")
    gemini_image_model: str = Field("gemini-3.1-flash-image-preview")
    gemini_max_retries: int = Field(3, ge=0, le=10)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
