"""Tests for Redis Pub/Sub events."""

import json
from unittest.mock import MagicMock, patch

import redis

from services.shared.events import EventPublisher, EventSubscriber


class TestEventPublisher:
    """Tests for EventPublisher."""

    def test_publish_success(self, mock_redis: MagicMock) -> None:
        publisher = EventPublisher(mock_redis)
        result = publisher.publish(
            "user.created",
            {"user_id": "123"},
            source_service="auth",
        )
        assert result is True
        mock_redis.publish.assert_called_once()
        channel, message = mock_redis.publish.call_args[0]
        assert channel == "user"
        data = json.loads(message)
        assert data["event_type"] == "user.created"
        assert data["payload"]["user_id"] == "123"
        assert data["source_service"] == "auth"
        assert "timestamp" in data

    def test_publish_redis_unavailable(self, mock_redis: MagicMock) -> None:
        mock_redis.publish.side_effect = redis.ConnectionError("Connection refused")
        publisher = EventPublisher(mock_redis)
        result = publisher.publish(
            "user.created",
            {"user_id": "123"},
            source_service="auth",
        )
        assert result is False


class TestEventSubscriber:
    """Tests for EventSubscriber."""

    def test_subscribe_registers_handler(self, mock_redis: MagicMock) -> None:
        mock_redis.pubsub.return_value = MagicMock()
        subscriber = EventSubscriber(mock_redis)
        handler = MagicMock()
        subscriber.subscribe("user.created", handler)
        assert "user.created" in subscriber._handlers
        assert handler in subscriber._handlers["user.created"]

    def test_subscribe_same_channel_multiple_handlers(self, mock_redis: MagicMock) -> None:
        mock_redis.pubsub.return_value = MagicMock()
        subscriber = EventSubscriber(mock_redis)
        handler1 = MagicMock()
        handler2 = MagicMock()
        subscriber.subscribe("user.created", handler1)
        subscriber.subscribe("user.created", handler2)
        assert len(subscriber._handlers["user.created"]) == 2
