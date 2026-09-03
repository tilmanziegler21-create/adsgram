"""Application settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Adsgram"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    ENABLE_ADMIN_API: bool = False
    ENABLE_LEGACY_API: bool = False

    DATABASE_URL: str = "postgresql+asyncpg://teleflow:teleflow@localhost:5432/teleflow"
    DATABASE_URL_SYNC: str = "postgresql://teleflow:teleflow@localhost:5432/teleflow"

    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    FRONTEND_URL: str = ""
    STATIC_DIR: str = ""

    # Telegram engine: Hydrogram (Pyrogram-compatible maintained fork)
    TELEGRAM_ENGINE: str = "hydrogram"
    TELEGRAM_API_ID: int = 0
    TELEGRAM_API_HASH: str = ""
    TELEGRAM_SESSIONS_DIR: str = "/data/sessions"

    SMART_SHIELD_MIN_DELAY: int = 30
    SMART_SHIELD_MAX_DELAY: int = 120

    # LLM: deepseek (default) | openai — через универсальный адаптер
    LLM_PROVIDER: str = "deepseek"
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"

    # CryptoBot billing
    CRYPTOBOT_TOKEN: str = ""

    # Telegram Bot (marketplace: channel connect + ad posting + login widget)
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_BOT_USERNAME: str = ""
    BACKEND_INTERNAL_URL: str = "http://backend:8000"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
