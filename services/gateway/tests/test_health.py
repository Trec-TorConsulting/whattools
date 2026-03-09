"""Tests for gateway health endpoints — liveness and aggregated checks."""

from unittest.mock import patch

import httpx
from flask.testing import FlaskClient


class TestGatewayLiveness:
    def test_liveness_returns_200(self, client: FlaskClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
        assert data["service"] == "gateway"

    def test_liveness_has_request_id(self, client: FlaskClient) -> None:
        resp = client.get("/health")
        assert "X-Request-ID" in resp.headers


class TestAggregatedHealth:
    def test_all_healthy(self, client: FlaskClient) -> None:
        mock_resp = httpx.Response(200, json={"status": "ok"})
        with patch("services.gateway.routes.health_routes.httpx.get", return_value=mock_resp):
            resp = client.get("/api/v1/health")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
        assert data["services"]["gateway"] == "ok"
        assert data["services"]["auth"] == "ok"
        assert data["services"]["inventory"] == "ok"

    def test_one_service_down(self, client: FlaskClient) -> None:
        def mock_get(url: str, **kwargs):  # type: ignore[no-untyped-def]
            if "5001" in url:  # auth
                return httpx.Response(200, json={"status": "ok"})
            # inventory is down
            raise httpx.ConnectError("Connection refused")

        with patch("services.gateway.routes.health_routes.httpx.get", side_effect=mock_get):
            resp = client.get("/api/v1/health")

        assert resp.status_code == 503
        data = resp.get_json()
        assert data["status"] == "degraded"
        assert data["services"]["auth"] == "ok"
        assert data["services"]["inventory"] == "unhealthy"
        assert data["services"]["inventory_detail"] == "Connection refused"

    def test_service_timeout(self, client: FlaskClient) -> None:
        def mock_get(url: str, **kwargs):  # type: ignore[no-untyped-def]
            raise httpx.TimeoutException("Timeout")

        with patch("services.gateway.routes.health_routes.httpx.get", side_effect=mock_get):
            resp = client.get("/api/v1/health")

        assert resp.status_code == 503
        data = resp.get_json()
        assert data["status"] == "degraded"
        assert data["services"]["auth"] == "unhealthy"
        assert data["services"]["auth_detail"] == "Timeout"

    def test_service_unhealthy_status_code(self, client: FlaskClient) -> None:
        mock_resp = httpx.Response(500, json={"status": "error"})
        with patch("services.gateway.routes.health_routes.httpx.get", return_value=mock_resp):
            resp = client.get("/api/v1/health")

        assert resp.status_code == 503
        data = resp.get_json()
        assert data["status"] == "degraded"
        assert data["services"]["auth"] == "unhealthy"
        assert "HTTP 500" in data["services"]["auth_detail"]

    def test_all_services_down(self, client: FlaskClient) -> None:
        with patch("services.gateway.routes.health_routes.httpx.get",
                   side_effect=httpx.ConnectError("refused")):
            resp = client.get("/api/v1/health")

        assert resp.status_code == 503
        data = resp.get_json()
        assert data["status"] == "degraded"
        assert data["services"]["gateway"] == "ok"  # gateway itself is fine
        assert data["services"]["auth"] == "unhealthy"
        assert data["services"]["inventory"] == "unhealthy"
