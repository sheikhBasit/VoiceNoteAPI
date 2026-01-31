import json
import asyncio
import logging
import redis.asyncio as redis
from typing import Dict, List, Any
from fastapi import WebSocket
from app.core.config import ai_config # Assuming REDIS_URL is in config or env

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Manages active WebSocket connections per User ID.
    Integrates with Redis Pub/Sub to support multi-process broadcasts (Celery -> API).
    """
    def __init__(self):
        # user_id -> List[WebSocket]
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.redis_url = __import__('os').getenv("REDIS_URL", "redis://redis:6379/0")
        self.pubsub_task = None

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        
        # Start background listener if first connection
        if not self.pubsub_task:
            self.pubsub_task = asyncio.create_task(self._listen_to_redis())
            
        # Subscribe to user-specific channel in Redis
        # (Managed inside _listen_to_redis via a set of subscribed channels or dynamic pattern)
        # Simplified: We listen to user_updates_* pattern or handle it in the loop.
        # Let's use user_updates_{user_id} channel.
        
        logger.info(f"WebSocket: User {user_id} connected. Active connections: {len(self.active_connections[user_id])}")

    def disconnect(self, user_id: str, websocket: WebSocket):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"WebSocket: User {user_id} disconnected.")

    async def _listen_to_redis(self):
        """Background task to listen for broadcasts from workers using pattern matching."""
        r = redis.from_url(self.redis_url)
        pubsub = r.pubsub()
        # Listen to all user-specific updates
        await pubsub.psubscribe("user_updates_*")
        
        logger.info("WebSocket: Redis Pattern Pub/Sub listener started.")
        try:
            async for message in pubsub.listen():
                if message["type"] == "pmessage":
                    # Extract user_id from channel name: user_updates_{user_id}
                    channel = message["channel"].decode("utf-8")
                    user_id = channel.replace("user_updates_", "")
                    
                    if user_id in self.active_connections:
                        await self.send_personal_message(message["data"], user_id)
        except Exception as e:
            logger.error(f"WebSocket: Redis Pub/Sub error: {e}")
        finally:
            await pubsub.punsubscribe("user_updates_*")

    async def send_personal_message(self, message: str, user_id: str):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.error(f"Failed to send WS message to {user_id}: {e}")

    async def broadcast_status(self, user_id: str, event_type: str, payload: Any):
        """Internal helper for API-local broadcasts."""
        message = json.dumps({
            "user_id": user_id,
            "type": event_type,
            "data": payload,
            "timestamp": int(__import__('time').time() * 1000)
        })
        await self.send_personal_message(message, user_id)

# Global Manager Instance
manager = ConnectionManager()
