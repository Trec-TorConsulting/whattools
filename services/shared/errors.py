"""Shared error handlers and JSON error response envelope."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from flask import Flask, Response, jsonify, request
from marshmallow import ValidationError
from werkzeug.exceptions import HTTPException


@dataclass
class ErrorDetail:
    """Single error in the response envelope."""

    code: str
    message: str
    field: str | None = None


@dataclass
class ApiResponse:
    """Standard JSON response envelope."""

    data: Any = None
    meta: dict[str, Any] = field(default_factory=dict)
    errors: list[ErrorDetail] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "data": self.data,
            "meta": self.meta,
            "errors": [{"code": e.code, "message": e.message, **({"field": e.field} if e.field else {})} for e in self.errors],
        }


def success_response(data: Any = None, *, status_code: int = 200, meta: dict[str, Any] | None = None) -> tuple[Response, int]:
    """Create a success response in the standard envelope format."""
    response = ApiResponse(
        data=data,
        meta={"request_id": request.headers.get("X-Request-ID", str(uuid.uuid4())), **(meta or {})},
    )
    return jsonify(response.to_dict()), status_code


def error_response(
    code: str,
    message: str,
    *,
    status_code: int = 400,
    field_name: str | None = None,
    errors: list[ErrorDetail] | None = None,
) -> tuple[Response, int]:
    """Create an error response in the standard envelope format."""
    error_list = errors or [ErrorDetail(code=code, message=message, field=field_name)]
    response = ApiResponse(
        meta={"request_id": request.headers.get("X-Request-ID", str(uuid.uuid4()))},
        errors=error_list,
    )
    return jsonify(response.to_dict()), status_code


def register_error_handlers(app: Flask) -> None:
    """Register centralized error handlers on a Flask app."""

    @app.errorhandler(ValidationError)
    def handle_validation_error(error: ValidationError) -> tuple[Response, int]:
        errors = []
        if isinstance(error.messages, dict):
            for field_name, messages in error.messages.items():
                for msg in messages:
                    errors.append(ErrorDetail(code="validation_error", message=str(msg), field=str(field_name)))
        else:
            for msg in error.messages:
                errors.append(ErrorDetail(code="validation_error", message=str(msg)))
        return error_response("validation_error", "Validation failed", status_code=422, errors=errors)

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException) -> tuple[Response, int]:
        return error_response(
            _http_status_to_code(error.code or 500),
            error.description or "An error occurred",
            status_code=error.code or 500,
        )

    @app.errorhandler(Exception)
    def handle_generic_exception(error: Exception) -> tuple[Response, int]:
        app.logger.exception("Unhandled exception: %s", error)
        return error_response(
            "internal_error",
            "An unexpected error occurred",
            status_code=500,
        )


def _http_status_to_code(status: int) -> str:
    """Map HTTP status codes to error code strings."""
    mapping = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        409: "conflict",
        413: "payload_too_large",
        422: "validation_error",
        429: "rate_limited",
        500: "internal_error",
        502: "bad_gateway",
        503: "service_unavailable",
    }
    return mapping.get(status, "error")
