"""Background jobs and system initialization for SnapBack."""

from apscheduler.schedulers.background import BackgroundScheduler
from services.storage.database import init_db, purge_old_data

def bootstrap_system(hours: int) -> BackgroundScheduler:
    """Prepare database and clean old records."""
    init_db()
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        purge_old_data,
        "interval",
        hours=max(hours, 1),
        args=[hours],
        id="cleanup-old-sessions",
        replace_existing=True,
    )
    scheduler.start()
    return scheduler
