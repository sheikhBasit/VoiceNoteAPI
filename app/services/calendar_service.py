import logging
import time
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class CalendarService:
    @staticmethod
    def get_user_events(user_id: str) -> List[Dict[str, Any]]:
        """
        Fetches user calendar events from Google Calendar using stored OAuth tokens.
        """
        from app.db.session import SessionLocal
        from app.db.models import UserIntegration
        import requests
        from datetime import UTC, datetime, timedelta

        events = []
        with SessionLocal() as db:
            integration = (
                db.query(UserIntegration)
                .filter(
                    UserIntegration.user_id == user_id,
                    UserIntegration.provider == "google",
                )
                .first()
            )

            if not integration or not integration.access_token:
                # Return mocks if no integration found (Graceful degradation for MVP)
                logger.warning(f"No Google Calendar integration found for user {user_id}. Using mocks.")
                return [
                    {
                        "title": "Gym Session (Mock)",
                        "start_time": int(time.time() * 1000) + 3600000,
                        "end_time": int(time.time() * 1000) + 7200000,
                    },
                    {
                        "title": "Lunch (Mock)",
                        "start_time": int(time.time() * 1000) + 10800000,
                        "end_time": int(time.time() * 1000) + 14400000,
                    },
                ]

            try:
                # Fetch next 24 hours of events
                now = datetime.now(UTC)
                tomorrow = now + timedelta(days=1)
                
                url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
                params = {
                    "timeMin": now.isoformat() + "Z",
                    "timeMax": tomorrow.isoformat() + "Z",
                    "singleEvents": True,
                    "orderBy": "startTime",
                }
                headers = {"Authorization": f"Bearer {integration.access_token}"}
                
                resp = requests.get(url, headers=headers, params=params, timeout=5)
                if resp.is_successful is False and resp.status_code == 401:
                    logger.warning(f"Google Token Expired for {user_id}. Attempting refresh.")
                    if CalendarService._refresh_google_token(user_id):
                        # Retry once with new token
                        with SessionLocal() as db_retry:
                            integration = db_retry.query(UserIntegration).filter(
                                UserIntegration.user_id == user_id,
                                UserIntegration.provider == "google"
                            ).first()
                            if integration and integration.access_token:
                                headers["Authorization"] = f"Bearer {integration.access_token}"
                                resp = requests.get(url, headers=headers, params=params, timeout=5)

                resp.raise_for_status()
                
                items = resp.json().get("items", [])
                for item in items:
                    # Parse start/end (handle pure dates vs datetimes)
                    start = item.get("start", {}).get("dateTime") or item.get("start", {}).get("date")
                    end = item.get("end", {}).get("dateTime") or item.get("end", {}).get("date")
                    
                    if start and end:
                        # Convert to ms (approximate parsing)
                        # Simplified: assuming ISO format
                        try:
                            # Remove Z if present for fromisoformat (pre-3.11/legacy compat)
                            s_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                            e_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
                            events.append({
                                "title": item.get("summary", "Busy"),
                                "start_time": int(s_dt.timestamp() * 1000),
                                "end_time": int(e_dt.timestamp() * 1000),
                            })
                        except Exception:
                            continue
                            
            except Exception as e:
                logger.error(f"Failed to fetch Google Calendar events: {e}")
                return []
                
        return events

    @staticmethod
    def _refresh_google_token(user_id: str) -> bool:
        """
        Uses the stored refresh token to get a new access token from Google.
        """
        from app.db.session import SessionLocal
        from app.db.models import UserIntegration
        from app.core.config import ai_config
        import requests
        import time

        with SessionLocal() as db:
            integration = (
                db.query(UserIntegration)
                .filter(
                    UserIntegration.user_id == user_id,
                    UserIntegration.provider == "google",
                )
                .first()
            )

            if not integration or not integration.refresh_token:
                logger.error(f"No refresh token available for user {user_id}")
                return False

            try:
                payload = {
                    "client_id": ai_config.GOOGLE_CLIENT_ID,
                    "client_secret": ai_config.GOOGLE_CLIENT_SECRET,
                    "refresh_token": integration.refresh_token,
                    "grant_type": "refresh_token",
                }
                
                resp = requests.post("https://oauth2.googleapis.com/token", data=payload, timeout=10)
                resp.raise_for_status()
                
                data = resp.json()
                integration.access_token = data["access_token"]
                if "expires_in" in data:
                    integration.expires_at = int(time.time() * 1000) + (data["expires_in"] * 1000)
                
                db.commit()
                logger.info(f"Successfully refreshed Google token for user {user_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to refresh Google token: {e}")
                return False

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

    @staticmethod
    def create_event(user_id: str, event_data: Dict[str, Any]) -> bool:
        """
        Creates an event in the user's primary Google Calendar using stored tokens.
        """
        from app.db.session import SessionLocal
        from app.db.models import UserIntegration
        import requests
        
        logger.info(f"📅 Calendar Sync: user={user_id}, event={event_data.get('title')}")
        
        def _execute_create(token):
            # 2. Construct Google Calendar Payload
            start_time = None
            end_time = None
            
            if event_data.get("deadline"):
                 ts = event_data["deadline"] / 1000 
                 from datetime import datetime, timedelta
                 start_dt = datetime.fromtimestamp(ts)
                 end_dt = start_dt + timedelta(hours=1)
                 
                 start_time = start_dt.isoformat() + "Z"
                 end_time = end_dt.isoformat() + "Z"
            
            if not start_time:
                 return None

            payload = {
                "summary": event_data.get("title", "New Task"),
                "description": event_data.get("description", ""),
                "start": {"dateTime": start_time},
                "end": {"dateTime": end_time},
            }

            return requests.post(
                "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=10
            )

        with SessionLocal() as db:
            integration = (
                db.query(UserIntegration)
                .filter(
                    UserIntegration.user_id == user_id,
                    UserIntegration.provider == "google",
                )
                .first()
            )
            
            if not integration or not integration.access_token:
                logger.error(f"No Google Calendar integration found for user {user_id}")
                return False

            response = _execute_create(integration.access_token)
            if response and response.status_code == 401:
                logger.warning("Google Access Token Expired. Refreshing.")
                if CalendarService._refresh_google_token(user_id):
                    # Refresh successful, get new token
                    db.refresh(integration)
                    response = _execute_create(integration.access_token)

            if response and response.status_code < 400:
                logger.info("Successfully created Google Calendar event")
                return True
            else:
                logger.error(f"Failed to create calendar event. Status: {response.status_code if response else 'N/A'}")
                return False
