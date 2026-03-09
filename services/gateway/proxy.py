"""Request proxy — forwards incoming requests to internal microservices via httpx."""

import os
from typing import Any

import httpx
from flask import Response, request

from services.shared.logging import get_logger

logger = get_logger("gateway.proxy")

# Timeout for proxied requests (seconds)
PROXY_TIMEOUT = float(os.environ.get("PROXY_TIMEOUT", "30"))

# Service URL registry — resolved at startup from env vars
SERVICE_URLS: dict[str, str] = {}


def init_service_urls() -> dict[str, str]:
    """Initialize service URL registry from environment variables."""
    global SERVICE_URLS
    SERVICE_URLS = {
        "auth": os.environ.get("AUTH_SERVICE_URL", "http://localhost:5001"),
        "inventory": os.environ.get("INVENTORY_SERVICE_URL", "http://localhost:5002"),
        "sales": os.environ.get("SALES_SERVICE_URL", "http://localhost:5003"),
        "analytics": os.environ.get("ANALYTICS_SERVICE_URL", "http://localhost:5004"),
        "shipping": os.environ.get("SHIPPING_SERVICE_URL", "http://localhost:5005"),
    }
    return SERVICE_URLS


# Route prefix → service name mapping
ROUTE_MAP: list[tuple[str, str]] = [
    ("/api/v1/auth/", "auth"),
    ("/api/v1/account", "auth"),
    ("/api/v1/users/", "auth"),
    ("/api/v1/items", "inventory"),
    ("/api/v1/categories", "inventory"),
    ("/api/v1/csv/", "inventory"),
    ("/api/v1/shows", "sales"),
    ("/api/v1/orders", "sales"),
    ("/api/v1/analytics", "analytics"),
    ("/api/v1/shipments", "shipping"),
    ("/api/v1/packing-lists", "shipping"),
]


def resolve_service(path: str) -> str | None:
    """Determine which backend service should handle the request.

    Args:
        path: The request path (e.g., /api/v1/items/123).

    Returns:
        Service name ('auth', 'inventory') or None if no match.
    """
    for prefix, service in ROUTE_MAP:
        if path.startswith(prefix):
            return service
    return None


def proxy_request(service_name: str) -> tuple[Response, int]:
    """Forward the current Flask request to the target service and return its response.

    Preserves: method, path, query string, headers, body.
    Injects: X-Request-ID (already set by middleware).

    Args:
        service_name: Name of the target service (key in SERVICE_URLS).

    Returns:
        Tuple of (Flask Response, status code).
    """
    base_url = SERVICE_URLS.get(service_name)
    if not base_url:
        logger.error("unknown_service", service=service_name)
        return Response('{"data": null, "meta": {}, "errors": [{"code": "internal_error", "message": "Unknown service"}]}',
                        status=500, content_type="application/json"), 500

    # Build target URL
    target_url = f"{base_url}{request.path}"
    if request.query_string:
        target_url = f"{target_url}?{request.query_string.decode('utf-8')}"

    # Forward headers (exclude hop-by-hop headers)
    excluded_headers = {"host", "content-length", "transfer-encoding"}
    forward_headers: dict[str, str] = {}
    for key, value in request.headers:
        if key.lower() not in excluded_headers:
            forward_headers[key] = value

    try:
        with httpx.Client(timeout=PROXY_TIMEOUT) as client:
            resp = client.request(
                method=request.method,
                url=target_url,
                headers=forward_headers,
                content=request.get_data(),
            )
    except httpx.TimeoutException:
        logger.warning("proxy_timeout", service=service_name, path=request.path)
        return Response(
            '{"data": null, "meta": {}, "errors": [{"code": "gateway_timeout", "message": "Upstream service timed out"}]}',
            status=504,
            content_type="application/json",
        ), 504
    except httpx.ConnectError:
        logger.error("proxy_connect_error", service=service_name, path=request.path)
        return Response(
            '{"data": null, "meta": {}, "errors": [{"code": "bad_gateway", "message": "Upstream service unavailable"}]}',
            status=502,
            content_type="application/json",
        ), 502

    # Build Flask response from upstream response
    excluded_response_headers = {"content-encoding", "content-length", "transfer-encoding"}
    response_headers: dict[str, str] = {}
    for key, value in resp.headers.items():
        if key.lower() not in excluded_response_headers:
            response_headers[key] = value

    flask_response = Response(
        response=resp.content,
        status=resp.status_code,
        headers=response_headers,
    )
    return flask_response, resp.status_code
