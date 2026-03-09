"""Tests for gateway proxy module."""

import uuid
from unittest.mock import MagicMock, patch

import httpx
import pytest
from flask import Flask

from services.gateway.proxy import (
    ROUTE_MAP,
    init_service_urls,
    proxy_request,
    resolve_service,
)


class TestResolveService:
    def test_auth_routes(self) -> None:
        assert resolve_service("/api/v1/auth/login") == "auth"
        assert resolve_service("/api/v1/auth/register") == "auth"
        assert resolve_service("/api/v1/auth/refresh") == "auth"

    def test_account_routes(self) -> None:
        assert resolve_service("/api/v1/account") == "auth"
        assert resolve_service("/api/v1/account/members") == "auth"

    def test_users_routes(self) -> None:
        assert resolve_service("/api/v1/users/me") == "auth"

    def test_items_routes(self) -> None:
        assert resolve_service("/api/v1/items") == "inventory"
        assert resolve_service(f"/api/v1/items/{uuid.uuid4()}") == "inventory"
        assert resolve_service("/api/v1/items/deleted") == "inventory"

    def test_categories_routes(self) -> None:
        assert resolve_service("/api/v1/categories") == "inventory"
        assert resolve_service(f"/api/v1/categories/{uuid.uuid4()}") == "inventory"

    def test_csv_routes(self) -> None:
        assert resolve_service("/api/v1/csv/upload") == "inventory"
        assert resolve_service(f"/api/v1/csv/{uuid.uuid4()}/map") == "inventory"

    def test_shows_routes(self) -> None:
        assert resolve_service("/api/v1/shows") == "sales"
        assert resolve_service(f"/api/v1/shows/{uuid.uuid4()}") == "sales"

    def test_orders_routes(self) -> None:
        assert resolve_service("/api/v1/orders") == "sales"
        assert resolve_service(f"/api/v1/orders/{uuid.uuid4()}") == "sales"

    def test_analytics_routes(self) -> None:
        assert resolve_service("/api/v1/analytics/summary") == "analytics"
        assert resolve_service("/api/v1/analytics/trends") == "analytics"

    def test_shipments_routes(self) -> None:
        assert resolve_service("/api/v1/shipments") == "shipping"
        assert resolve_service(f"/api/v1/shipments/{uuid.uuid4()}") == "shipping"
        assert resolve_service("/api/v1/shipments/bulk") == "shipping"
        assert resolve_service("/api/v1/shipments/overdue") == "shipping"

    def test_packing_lists_routes(self) -> None:
        assert resolve_service(f"/api/v1/packing-lists/{uuid.uuid4()}") == "shipping"

    def test_unknown_route(self) -> None:
        assert resolve_service("/api/v1/unknown") is None
        assert resolve_service("/api/v1/billing") is None

    def test_missing_version(self) -> None:
        assert resolve_service("/items") is None
        assert resolve_service("/auth/login") is None


class TestInitServiceUrls:
    def test_default_urls(self) -> None:
        urls = init_service_urls()
        assert "auth" in urls
        assert "inventory" in urls
        assert "sales" in urls
        assert "analytics" in urls
        assert "shipping" in urls
        assert "localhost:5001" in urls["auth"]
        assert "localhost:5002" in urls["inventory"]
        assert "localhost:5003" in urls["sales"]
        assert "localhost:5004" in urls["analytics"]
        assert "localhost:5005" in urls["shipping"]

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AUTH_SERVICE_URL", "http://auth:8001")
        monkeypatch.setenv("INVENTORY_SERVICE_URL", "http://inventory:8002")
        urls = init_service_urls()
        assert urls["auth"] == "http://auth:8001"
        assert urls["inventory"] == "http://inventory:8002"
        # Restore defaults
        init_service_urls()


