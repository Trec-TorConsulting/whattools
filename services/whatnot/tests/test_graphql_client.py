"""Tests for Whatnot GraphQL client."""

import time
from unittest.mock import MagicMock, patch

import pytest

from services.whatnot.graphql.client import RateLimiter, WhatnotApiError, WhatnotClient, WhatnotUserError


class TestRateLimiter:
    def test_acquire_within_limit(self):
        limiter = RateLimiter(max_requests=100, window=1.0)
        for _ in range(10):
            limiter.acquire()  # Should not block

    def test_rate_limiter_initializes(self):
        limiter = RateLimiter(max_requests=10, window=1.0)
        assert limiter._max == 10
        assert limiter._window == 1.0


class TestWhatnotClient:
    def test_client_initialization(self):
        client = WhatnotClient(access_token="test_token")
        assert client._access_token == "test_token"
        assert "api.whatnot.com" in client._base_url

    def test_client_staging_url(self):
        client = WhatnotClient(access_token="test_token", staging=True)
        assert "stage.whatnot.com" in client._base_url

    @patch("services.whatnot.graphql.client.httpx.Client")
    def test_execute_success(self, mock_client_class):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"products": []}}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = WhatnotClient(access_token="test_token")
        result = client.execute("query { products { id } }")

        assert result == {"products": []}

    @patch("services.whatnot.graphql.client.httpx.Client")
    def test_execute_graphql_errors(self, mock_client_class):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": None,
            "errors": [{"message": "Not found"}],
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = WhatnotClient(access_token="test_token")
        with pytest.raises(WhatnotApiError, match="Not found"):
            client.execute("query { product(id: \"abc\") { id } }")

    @patch("services.whatnot.graphql.client.httpx.Client")
    def test_execute_mutation_user_errors(self, mock_client_class):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "productCreate": {
                    "product": None,
                    "userErrors": [{"message": "Invalid title", "field": ["title"]}],
                }
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = WhatnotClient(access_token="test_token")
        with pytest.raises(WhatnotUserError, match="Invalid title"):
            client.execute_mutation(
                "mutation { productCreate(input: {}) { product { id } userErrors { message field } } }",
                mutation_name="productCreate",
            )


class TestWhatnotApiError:
    def test_error_message(self):
        err = WhatnotApiError("Something went wrong")
        assert str(err) == "Something went wrong"


class TestWhatnotUserError:
    def test_user_error_fields(self):
        err = WhatnotUserError("Bad input", field="name", code="INVALID")
        assert "Bad input" in str(err)
        assert err.field == "name"
        assert err.code == "INVALID"


class TestWhatnotClientEdgeCases:
    @patch("services.whatnot.graphql.client.httpx.Client")
    def test_execute_rate_limited_429(self, mock_client_class):
        mock_response = MagicMock()
        mock_response.status_code = 429

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = WhatnotClient(access_token="test_token")
        with pytest.raises(WhatnotApiError, match="Rate limited"):
            client.execute("query { products { id } }")

    @patch("services.whatnot.graphql.client.httpx.Client")
    def test_execute_server_error_500(self, mock_client_class):
        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = WhatnotClient(access_token="test_token")
        with pytest.raises(WhatnotApiError, match="server error"):
            client.execute("query { products { id } }")

    @patch("services.whatnot.graphql.client.httpx.Client")
    def test_execute_no_data(self, mock_client_class):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = WhatnotClient(access_token="test_token")
        with pytest.raises(WhatnotApiError, match="No data"):
            client.execute("query { products { id } }")

    @patch("services.whatnot.graphql.client.httpx.Client")
    def test_execute_transport_error(self, mock_client_class):
        import httpx as real_httpx

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = real_httpx.ConnectError("connection refused")
        mock_client_class.return_value = mock_client

        client = WhatnotClient(access_token="test_token")
        with pytest.raises(WhatnotApiError, match="Transport error"):
            client.execute("query { products { id } }")

    @patch("services.whatnot.graphql.client.httpx.Client")
    def test_execute_mutation_success(self, mock_client_class):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "productUpdate": {
                    "product": {"id": "prod_1", "title": "Updated"},
                    "userErrors": [],
                }
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = WhatnotClient(access_token="test_token")
        result = client.execute_mutation(
            "mutation { productUpdate(input: {}) { product { id title } userErrors { message } } }",
            mutation_name="productUpdate",
        )
        assert result["product"]["id"] == "prod_1"

    @patch("services.whatnot.graphql.client.httpx.Client")
    def test_execute_with_variables(self, mock_client_class):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"product": {"id": "p1"}}}

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = WhatnotClient(access_token="test_token")
        result = client.execute("query ($id: ID!) { product(id: $id) { id } }", variables={"id": "p1"})

        assert result["product"]["id"] == "p1"
        # Verify variables were passed
        call_kwargs = mock_client.post.call_args
        assert "variables" in call_kwargs.kwargs.get("json", {}) or "variables" in str(call_kwargs)
