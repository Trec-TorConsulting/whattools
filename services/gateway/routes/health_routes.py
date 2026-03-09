"""Aggregated health check — pings all downstream services."""

import os
from typing import Any

import httpx
from flask import Blueprint, Response, jsonify

from services.shared.logging import get_logger

logger = get_logger("gateway.health")

health_bp = Blueprint("health", __name__)

HEALTH_TIMEOUT = float(os.environ.get("HEALTH_CHECK_TIMEOUT", "5"))


def _check_service(name: str, base_url: str) -> dict[str, str]:
    """Check a single service's /health endpoint."""
    try:
        resp = httpx.get(f"{base_url}/health", timeout=HEALTH_TIMEOUT)
        if resp.status_code == 200:
            return {"name": name, "status": "ok"}
        return {"name": name, "status": "unhealthy", "detail": f"HTTP {resp.status_code}"}
    except httpx.ConnectError:
        return {"name": name, "status": "unhealthy", "detail": "Connection refused"}
    except httpx.TimeoutException:
        return {"name": name, "status": "unhealthy", "detail": "Timeout"}


@health_bp.route("/health")
def gateway_health():  # type: ignore[no-untyped-def]
    """Gateway liveness check — always returns 200 if the process is running."""
    return jsonify({"status": "ok", "service": "gateway"}), 200


@health_bp.route("/api/v1/health")
def aggregated_health():  # type: ignore[no-untyped-def]
    """Aggregated health — checks gateway + all downstream services."""
    from services.gateway.proxy import SERVICE_URLS

    results: dict[str, Any] = {"gateway": "ok"}
    all_healthy = True

    for name, base_url in SERVICE_URLS.items():
        check = _check_service(name, base_url)
        results[name] = check["status"]
        if check["status"] != "ok":
            all_healthy = False
            if "detail" in check:
                results[f"{name}_detail"] = check["detail"]

    status_code = 200 if all_healthy else 503
    return jsonify({"status": "ok" if all_healthy else "degraded", "services": results}), status_code
