import os
import sys

from celery import Celery

# Determine if we are in a testing environment (CI or local pytest)
# We check multiple sources to be absolutely sure
is_testing = (
    os.getenv("ENVIRONMENT") == "testing"
    or os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true"
    or os.getenv("GITHUB_ACTIONS") == "true"
    or "pytest" in sys.modules
    or os.path.basename(sys.argv[0]) == "pytest"
)

# Debug print for CI logs (can be removed after CI is green)
if os.getenv("GITHUB_ACTIONS") == "true" or os.getenv("DEBUG_CELERY") == "true":
    print(f"DEBUG: Celery is_testing={is_testing}")
    print(f"DEBUG: sys.modules contains pytest: {'pytest' in sys.modules}")
    print(f"DEBUG: sys.argv[0]: {sys.argv[0]}")

if is_testing:
    broker_url = "memory://"
    result_backend = "cache+memory://"
else:
    broker_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    result_backend = os.getenv("REDIS_URL", "redis://redis:6379/1")

# Celery App Instance
celery_app = Celery("voicenote", broker=broker_url, backend=result_backend)

# Optimization for audio processing
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_always_eager=is_testing,
    task_eager_propagates=True,
    task_track_started=True,
    task_time_limit=600,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    broker_url=broker_url,
    result_backend=result_backend,
    task_queues={
        "short": {"exchange": "short", "routing_key": "short"},
        "long": {"exchange": "long", "routing_key": "long"},
        "celery": {"exchange": "celery", "routing_key": "celery"},
    },
    task_default_queue="celery",
    imports=["app.worker.task"],  # Explicit import
)

# Extra enforcement for testing
if is_testing:
    celery_app.conf.task_always_eager = True
    celery_app.conf.broker_url = "memory://"
    celery_app.conf.result_backend = "cache+memory://"

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
