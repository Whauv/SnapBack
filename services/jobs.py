"""System bootstrap and background task management."""

from __future__ import annotations

import os
from apscheduler.schedulers.background import BackgroundScheduler
from services.storage.database import SnapBackStorage


def bootstrap_system() -> BackgroundScheduler:
    """Initialize database and schedule retention tasks."""
    store = SnapBackStorage()
    store.init_db()

    scheduler = BackgroundScheduler()
    hours = int(os.getenv("AUTO_DELETE_AFTER_HOURS", "24"))
    scheduler.add_job(
        lambda: store.purge_data(hours), "interval", hours=1, name="data_retention"
    )
    scheduler.start()
    return scheduler
