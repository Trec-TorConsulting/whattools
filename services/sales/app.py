"""Flask app factory for the sales service."""

from typing import Any

import redis
from flask import Flask

from services.shared.app_factory import create_base_app
from services.shared.database import init_db
from services.shared.events import EventPublisher
from services.shared.health import create_health_blueprint


def create_app(*, config_overrides: dict[str, Any] | None = None) -> Flask:
    """Create and configure the sales service Flask app."""
    app = create_base_app("sales", config_overrides=config_overrides)

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

    health_bp = create_health_blueprint(get_db, "sales")
    app.register_blueprint(health_bp)

    # API routes
    from services.sales.routes.show_routes import shows_bp
    from services.sales.routes.order_routes import orders_bp

    app.register_blueprint(shows_bp, url_prefix="/api/v1/shows")
    app.register_blueprint(orders_bp, url_prefix="/api/v1/orders")

    return app
