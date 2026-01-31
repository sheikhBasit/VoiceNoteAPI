from sqlalchemy.orm import Session, joinedload
from app.db import models
from typing import List, Dict, Any
import time

class TaskService:
    def __init__(self, db: Session):
        self.db = db

    def get_task_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        Calculate and return task statistics for a specific user.
        Modularized from the API layer for reusability.
        """
        all_tasks = self.db.query(models.Task).filter(
            models.Task.user_id == user_id,
            models.Task.is_deleted == False
        ).all()
        
        current_time = int(time.time() * 1000)
        total_tasks = len(all_tasks)
        completed_tasks = len([t for t in all_tasks if t.is_done])
        pending_tasks = total_tasks - completed_tasks
        
        high_priority = len([t for t in all_tasks if t.priority == models.Priority.HIGH])
        medium_priority = len([t for t in all_tasks if t.priority == models.Priority.MEDIUM])
        low_priority = len([t for t in all_tasks if t.priority == models.Priority.LOW])
        
        overdue_tasks = len([
            t for t in all_tasks
            if not t.is_done and t.deadline and t.deadline < current_time
        ])
        
        # Today calculation is now handled more precisely via timezone in the API, 
        # but for stats we use a generic 24h window or pass parameters.
        # Keeping consistent with the existing generic logic for now.
        today_start = (current_time // (24 * 60 * 60 * 1000)) * (24 * 60 * 60 * 1000)
        today_end = today_start + (24 * 60 * 60 * 1000)
        due_today = len([
            t for t in all_tasks
            if not t.is_done and t.deadline and today_start <= t.deadline < today_end
        ])
        
        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "by_priority": {
                "high": high_priority,
                "medium": medium_priority,
                "low": low_priority
            },
            "by_status": {
                "overdue": overdue_tasks,
                "due_today": due_today
            },
            "completion_rate": round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 2)
        }
