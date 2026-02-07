import re
import time
from collections import Counter

from sqlalchemy.orm import Session

from app.db import models
from app.utils.json_logger import JLogger


class AnalyticsService:
    @staticmethod
    def get_productivity_pulse(db: Session, user_id: str, force_refresh: bool = False):
        """
        Calculates the "Productivity Pulse" dashboard metrics with caching.
        """
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            return {}

        # Check Cache (usage_stats)
        cache = user.usage_stats or {}
        last_refresh = cache.get("last_analytics_refresh", 0)

        # Ensure last_refresh is an integer for comparison (handles MagicMock or bad data)
        try:
            last_refresh = int(last_refresh)
        except (ValueError, TypeError):
            last_refresh = 0

        # Refresh if stale (> 15 mins) or forced
        if force_refresh or (int(time.time() * 1000) - last_refresh > 15 * 60 * 1000):
            pulse_data = AnalyticsService._calculate_pulse(db, user_id)

            # Update Cache
            cache.update(
                {
                    "last_analytics_refresh": int(time.time() * 1000),
                    "productivity_pulse": pulse_data,
                }
            )
            user.usage_stats = cache

            from sqlalchemy.orm.attributes import flag_modified

            flag_modified(user, "usage_stats")
            db.commit()

            JLogger.info("Refreshed productivity pulse cache", user_id=user_id)
            return pulse_data

        return cache.get("productivity_pulse", {})

    @staticmethod
    def _calculate_pulse(db: Session, user_id: str):
        """Internal heavy calculation logic."""
        # 1. Task Velocity
        total_tasks = (
            db.query(models.Task)
            .filter(models.Task.user_id == user_id, models.Task.is_deleted == False)
            .count()
        )

        completed_tasks = (
            db.query(models.Task)
            .filter(
                models.Task.user_id == user_id,
                models.Task.is_deleted == False,
                models.Task.is_done == True,
            )
            .count()
        )

        task_velocity = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        # 2. Topic Heatmap (Limit notes for performance even in calc)
        notes = (
            db.query(models.Note)
            .filter(models.Note.user_id == user_id, models.Note.is_deleted == False)
            .order_by(models.Note.timestamp.desc())
            .limit(100)
            .all()
        )  # Scan only last 100 notes

        words = []
        for note in notes:
            content = f"{note.title} {note.summary}".lower()
            clean_words = re.findall(r"\w{4,}", content)
            stop_words = {
                "this",
                "that",
                "with",
                "from",
                "about",
                "note",
                "meeting",
                "project",
                "should",
                "would",
                "could",
                "there",
                "their",
                "which",
                "where",
                "when",
                "tasks",
                "notes",
                "summaries",
                "transcript",
                "user",
                "primary",
                "secondary",
            }
            words.extend([w for w in clean_words if w not in stop_words])

        topic_counts = Counter(words).most_common(10)
        topic_heatmap = [{"topic": t, "count": c} for t, c in topic_counts]

        # 3. Dynamic Meeting ROI
        meeting_roi_hours = 0
        for note in notes:
            transcript = (
                note.transcript_groq
                or note.transcript_deepgram
                or note.transcript_android
                or ""
            )
            meeting_roi_hours += len(transcript.split()) / (40 * 60)

        # 4. Recent Activity
        recent_notes_count = (
            db.query(models.Note)
            .filter(
                models.Note.user_id == user_id,
                models.Note.is_deleted == False,
                models.Note.timestamp > (time.time() - 7 * 24 * 3600) * 1000,
            )
            .count()
        )

        return {
            "task_velocity": round(task_velocity, 1),
            "completed_tasks": completed_tasks,
            "total_tasks": total_tasks,
            "topic_heatmap": topic_heatmap,
            "meeting_roi_hours": round(meeting_roi_hours, 1),
            "recent_notes_count": recent_notes_count,
            "status": "Pulse active",
        }
