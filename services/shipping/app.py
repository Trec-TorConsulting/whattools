"""Flask app factory for the shipping service."""

from typing import Any

import redis
from flask import Flask

from services.shared.app_factory import create_base_app
from services.shared.database import init_db
from services.shared.events import EventPublisher
from services.shared.health import create_health_blueprint
from services.shipping.providers.manual import ManualProvider


def create_app(*, config_overrides: dict[str, Any] | None = None) -> Flask:
    """Create and configure the shipping service Flask app."""
    app = create_base_app("shipping", config_overrides=config_overrides)

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

    # Shipping provider (ManualProvider for MVP)
    app.config.setdefault("_SHIPPING_PROVIDER", ManualProvider())

    # Health check
    from services.shared.database import get_db

    health_bp = create_health_blueprint(get_db, "shipping")
    app.register_blueprint(health_bp)

    # API routes
    from services.auth.models import models as _auth_models  # noqa: F401 — register accounts table
    from services.shipping.routes.shipment_routes import shipments_bp
    from services.shipping.routes.packing_list_routes import packing_lists_bp

    app.register_blueprint(shipments_bp, url_prefix="/api/v1/shipments")
    app.register_blueprint(packing_lists_bp, url_prefix="/api/v1/packing-lists")

    return app
