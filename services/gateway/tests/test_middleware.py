"""Tests for gateway middleware — request ID, logging, rate limiting."""

import uuid
from unittest.mock import patch

from flask import Flask
from flask.testing import FlaskClient


class TestRequestIdMiddleware:
    def test_generates_request_id_when_missing(self, client: FlaskClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        request_id = resp.headers.get("X-Request-ID")
        assert request_id is not None
        # Validate it's a UUID
        uuid.UUID(request_id)

    def test_preserves_existing_request_id(self, client: FlaskClient) -> None:
        custom_id = "my-custom-request-id-123"
        resp = client.get("/health", headers={"X-Request-ID": custom_id})
        assert resp.headers.get("X-Request-ID") == custom_id

    def test_unique_ids_for_different_requests(self, client: FlaskClient) -> None:
        r1 = client.get("/health")
        r2 = client.get("/health")
        assert r1.headers["X-Request-ID"] != r2.headers["X-Request-ID"]


class TestRequestLogging:
    def test_logs_request_info(self, app: Flask, client: FlaskClient) -> None:
        with patch("services.gateway.middleware.logging.logger") as mock_logger:
            resp = client.get("/health")
            assert resp.status_code == 200

            mock_logger.info.assert_called()
            call_kwargs = mock_logger.info.call_args
            # Structlog style: first arg is event name, rest are kwargs
            assert call_kwargs[0][0] == "request_completed"
            assert call_kwargs[1]["method"] == "GET"
            assert call_kwargs[1]["path"] == "/health"
            assert call_kwargs[1]["status"] == 200
            assert "duration_ms" in call_kwargs[1]
            assert "request_id" in call_kwargs[1]

    def test_logs_authenticated_user(self, app: Flask, client: FlaskClient) -> None:
        with patch("services.gateway.middleware.logging.logger") as mock_logger:
            client.get("/health", headers={"Authorization": "Bearer faketoken"})
            call_kwargs = mock_logger.info.call_args
            assert call_kwargs[1]["user_id"] == "authenticated"

    def test_logs_unauthenticated_user(self, app: Flask, client: FlaskClient) -> None:
        with patch("services.gateway.middleware.logging.logger") as mock_logger:
            client.get("/health")
            call_kwargs = mock_logger.info.call_args
            assert call_kwargs[1]["user_id"] is None


class TestRateLimiting:
    def test_rate_limiting_disabled_in_testing(self, app: Flask) -> None:
        """TESTING=True skips rate limit initialization."""
        assert app.config["TESTING"] is True
        # Should not have limiter extension registered
        assert not hasattr(app, "extensions") or "limiter" not in app.extensions

    def test_rate_limiting_enabled_in_production(self) -> None:
        """Non-TESTING apps get rate limiting."""
        from services.gateway.app import create_app

        prod_app = create_app(config_overrides={
            "TESTING": False,
            "SECRET_KEY": "test",
            "REDIS_URL": "memory://",
        })
        assert "limiter" in prod_app.extensions
