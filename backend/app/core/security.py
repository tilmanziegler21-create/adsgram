"""Production/runtime guards for settings."""

from app.core.config import settings


def validate_production_settings() -> None:
    """Fail fast on unsafe production configuration."""
    if settings.ENVIRONMENT != "production":
        return

    if settings.ENABLE_ADMIN_API:
        raise RuntimeError("ENABLE_ADMIN_API must be false in production")

    if settings.SMART_SHIELD_MIN_DELAY < 30:
        raise RuntimeError(
            f"SMART_SHIELD_MIN_DELAY={settings.SMART_SHIELD_MIN_DELAY} is unsafe in production "
            "(minimum 30 seconds)"
        )

    if settings.SMART_SHIELD_MAX_DELAY < settings.SMART_SHIELD_MIN_DELAY:
        raise RuntimeError("SMART_SHIELD_MAX_DELAY must be >= SMART_SHIELD_MIN_DELAY")

    if settings.SMART_SHIELD_MAX_DELAY < 60:
        raise RuntimeError(
            f"SMART_SHIELD_MAX_DELAY={settings.SMART_SHIELD_MAX_DELAY} is below recommended "
            "production minimum of 60 seconds"
        )


def is_admin_api_enabled() -> bool:
    """Admin routes are available only in development with explicit flag."""
    return settings.ENVIRONMENT == "development" and settings.ENABLE_ADMIN_API
