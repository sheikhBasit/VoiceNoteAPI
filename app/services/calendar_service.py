import logging
import time
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class CalendarService:
    @staticmethod
    def get_user_events(user_id: str) -> List[Dict[str, Any]]:
        """
        Stub for fetching user calendar events (Google/Outlook).
        In a real app, this would use OAuth tokens and APIs.
        """
        # For MVP: Return mock events for testing conflict logic
        return [
            {
                "title": "Gym Session",
                "start_time": int(time.time() * 1000) + 3600000,
                "end_time": int(time.time() * 1000) + 7200000,
            },
            {
                "title": "Lunch",
                "start_time": int(time.time() * 1000) + 10800000,
                "end_time": int(time.time() * 1000) + 14400000,
            },
        ]

    @staticmethod
    def detect_conflicts(
        tasks: List[Dict[str, Any]], events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detects conflicts between newly extracted tasks with deadlines and existing calendar events.
        """
        conflicts = []
        for task in tasks:
            deadline = task.get("deadline")
            if not deadline:
                continue

            for event in events:
                # If task deadline falls within event time range
                if event["start_time"] <= deadline <= event["end_time"]:
                    conflicts.append(
                        {
                            "task": task["description"],
                            "task_deadline": deadline,
                            "conflicting_event": event["title"],
                            "event_start": event["start_time"],
                            "event_end": event["end_time"],
                        }
                    )
        return conflicts
