"""Health check blueprint for Kubernetes liveness and readiness probes."""

from flask import Blueprint, Response, jsonify
from sqlalchemy import text
from sqlalchemy.orm import Session


def create_health_blueprint(get_db: callable, service_name: str) -> Blueprint:  # type: ignore[type-arg]
    """Create a health check blueprint for a service.

    Args:
        get_db: Callable that returns a SQLAlchemy Session.
        service_name: Name of the service (for response body).

    Returns:
        Flask Blueprint with /health and /ready endpoints.
    """
    bp = Blueprint("health", __name__)

    @bp.route("/health")
    def health() -> tuple[Response, int]:
        """Liveness probe — is the process running?"""
        return jsonify({"status": "ok", "service": service_name}), 200

    @bp.route("/ready")
    def ready() -> tuple[Response, int]:
        """Readiness probe — can we serve traffic?"""
        try:
            db: Session = get_db()
            db.execute(text("SELECT 1"))
            return jsonify({"status": "ready", "service": service_name}), 200
        except Exception as e:
            return jsonify({"status": "not_ready", "service": service_name, "reason": str(e)}), 503

    return bp
