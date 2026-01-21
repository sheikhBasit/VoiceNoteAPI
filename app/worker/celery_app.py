from celery import Celery
import os
from dotenv import load_dotenv

load_dotenv()

celery_app = Celery(
    "voicenote_worker",
    broker=os.getenv("REDIS_URL", "redis://redis:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://redis:6379/0"),
    include=["app.worker.tasks"] # Points to your task definitions
)

# Optimization for audio processing
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600, # 10-minute limit for long meetings
    worker_prefetch_multiplier=1 # One audio file per worker at a time for CPU efficiency
)

from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    "scan-for-upcoming-deadlines-every-hour": {
        "task": "check_upcoming_tasks",
        "schedule": crontab(minute=0), # Runs at the top of every hour
    },
}