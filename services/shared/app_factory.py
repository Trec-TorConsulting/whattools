"""Flask app factory base with common configuration."""

import os
from typing import Any

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from services.shared.errors import register_error_handlers
from services.shared.logging import setup_logging


def create_base_app(
    service_name: str,
    *,
    config_overrides: dict[str, Any] | None = None,
) -> Flask:
    """Create a Flask app with common configuration.

    Args:
        service_name: Name of the service (used for logging and health checks).
        config_overrides: Optional dict of Flask config overrides (used in testing).

    Returns:
        Configured Flask app instance.
    """
    app = Flask(service_name)

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "postgresql://whattools:whattools@localhost:5432/whattools"
    )
    app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES", "900"))
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = int(os.environ.get("JWT_REFRESH_TOKEN_EXPIRES", "604800"))
    app.config["REDIS_URL"] = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    if config_overrides:
        app.config.update(config_overrides)

    setup_logging(service_name, log_level=os.environ.get("LOG_LEVEL", "INFO"))

    cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
    CORS(app, origins=cors_origins)

    JWTManager(app)

    register_error_handlers(app)

    return app


def create_db_engine(database_url: str) -> Any:
    """Create a SQLAlchemy engine.

    Args:
        database_url: PostgreSQL connection string.

    Returns:
        SQLAlchemy Engine instance.
    """
    return create_engine(database_url, pool_pre_ping=True, pool_size=10, max_overflow=20)


def create_session_factory(engine: Any) -> sessionmaker[Session]:
    """Create a SQLAlchemy session factory.

    Args:
        engine: SQLAlchemy Engine instance.

    Returns:
        Session factory (sessionmaker).
    """
    return sessionmaker(bind=engine, expire_on_commit=False)
