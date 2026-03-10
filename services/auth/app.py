"""Flask app factory for the auth service."""

import os
from typing import Any

import redis
from flask import Flask

from services.shared.app_factory import create_base_app
from services.shared.database import init_db
from services.shared.events import EventPublisher
from services.shared.health import create_health_blueprint


def create_app(*, config_overrides: dict[str, Any] | None = None) -> Flask:
    """Create and configure the auth service Flask app.

    Args:
        config_overrides: Optional config dict (used in testing).

    Returns:
        Fully configured Flask app.
    """
    app = create_base_app("auth", config_overrides=config_overrides)

    # Database
    if not app.config.get("TESTING"):
        init_db(app)

    # Redis / event publisher
    redis_url = app.config.get("REDIS_URL", "redis://localhost:6379/0")
    if not app.config.get("TESTING"):
        redis_client = redis.from_url(redis_url)
        app.config["_EVENT_PUBLISHER"] = EventPublisher(redis_client)
    else:
        app.config.setdefault("_EVENT_PUBLISHER", None)

    # Health check
    from services.shared.database import get_db

    health_bp = create_health_blueprint(get_db, "auth")
    app.register_blueprint(health_bp)

    # API routes
    from services.auth.routes.auth_routes import auth_bp
    from services.auth.routes.account_routes import account_bp
    from services.auth.routes.profile_routes import profile_bp
    from services.auth.routes.billing_routes import billing_bp

    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
    app.register_blueprint(account_bp, url_prefix="/api/v1")
    app.register_blueprint(profile_bp, url_prefix="/api/v1")
    app.register_blueprint(billing_bp, url_prefix="/api/v1/billing")

    return app
