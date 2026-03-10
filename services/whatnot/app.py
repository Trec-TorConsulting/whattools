"""Flask app factory for the Whatnot integration service."""

import os
from typing import Any

import redis
from flask import Flask

from services.shared.app_factory import create_base_app
from services.shared.database import init_db
from services.shared.events import EventPublisher
from services.shared.health import create_health_blueprint


def create_app(*, config_overrides: dict[str, Any] | None = None) -> Flask:
    """Create and configure the Whatnot integration service Flask app.

    Args:
        config_overrides: Optional config dict (used in testing).

    Returns:
        Fully configured Flask app.
    """
    app = create_base_app("whatnot", config_overrides=config_overrides)

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

    health_bp = create_health_blueprint(get_db, "whatnot")
    app.register_blueprint(health_bp)

    # API routes
    from services.whatnot.routes.oauth_routes import oauth_bp
    from services.whatnot.routes.product_routes import product_bp
    from services.whatnot.routes.listing_routes import listing_bp
    from services.whatnot.routes.order_routes import order_bp
    from services.whatnot.routes.livestream_routes import livestream_bp
    from services.whatnot.routes.webhook_routes import webhook_bp
    from services.whatnot.routes.sync_routes import sync_bp

    app.register_blueprint(oauth_bp, url_prefix="/api/v1/whatnot")
    app.register_blueprint(product_bp, url_prefix="/api/v1/whatnot")
    app.register_blueprint(listing_bp, url_prefix="/api/v1/whatnot/listings")
    app.register_blueprint(order_bp, url_prefix="/api/v1/whatnot/orders")
    app.register_blueprint(livestream_bp, url_prefix="/api/v1/whatnot/livestreams")
    app.register_blueprint(webhook_bp, url_prefix="/api/v1/whatnot/webhooks")
    app.register_blueprint(sync_bp, url_prefix="/api/v1/whatnot/sync")

    return app
