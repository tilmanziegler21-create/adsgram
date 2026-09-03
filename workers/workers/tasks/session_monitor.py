"""Periodic session health monitoring Celery task."""

from workers.celery_app import celery_app
from workers.services.session_monitor import run_monitor_all_accounts


@celery_app.task(name="workers.monitor_sessions", bind=True)
def monitor_sessions(self):
    """Probe all pool accounts: session files + FloodWait / deactivated / auth errors."""
    return run_monitor_all_accounts()
