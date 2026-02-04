from celery import Celery
import os
from dotenv import load_dotenv

if not os.path.exists("/.dockerenv") and os.path.exists(".env"):
    load_dotenv()

celery_app = Celery(
    "voicenote",
    broker=os.getenv("REDIS_URL", "redis://redis:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://redis:6379/1")
)

# Optimization for audio processing
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_always_eager=os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true",
    task_eager_propagates=True,  # Important for tests to see errors
    task_track_started=True,
    task_time_limit=600,
    worker_prefetch_multiplier=1,
    task_queues={
        "short": {"exchange": "short", "routing_key": "short"},
        "long": {"exchange": "long", "routing_key": "long"},
        "celery": {"exchange": "celery", "routing_key": "celery"},
    },
    task_default_queue="celery",
    imports=["app.worker.task"] # Explicit import
)

from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    "scan-for-upcoming-deadlines-every-hour": {
        "task": "check_upcoming_tasks",
        "schedule": crontab(minute=0),
    },
    "hard-delete-old-soft-deleted-records": {
        "task": "hard_delete_expired_records",
        "schedule": crontab(hour=3, minute=0),
    },
    "reset-api-key-rate-limits": {
        "task": "reset_api_key_limits",
        "schedule": crontab(hour=0, minute=0),
    },
    "weekly-productivity-report": {
        "task": "generate_productivity_report_task",
        "schedule": crontab(day_of_week=1, hour=9, minute=0),
    },
}