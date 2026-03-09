"""Redis Pub/Sub event publisher and subscriber for inter-service communication."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable

import redis

logger = logging.getLogger(__name__)


class EventPublisher:
    """Publishes events to Redis Pub/Sub channels.

    Events are fire-and-forget: if Redis is unavailable, the primary
    operation continues and a warning is logged.
    """

    def __init__(self, redis_client: redis.Redis) -> None:  # type: ignore[type-arg]
        self.redis = redis_client

    def publish(self, event_type: str, payload: dict[str, Any], *, source_service: str) -> bool:
        """Publish an event to Redis Pub/Sub.

        Args:
            event_type: Event name (e.g., 'user.created', 'inventory.item.updated').
            payload: Event data (must be JSON-serializable).
            source_service: Name of the service publishing the event.

        Returns:
            True if published successfully, False if Redis was unavailable.
        """
        channel = event_type.split(".")[0]
        message = {
            "event_type": event_type,
            "payload": payload,
            "source_service": source_service,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            self.redis.publish(channel, json.dumps(message, default=str))
            return True
        except redis.ConnectionError:
            logger.warning("Redis unavailable, event not published: %s", event_type)
            return False


class EventSubscriber:
    """Subscribes to Redis Pub/Sub channels and dispatches events to handlers."""

    def __init__(self, redis_client: redis.Redis) -> None:  # type: ignore[type-arg]
        self.redis = redis_client
        self.pubsub = self.redis.pubsub()
        self._handlers: dict[str, list[Callable[[dict[str, Any]], None]]] = {}

    def subscribe(self, event_type: str, handler: Callable[[dict[str, Any]], None]) -> None:
        """Register a handler for an event type.

        Args:
            event_type: Event name to listen for (e.g., 'user.created').
            handler: Callable that receives the event payload dict.
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
            channel = event_type.split(".")[0]
            self.pubsub.subscribe(channel)
        self._handlers[event_type].append(handler)

    def listen(self) -> None:
        """Start listening for events and dispatching to handlers.

        This blocks the current thread. Run in a background thread or process.
        """
        for message in self.pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                data = json.loads(message["data"])
                event_type = data.get("event_type", "")
                handlers = self._handlers.get(event_type, [])
                for handler in handlers:
                    handler(data)
            except (json.JSONDecodeError, KeyError):
                logger.warning("Failed to parse event message: %s", message.get("data"))
