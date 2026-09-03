"""Production/runtime guards for worker settings."""

from workers.core.config import settings


def validate_production_settings() -> None:
    if settings.ENVIRONMENT != "production":
        return

    if settings.SMART_SHIELD_MIN_DELAY < 30:
        raise RuntimeError(
            f"SMART_SHIELD_MIN_DELAY={settings.SMART_SHIELD_MIN_DELAY} is unsafe in production "
            "(minimum 30 seconds). Remove E2E test overrides from .env."
        )

    if settings.SMART_SHIELD_MAX_DELAY < settings.SMART_SHIELD_MIN_DELAY:
        raise RuntimeError("SMART_SHIELD_MAX_DELAY must be >= SMART_SHIELD_MIN_DELAY")

    if settings.SMART_SHIELD_MAX_DELAY < 60:
        raise RuntimeError(
            f"SMART_SHIELD_MAX_DELAY={settings.SMART_SHIELD_MAX_DELAY} is below recommended "
            "production minimum of 60 seconds"
        )
