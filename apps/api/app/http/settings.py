"""Core settings, read from the environment (and .env). Module keys live in app/glue/config.py."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "development"  # ENV: "development" enables /docs, /redoc and /openapi.json
    port: int = 8000  # PORT
    cors_origins: str = ""  # CORS_ORIGINS: comma-separated origins; empty = no CORS headers
    log_level: str = "INFO"  # LOG_LEVEL

    @property
    def is_development(self) -> bool:
        return self.env.lower() == "development"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
