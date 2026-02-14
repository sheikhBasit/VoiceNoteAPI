import asyncio
import json
import uuid
import time
import redis.asyncio as redis
from typing import Any, List, AsyncGenerator
from app.core.config import ai_config
from app.utils.json_logger import JLogger

class Broadcaster:
    """
    Service responsible for real-time event distribution across multiple 
    backend worker processes using Redis Pub/Sub.
    """
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(
            redis_url, 
            decode_responses=True,
            socket_timeout=5,
            retry_on_timeout=True
        )

    async def subscribe(self, team_ids: List[str], user_id: str = None) -> AsyncGenerator[str, None]:
        """
        Creates a generator that yields events for the specified team_ids and user_id.
        Includes a heartbeat to keep connections alive through proxies.
        """
        pubsub = self.redis.pubsub()
        channels = [f"team:{tid}" for tid in team_ids]
        if user_id:
            channels.append(f"user:{user_id}")
            
        if not channels:
            return

        try:
            await pubsub.subscribe(*channels)
            JLogger.info("Broadcaster subscription active", channels=channels, user_id=user_id)
            
            while True:
                try:
                    # Wait for a message with a timeout to allow for heartbeats
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=20.0)
                    
                    if message:
                        if message["type"] == "message":
                            yield message["data"]
                    else:
                        # Send heartbeat if no message received within timeout
                        yield json.dumps({"type": "HEARTBEAT", "timestamp": int(time.time() * 1000)})
                        
                except (redis.ConnectionError, redis.TimeoutError):
                    JLogger.warning("Redis connection lost, attempting to reconnect...")
                    await asyncio.sleep(2)
                    await pubsub.subscribe(*channels)
                except Exception as e:
                    JLogger.error("Broadcaster stream error", error=str(e))
                    break
        finally:
            try:
                await pubsub.unsubscribe(*channels)
                await pubsub.close()
            except Exception:
                pass

    async def push_team_event(self, team_id: str, event_type: str, data: Any, trigger_id: str = None):
        """
        Publishes an event to a team's channel with structured metadata.
        """
        message = {
            "type": event_type,
            "data": data,
            "trigger_id": trigger_id or str(uuid.uuid4()),
            "timestamp": int(time.time() * 1000)
        }
        channel = f"team:{team_id}"
        try:
            await self.redis.publish(channel, json.dumps(message))
        except Exception as e:
            JLogger.error("Failed to push team event", team_id=team_id, event=event_type, error=str(e))

    async def push_user_event(self, user_id: str, event_type: str, data: Any, trigger_id: str = None):
        """
        Publishes a private event to a specific user's channel.
        """
        message = {
            "type": event_type,
            "data": data,
            "trigger_id": trigger_id or str(uuid.uuid4()),
            "timestamp": int(time.time() * 1000)
        }
        channel = f"user:{user_id}"
        try:
            await self.redis.publish(channel, json.dumps(message))
        except Exception as e:
            JLogger.error("Failed to push user event", user_id=user_id, event=event_type, error=str(e))

# Global instance initialized with config
broadcaster = Broadcaster(ai_config.REDIS_URL)
