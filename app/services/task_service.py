import time
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.db import models


class TaskService:
    def __init__(self, db: Session):
        self.db = db

    def create_task_with_deduplication(self, user_id: str, title: str, description: str, note_id: str = None, deadline: int = None, priority: models.Priority = models.Priority.MEDIUM) -> models.Task:
        """
        GHOST TASK PREVENTION: Ensures we don't create duplicate tasks for the same note and title.
        """
        query = self.db.query(models.Task).filter(
            models.Task.user_id == user_id,
            models.Task.title == title,
            models.Task.is_deleted == False
        )
        if note_id:
            query = query.filter(models.Task.note_id == note_id)
            
        existing = query.first()
        if existing:
            return existing

        import uuid
        new_task = models.Task(
            id=str(uuid.uuid4()),
            user_id=user_id,
            note_id=note_id,
            title=title,
            description=description,
            deadline=deadline,
            priority=priority
        )
        self.db.add(new_task)
        self.db.commit()
        self.db.refresh(new_task)
        return new_task

    def get_task_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        Calculate and return task statistics for a specific user.
        Modularized from the API layer for reusability.
        """
        all_tasks = (
            self.db.query(models.Task)
            .filter(models.Task.user_id == user_id, models.Task.is_deleted == False)
            .all()
        )

        current_time = int(time.time() * 1000)
        total_tasks = len(all_tasks)
        completed_tasks = len([t for t in all_tasks if t.is_done])
        pending_tasks = total_tasks - completed_tasks

        high_priority = len(
            [t for t in all_tasks if t.priority == models.Priority.HIGH]
        )
        medium_priority = len(
            [t for t in all_tasks if t.priority == models.Priority.MEDIUM]
        )
        low_priority = len([t for t in all_tasks if t.priority == models.Priority.LOW])

        overdue_tasks = len(
            [
                t
                for t in all_tasks
                if not t.is_done and t.deadline and t.deadline < current_time
            ]
        )

        # Today calculation is now handled more precisely via timezone in the API,
        # but for stats we use a generic 24h window or pass parameters.
        # Keeping consistent with the existing generic logic for now.
        today_start = (current_time // (24 * 60 * 60 * 1000)) * (24 * 60 * 60 * 1000)
        today_end = today_start + (24 * 60 * 60 * 1000)
        due_today = len(
            [
                t
                for t in all_tasks
                if not t.is_done
                and t.deadline
                and today_start <= t.deadline < today_end
            ]
        )

        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "by_priority": {
                "high": high_priority,
                "medium": medium_priority,
                "low": low_priority,
            },
            "by_status": {"overdue": overdue_tasks, "due_today": due_today},
            "completion_rate": round(
                (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 2
            ),
        }
