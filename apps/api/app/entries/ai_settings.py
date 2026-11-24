"""Settings of the AI call (REQ-438, WI-066), read from the environment (and .env)."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ANTHROPIC_API_KEY: when empty, the SDK looks for credentials in the environment; with none, AI is unavailable
    anthropic_api_key: SecretStr | None = None
    anthropic_model: str = "claude-haiku-5-5"  # ANTHROPIC_MODEL (product owner, 23 Nov 2026)
    ai_timeout_seconds: float = 20.0  # AI_TIMEOUT_SECONDS
    ai_max_retries: int = 1  # AI_MAX_RETRIES


@lru_cache
def get_ai_settings() -> AiSettings:
    return AiSettings()
