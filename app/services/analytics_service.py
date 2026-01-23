import time
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db import models
from collections import Counter
import re

class AnalyticsService:
    @staticmethod
    def get_productivity_pulse(db: Session, user_id: str):
        """
        Calculates the "Productivity Pulse" dashboard metrics.
        """
        # 1. Task Velocity
        total_tasks = db.query(models.Task).join(models.Note).filter(
            models.Note.user_id == user_id,
            models.Task.is_deleted == False
        ).count()
        
        completed_tasks = db.query(models.Task).join(models.Note).filter(
            models.Note.user_id == user_id,
            models.Task.is_deleted == False,
            models.Task.is_done == True
        ).count()
        
        task_velocity = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        # 2. Topic Heatmap (Simple Keyword Extraction from Summaries)
        notes = db.query(models.Note).filter(
            models.Note.user_id == user_id,
            models.Note.is_deleted == False
        ).all()
        
        words = []
        for note in notes:
            # Extract words from title and summary
            content = f"{note.title} {note.summary}".lower()
            # Basic cleanup
            clean_words = re.findall(r'\w{4,}', content) # Words with at least 4 chars
            # Filter out common stop words (manual list for MVP)
            stop_words = {'this', 'that', 'with', 'from', 'about', 'note', 'meeting', 'project'}
            words.extend([w for w in clean_words if w not in stop_words])
            
        topic_counts = Counter(words).most_common(5)
        topic_heatmap = [{"topic": t, "count": c} for t, c in topic_counts]
        
        # 3. Meeting ROI
        # Assumption: Every voice note saves 5 minutes of manual typing/review
        meeting_roi_hours = (len(notes) * 5) / 60
        
        # 4. Recent Activity
        recent_notes_count = db.query(models.Note).filter(
            models.Note.user_id == user_id,
            models.Note.is_deleted == False,
            models.Note.timestamp > (time.time() - 7*24*3600) * 1000 # Last 7 days
        ).count()

        return {
            "task_velocity": round(task_velocity, 1),
            "completed_tasks": completed_tasks,
            "total_tasks": total_tasks,
            "topic_heatmap": topic_heatmap,
            "meeting_roi_hours": round(meeting_roi_hours, 1),
            "recent_notes_count": recent_notes_count,
            "status": "Pulse active"
        }
