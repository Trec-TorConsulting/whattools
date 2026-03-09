"""Request ID middleware — injects X-Request-ID into every request and response."""

import uuid

from flask import Flask, g, request


def init_request_id(app: Flask) -> None:
    """Register before/after request hooks for X-Request-ID injection."""

    @app.before_request
    def inject_request_id() -> None:
        """Ensure every request has an X-Request-ID."""
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())
        g.request_id = request_id

    @app.after_request
    def set_response_request_id(response):  # type: ignore[no-untyped-def]
        """Add X-Request-ID to the response headers."""
        request_id = getattr(g, "request_id", None)
        if request_id:
            response.headers["X-Request-ID"] = request_id
        return response
