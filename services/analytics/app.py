"""Flask app factory for the analytics service."""

from typing import Any

import redis
from flask import Flask

from services.shared.app_factory import create_base_app
from services.shared.database import init_db
from services.shared.health import create_health_blueprint


def create_app(*, config_overrides: dict[str, Any] | None = None) -> Flask:
    """Create and configure the analytics service Flask app."""
    app = create_base_app("analytics", config_overrides=config_overrides)

    # Database (read-only queries against shared DB)
    if not app.config.get("TESTING"):
        init_db(app)

    # Redis for caching
    redis_url = app.config.get("REDIS_URL", "redis://localhost:6379/0")
    if not app.config.get("TESTING"):
        redis_client = redis.from_url(redis_url)
        app.config["_REDIS_CLIENT"] = redis_client
    else:
        app.config.setdefault("_REDIS_CLIENT", None)

    # Health check
    from services.shared.database import get_db

    health_bp = create_health_blueprint(get_db, "analytics")
    app.register_blueprint(health_bp)

    # API routes
    from services.auth.models import models as _auth_models  # noqa: F401 — register accounts table
    from services.analytics.routes.analytics_routes import analytics_bp
    from services.analytics.routes.export_routes import export_bp

    app.register_blueprint(analytics_bp, url_prefix="/api/v1/analytics")
    app.register_blueprint(export_bp, url_prefix="/api/v1/analytics/exports")

    return app
