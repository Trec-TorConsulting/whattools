"""Gateway routes — proxy all /api/v1/* requests to the correct service."""

from flask import Blueprint

from services.gateway.proxy import proxy_request, resolve_service
from services.shared.errors import error_response

gateway_bp = Blueprint("gateway", __name__)


@gateway_bp.route("/api/v1/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
def proxy_route(path: str):  # type: ignore[no-untyped-def]
    """Catch-all route that proxies /api/v1/* to internal services."""
    from flask import request

    service = resolve_service(request.path)
    if service is None:
        return error_response("not_found", "The requested endpoint does not exist.", status_code=404)

    response, status_code = proxy_request(service)
    return response, status_code
