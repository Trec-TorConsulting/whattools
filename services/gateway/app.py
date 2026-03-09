"""Flask app factory for the API gateway."""

import os
from typing import Any

from flask import Flask
from flask_cors import CORS

from services.gateway.middleware.logging import init_request_logging
from services.gateway.middleware.rate_limit import init_rate_limiting
from services.gateway.middleware.request_id import init_request_id
from services.gateway.proxy import init_service_urls
from services.gateway.routes.health_routes import health_bp
from services.gateway.routes.proxy_routes import gateway_bp
from services.shared.errors import register_error_handlers
from services.shared.logging import setup_logging


def create_app(*, config_overrides: dict[str, Any] | None = None) -> Flask:
    """Create and configure the API gateway Flask app."""
    app = Flask("gateway")

    # Base config
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
    app.config["REDIS_URL"] = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    if config_overrides:
        app.config.update(config_overrides)

    # Logging
    setup_logging("gateway", log_level=os.environ.get("LOG_LEVEL", "INFO"))

    # CORS — explicit allowlist
    cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
    CORS(app, origins=cors_origins)

    # Error handlers
    register_error_handlers(app)

    # Middleware
    init_request_id(app)
    init_request_logging(app)

    # Rate limiting
    if not app.config.get("TESTING"):
        init_rate_limiting(app)

    # Service URL registry
    init_service_urls()

    # Routes
    app.register_blueprint(health_bp)
    app.register_blueprint(gateway_bp)

    return app
