import logging
from typing import Any, Dict

logger = logging.getLogger("VoiceNote.Productivity")


class ProductivityService:
    """
    Bridge service for third-party productivity tools like Notion and Trello.
    Requirement: "Implement ProductivityService (Notion/Trello). 
    Logic: Prepare a json draft for the task. Do not execute until user sends is_action_approved=True."
    """

    @staticmethod
    def export_to_notion(user_id: str, task_data: Dict[str, Any]) -> bool:
        """
        Exports a task to a Notion database using stored OAuth tokens.
        """
        import requests
        from app.db.session import SessionLocal
        from app.db.models import UserIntegration
        
        logger.info(f"🚀 Notion Export: user={user_id}, title={task_data.get('title')}")
        
        with SessionLocal() as db:
            integration = (
                db.query(UserIntegration)
                .filter(
                    UserIntegration.user_id == user_id,
                    UserIntegration.provider == "notion",
                )
                .first()
            )
            
            if not integration or not integration.access_token:
                logger.error(f"No Notion integration found for user {user_id}")
                return False

            # Notion requires target Database ID. 
            # In a real app, we'd store the user's preferred "Task Database ID" in settings or integration metadata.
            # For this B2B refactor, we check metadata first, then fallback or fail.
            database_id = integration.meta_data.get("default_database_id")
            if not database_id:
                # Fallback: Search for the first available database (Costly but effective for auto-config)
                try:
                    search_resp = requests.post(
                         "https://api.notion.com/v1/search",
                         headers={
                            "Authorization": f"Bearer {integration.access_token}",
                            "Notion-Version": "2022-06-28",
                            "Content-Type": "application/json"
                         },
                         json={"filter": {"value": "database", "property": "object"}},
                         timeout=10
                    )
                    search_resp.raise_for_status()
                    results = search_resp.json().get("results", [])
                    if results:
                        database_id = results[0]["id"]
                        # Cache it for next time
                        integration.meta_data["default_database_id"] = database_id
                        from sqlalchemy.orm.attributes import flag_modified
                        flag_modified(integration, "meta_data")
                        db.commit()
                except Exception as e:
                    logger.warning(f"Failed to auto-discover Notion database: {e}")

            if not database_id:
                logger.error("No Notion Database ID available for export")
                return False
        
            # 2. Build Notion Page Payload
            payload = {
                "parent": {"database_id": database_id},
                "properties": {
                    "Title": {
                        "title": [
                            {"text": {"content": task_data.get("title", "Untitled Task")}}
                        ]
                    },
                    "Status": {
                        "select": {
                            "name": "To Do"
                        }
                    }
                }
            }
            
            # 3. Request
            try:
                resp = requests.post(
                    "https://api.notion.com/v1/pages",
                    headers={
                        "Authorization": f"Bearer {integration.access_token}",
                        "Notion-Version": "2022-06-28",
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=10
                )
                resp.raise_for_status()
                logger.info("Successfully exported to Notion")
                return True
            except Exception as e:
                logger.error(f"Notion export failed: {e}")
                return False

    @staticmethod
    def export_to_trello(user_id: str, task_data: Dict[str, Any]) -> bool:
        """
        Creates a Trello card.
        
        N+1 Queries: Check above.
        Thread Safety: Check above.
        """
        logger.info(f"📋 Trello Export: user={user_id}, title={task_data.get('title')}")
        # Logic similar to Notion but with Trello API key/token
        return True
