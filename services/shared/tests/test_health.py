"""Tests for health check blueprint."""

from unittest.mock import MagicMock, patch

from flask import Flask

from services.shared.health import create_health_blueprint


class TestHealthBlueprint:
    """Tests for /health and /ready endpoints."""

    def test_health_returns_ok(self, app: Flask) -> None:
        bp = create_health_blueprint(MagicMock(), "test-service")
        app.register_blueprint(bp)
        client = app.test_client()
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
        assert data["service"] == "test-service"

    def test_ready_returns_ready_when_db_ok(self, app: Flask) -> None:
        mock_db = MagicMock()
        bp = create_health_blueprint(lambda: mock_db, "test-service")
        app.register_blueprint(bp)
        client = app.test_client()
        resp = client.get("/ready")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ready"

    def test_ready_returns_not_ready_when_db_fails(self, app: Flask) -> None:
        def failing_db() -> None:
            msg = "Connection refused"
            raise ConnectionError(msg)

        bp = create_health_blueprint(failing_db, "test-service")
        app2 = Flask("test2")
        app2.config["TESTING"] = True
        app2.register_blueprint(bp)
        client = app2.test_client()
        resp = client.get("/ready")
        assert resp.status_code == 503
        data = resp.get_json()
        assert data["status"] == "not_ready"
        assert "Connection refused" in data["reason"]
