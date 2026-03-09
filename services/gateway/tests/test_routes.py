"""Tests for gateway routes — proxy catch-all and error handling."""

from unittest.mock import MagicMock, patch

import httpx
from flask.testing import FlaskClient


class TestProxyRoutes:
    def test_routes_to_auth_service(self, client: FlaskClient) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"data": {"token": "abc"}, "meta": {}, "errors": []}'
        mock_response.headers = httpx.Headers({"content-type": "application/json"})

        with patch("services.gateway.proxy.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.request.return_value = mock_response
            mock_client_class.return_value = mock_client

            resp = client.post("/api/v1/auth/login",
                               json={"email": "a@b.c", "password": "x"})

        assert resp.status_code == 200
        assert b"token" in resp.data

    def test_routes_to_inventory_service(self, client: FlaskClient) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"data": [], "meta": {"total": 0}, "errors": []}'
        mock_response.headers = httpx.Headers({"content-type": "application/json"})

        with patch("services.gateway.proxy.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.request.return_value = mock_response
            mock_client_class.return_value = mock_client

            resp = client.get("/api/v1/items")

        assert resp.status_code == 200

    def test_unknown_route_returns_404(self, client: FlaskClient) -> None:
        resp = client.get("/api/v1/unknown/path")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["errors"][0]["code"] == "not_found"

    def test_upstream_timeout_returns_504(self, client: FlaskClient) -> None:
        with patch("services.gateway.proxy.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.request.side_effect = httpx.TimeoutException("timeout")
            mock_client_class.return_value = mock_client

            resp = client.get("/api/v1/items")

        assert resp.status_code == 504
        data = resp.get_json()
        assert data["errors"][0]["code"] == "gateway_timeout"

    def test_upstream_unavailable_returns_502(self, client: FlaskClient) -> None:
        with patch("services.gateway.proxy.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.request.side_effect = httpx.ConnectError("refused")
            mock_client_class.return_value = mock_client

            resp = client.get("/api/v1/items")

        assert resp.status_code == 502
        data = resp.get_json()
        assert data["errors"][0]["code"] == "bad_gateway"

    def test_preserves_request_id_through_proxy(self, client: FlaskClient) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{}'
        mock_response.headers = httpx.Headers({})

        with patch("services.gateway.proxy.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.request.return_value = mock_response
            mock_client_class.return_value = mock_client

            resp = client.get("/api/v1/items",
                              headers={"X-Request-ID": "trace-123"})

        assert resp.headers.get("X-Request-ID") == "trace-123"

    def test_options_method_supported(self, client: FlaskClient) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.content = b''
        mock_response.headers = httpx.Headers({})

        with patch("services.gateway.proxy.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.request.return_value = mock_response
            mock_client_class.return_value = mock_client

            resp = client.options("/api/v1/auth/login")

        assert resp.status_code == 204

    def test_put_method_supported(self, client: FlaskClient) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"data": {}, "meta": {}, "errors": []}'
        mock_response.headers = httpx.Headers({"content-type": "application/json"})

        with patch("services.gateway.proxy.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.request.return_value = mock_response
            mock_client_class.return_value = mock_client

            resp = client.put("/api/v1/items/some-id", json={"name": "updated"})

        assert resp.status_code == 200

    def test_delete_method_supported(self, client: FlaskClient) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.content = b''
        mock_response.headers = httpx.Headers({})

        with patch("services.gateway.proxy.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.request.return_value = mock_response
            mock_client_class.return_value = mock_client

            resp = client.delete("/api/v1/items/some-id")

        assert resp.status_code == 204