class TestProxyRequest:
    def test_success(self, app: Flask) -> None:
        from services.gateway.proxy import SERVICE_URLS
        SERVICE_URLS["auth"] = "http://localhost:5001"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"data": {"token": "abc"}, "meta": {}, "errors": []}'
        mock_response.headers = httpx.Headers({"content-type": "application/json"})

        with app.test_request_context("/api/v1/auth/login", method="POST",
                                       data=b'{"email":"a@b.c","password":"x"}',
                                       headers={"Authorization": "Bearer tok123"}):
            with patch("services.gateway.proxy.httpx.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client.__enter__ = MagicMock(return_value=mock_client)
                mock_client.__exit__ = MagicMock(return_value=False)
                mock_client.request.return_value = mock_response
                mock_client_class.return_value = mock_client

                response, status = proxy_request("auth")

        assert status == 200
        assert b"token" in response.get_data()

    def test_timeout(self, app: Flask) -> None:
        from services.gateway.proxy import SERVICE_URLS
        SERVICE_URLS["auth"] = "http://localhost:5001"

        with app.test_request_context("/api/v1/auth/login", method="POST"):
            with patch("services.gateway.proxy.httpx.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client.__enter__ = MagicMock(return_value=mock_client)
                mock_client.__exit__ = MagicMock(return_value=False)
                mock_client.request.side_effect = httpx.TimeoutException("timeout")
                mock_client_class.return_value = mock_client

                response, status = proxy_request("auth")

        assert status == 504
        assert b"gateway_timeout" in response.get_data()

    def test_connect_error(self, app: Flask) -> None:
        from services.gateway.proxy import SERVICE_URLS
        SERVICE_URLS["auth"] = "http://localhost:5001"

        with app.test_request_context("/api/v1/auth/login", method="POST"):
            with patch("services.gateway.proxy.httpx.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client.__enter__ = MagicMock(return_value=mock_client)
                mock_client.__exit__ = MagicMock(return_value=False)
                mock_client.request.side_effect = httpx.ConnectError("refused")
                mock_client_class.return_value = mock_client

                response, status = proxy_request("auth")

        assert status == 502
        assert b"bad_gateway" in response.get_data()

    def test_unknown_service(self, app: Flask) -> None:
        with app.test_request_context("/api/v1/unknown"):
            response, status = proxy_request("nonexistent")
        assert status == 500

    def test_preserves_query_string(self, app: Flask) -> None:
        from services.gateway.proxy import SERVICE_URLS
        SERVICE_URLS["inventory"] = "http://localhost:5002"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"data": []}'
        mock_response.headers = httpx.Headers({"content-type": "application/json"})

        with app.test_request_context("/api/v1/items?search=widget&limit=10"):
            with patch("services.gateway.proxy.httpx.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client.__enter__ = MagicMock(return_value=mock_client)
                mock_client.__exit__ = MagicMock(return_value=False)
                mock_client.request.return_value = mock_response
                mock_client_class.return_value = mock_client

                proxy_request("inventory")

                call_args = mock_client.request.call_args
                url = call_args[1]["url"]
                assert "search=widget" in url
                assert "limit=10" in url

    def test_forwards_headers(self, app: Flask) -> None:
        from services.gateway.proxy import SERVICE_URLS
        SERVICE_URLS["auth"] = "http://localhost:5001"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{}'
        mock_response.headers = httpx.Headers({})

        with app.test_request_context("/api/v1/auth/login", headers={
            "Authorization": "Bearer mytoken",
            "X-Request-ID": "req-123",
        }):
            with patch("services.gateway.proxy.httpx.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client.__enter__ = MagicMock(return_value=mock_client)
                mock_client.__exit__ = MagicMock(return_value=False)
                mock_client.request.return_value = mock_response
                mock_client_class.return_value = mock_client

                proxy_request("auth")

                call_args = mock_client.request.call_args
                forwarded_headers = call_args[1]["headers"]
                # Normalize keys for case-insensitive lookup
                lower_headers = {k.lower(): v for k, v in forwarded_headers.items()}
                assert lower_headers["authorization"] == "Bearer mytoken"
                assert lower_headers["x-request-id"] == "req-123"
                # Host should be excluded
                assert "host" not in lower_headers
