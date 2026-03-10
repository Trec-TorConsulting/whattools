"""Test fixtures for whatnot service tests."""

import uuid
from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from services.shared.models import Base


@pytest.fixture(scope="session")
def db_engine() -> Any:
    """Create a test database engine using SQLite in-memory."""
    engine = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Import all models to register them
    from services.auth.models import models as _auth  # noqa: F401
    from services.inventory.models import models as _inv  # noqa: F401
    from services.sales.models import models as _sales  # noqa: F401
    from services.whatnot.models import (  # noqa: F401
        WhatnotCredential,
        SyncLog,
        WebhookEvent,
    )

    Base.metadata.create_all(engine)
    return engine


@pytest.fixture()
def db_session(db_engine: Any) -> Generator[Session, None, None]:
    """Create a database session that rolls back after each test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection)
    session = factory()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def test_account_id() -> uuid.UUID:
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture()
def app(db_engine: Any) -> Flask:
    """Create a test Flask app."""
    test_app = Flask("test")
    test_app.config["TESTING"] = True
    test_app.config["SECRET_KEY"] = "test-secret"
    test_app.config["JWT_SECRET_KEY"] = "test-jwt-secret"
    test_app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 900
    test_app.config["JWT_REFRESH_TOKEN_EXPIRES"] = 604800
    test_app.config["_EVENT_PUBLISHER"] = None
    JWTManager(test_app)
    return test_app


@pytest.fixture()
def sample_account(db_session: Session) -> Any:
    """Create a sample account."""
    from services.auth.models.models import Account, PlanTier

    account = Account(name="Test Business", plan_tier=PlanTier.FREE)
    db_session.add(account)
    db_session.flush()
    return account


@pytest.fixture()
def sample_credential(db_session: Session, sample_account: Any) -> Any:
    """Create a sample Whatnot credential."""
    from services.whatnot.models import WhatnotCredential

    cred = WhatnotCredential(
        account_id=sample_account.id,
        whatnot_user_id="wn_user_123",
        whatnot_username="testuser",
        encrypted_access_token="encrypted_token",
        encrypted_refresh_token="encrypted_refresh",
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        scopes="full_access",
        is_active=True,
        webhook_secret="test_webhook_secret",
    )
    db_session.add(cred)
    db_session.flush()
    return cred


@pytest.fixture()
def mock_whatnot_client() -> MagicMock:
    """Create a mock WhatnotClient."""
    client = MagicMock()
    client.execute.return_value = {"data": {}}
    client.execute_mutation.return_value = {}
    return client
