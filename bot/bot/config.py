"""Bot configuration."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    TELEGRAM_BOT_TOKEN: str = ""
    BACKEND_URL: str = "http://backend:8000"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
