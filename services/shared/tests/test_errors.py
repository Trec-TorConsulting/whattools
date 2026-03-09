"""Tests for the error handling and response envelope."""

import uuid

import pytest
from flask import Flask

from services.shared.errors import (
    ApiResponse,
    ErrorDetail,
    _http_status_to_code,
    error_response,
    register_error_handlers,
    success_response,
)


class TestErrorDetail:
    """Tests for ErrorDetail dataclass."""

    def test_error_detail_with_field(self) -> None:
        err = ErrorDetail(code="validation_error", message="Required", field="email")
        assert err.code == "validation_error"
        assert err.message == "Required"
        assert err.field == "email"

    def test_error_detail_without_field(self) -> None:
        err = ErrorDetail(code="unauthorized", message="Not authenticated")
        assert err.field is None


class TestApiResponse:
    """Tests for ApiResponse envelope."""

    def test_success_envelope(self) -> None:
        resp = ApiResponse(data={"id": "123"}, meta={"request_id": "abc"})
        d = resp.to_dict()
        assert d["data"] == {"id": "123"}
        assert d["meta"]["request_id"] == "abc"
        assert d["errors"] == []

    def test_error_envelope(self) -> None:
        resp = ApiResponse(
            errors=[ErrorDetail(code="not_found", message="Item not found")],
            meta={"request_id": "abc"},
        )
        d = resp.to_dict()
        assert d["data"] is None
        assert len(d["errors"]) == 1
        assert d["errors"][0]["code"] == "not_found"
        assert "field" not in d["errors"][0]

    def test_error_with_field(self) -> None:
        resp = ApiResponse(
            errors=[ErrorDetail(code="validation_error", message="Required", field="name")]
        )
        d = resp.to_dict()
        assert d["errors"][0]["field"] == "name"


class TestSuccessResponse:
    """Tests for success_response helper."""

    def test_success_response_default(self, app: Flask) -> None:
        with app.test_request_context():
            response, status = success_response({"key": "value"})
            assert status == 200
            data = response.get_json()
            assert data["data"] == {"key": "value"}
            assert data["errors"] == []
            assert "request_id" in data["meta"]

    def test_success_response_custom_status(self, app: Flask) -> None:
        with app.test_request_context():
            response, status = success_response(None, status_code=201)
            assert status == 201

    def test_success_response_with_meta(self, app: Flask) -> None:
        with app.test_request_context():
            response, status = success_response(None, meta={"page": 1})
            data = response.get_json()
            assert data["meta"]["page"] == 1


class TestErrorResponse:
    """Tests for error_response helper."""

    def test_error_response(self, app: Flask) -> None:
        with app.test_request_context():
            response, status = error_response("not_found", "Item not found", status_code=404)
            assert status == 404
            data = response.get_json()
            assert data["data"] is None
            assert len(data["errors"]) == 1
            assert data["errors"][0]["code"] == "not_found"

    def test_error_response_with_field(self, app: Flask) -> None:
        with app.test_request_context():
            response, status = error_response(
                "validation_error", "Required", status_code=422, field_name="email"
            )
            data = response.get_json()
            assert data["errors"][0]["field"] == "email"

    def test_error_response_with_multiple_errors(self, app: Flask) -> None:
        with app.test_request_context():
            errors = [
                ErrorDetail(code="validation_error", message="Required", field="name"),
                ErrorDetail(code="validation_error", message="Too short", field="password"),
            ]
            response, status = error_response("validation_error", "Failed", status_code=422, errors=errors)
            data = response.get_json()
            assert len(data["errors"]) == 2


class TestHttpStatusToCode:
    """Tests for HTTP status code mapping."""

    def test_known_status_codes(self) -> None:
        assert _http_status_to_code(400) == "bad_request"
        assert _http_status_to_code(401) == "unauthorized"
        assert _http_status_to_code(403) == "forbidden"
        assert _http_status_to_code(404) == "not_found"
        assert _http_status_to_code(409) == "conflict"
        assert _http_status_to_code(413) == "payload_too_large"
        assert _http_status_to_code(422) == "validation_error"
        assert _http_status_to_code(429) == "rate_limited"
        assert _http_status_to_code(500) == "internal_error"
        assert _http_status_to_code(503) == "service_unavailable"

    def test_unknown_status_code(self) -> None:
        assert _http_status_to_code(418) == "error"


class TestRegisterErrorHandlers:
    """Tests for Flask error handler registration."""

    def test_handles_http_exception(self, app: Flask) -> None:
        register_error_handlers(app)
        client = app.test_client()

        @app.route("/not-here")
        def nope() -> str:
            return "nope"

        resp = client.get("/does-not-exist")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["errors"][0]["code"] == "not_found"

    def test_handles_generic_exception(self, app: Flask) -> None:
        register_error_handlers(app)

        @app.route("/boom")
        def boom() -> str:
            msg = "Something broke"
            raise RuntimeError(msg)

        client = app.test_client()
        resp = client.get("/boom")
        assert resp.status_code == 500
        data = resp.get_json()
        assert data["errors"][0]["code"] == "internal_error"
        assert "unexpected" in data["errors"][0]["message"].lower()
