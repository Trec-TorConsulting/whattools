"""Request/response logging middleware — structured JSON, no body logging."""

import time

from flask import Flask, g, request

from services.shared.logging import get_logger

logger = get_logger("gateway.access")


def init_request_logging(app: Flask) -> None:
    """Register before/after request hooks for structured access logging."""

    @app.before_request
    def start_timer() -> None:
        g.start_time = time.monotonic()

    @app.after_request
    def log_request(response):  # type: ignore[no-untyped-def]
        duration_ms = round((time.monotonic() - getattr(g, "start_time", time.monotonic())) * 1000, 2)
        request_id = getattr(g, "request_id", None)

        # Extract user_id from JWT if present (without importing jwt libs)
        user_id = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            # Just note that auth is present — don't decode the JWT in the gateway
            user_id = "authenticated"

        logger.info(
            "request_completed",
            method=request.method,
            path=request.path,
            status=response.status_code,
            duration_ms=duration_ms,
            client_ip=request.remote_addr,
            user_id=user_id,
            request_id=request_id,
        )
        return response
