"""Database session management and dependency injection for Flask."""

import os
from collections.abc import Generator
from typing import Any

from flask import Flask, g
from sqlalchemy.orm import Session

from services.shared.app_factory import create_db_engine, create_session_factory


def init_db(app: Flask) -> None:
    """Initialize database engine and session factory on the Flask app.

    Args:
        app: Flask app instance.
    """
    database_url = app.config.get("SQLALCHEMY_DATABASE_URI") or os.environ.get(
        "DATABASE_URL", "postgresql://whattools:whattools@localhost:5432/whattools"
    )
    engine = create_db_engine(database_url)
    app.config["_DB_ENGINE"] = engine
    app.config["_DB_SESSION_FACTORY"] = create_session_factory(engine)

    @app.teardown_appcontext
    def close_session(exception: BaseException | None = None) -> None:
        session: Session | None = g.pop("db_session", None)
        if session is not None:
            if exception:
                session.rollback()
            session.close()


def get_db() -> Session:
    """Get the current database session from Flask's g context.

    Returns:
        SQLAlchemy Session for the current request.
    """
    from flask import current_app

    if "db_session" not in g:
        factory: Any = current_app.config["_DB_SESSION_FACTORY"]
        g.db_session = factory()
    return g.db_session
