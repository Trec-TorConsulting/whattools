"""Test fixtures for auth service tests."""

import uuid
from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from services.auth.models.models import (
    Account,
    PlanTier,
    RefreshToken,
    TeamInvite,
    TeamRole,
    User,
)
from services.shared.models import Base


@pytest.fixture(scope="session")
def db_engine() -> Any:
    """Create a test database engine using SQLite in-memory."""
    engine = create_engine("sqlite:///:memory:", echo=False)

    # Enable foreign key enforcement for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Import models to register them with Base metadata
    from services.auth.models import models as _  # noqa: F811

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
def test_user_id() -> uuid.UUID:
    return uuid.UUID("00000000-0000-0000-0000-000000000002")


@pytest.fixture()
def mock_redis() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def mock_event_publisher() -> MagicMock:
    publisher = MagicMock()
    publisher.publish = MagicMock(return_value=True)
    return publisher


@pytest.fixture()
def app(db_engine: Any) -> Flask:
    """Create a test Flask app with JWT and test config."""
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
def sample_account(db_session: Session) -> Account:
    """Create a sample account in the database."""
    account = Account(name="Test Business", plan_tier=PlanTier.FREE)
    db_session.add(account)
    db_session.flush()
    return account


@pytest.fixture()
def sample_owner(db_session: Session, sample_account: Account) -> User:
    """Create a sample owner user in the database."""
    user = User(
        account_id=sample_account.id,
        email="owner@test.com",
        password_hash="",
        name="Test Owner",
        role=TeamRole.OWNER,
        is_verified=True,
        is_active=True,
    )
    user.set_password("StrongPass1")
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture()
def sample_admin(db_session: Session, sample_account: Account) -> User:
    """Create a sample admin user in the database."""
    user = User(
        account_id=sample_account.id,
        email="admin@test.com",
        password_hash="",
        name="Test Admin",
        role=TeamRole.ADMIN,
        is_verified=True,
        is_active=True,
    )
    user.set_password("StrongPass1")
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture()
def sample_member(db_session: Session, sample_account: Account) -> User:
    """Create a sample member user in the database."""
    user = User(
        account_id=sample_account.id,
        email="member@test.com",
        password_hash="",
        name="Test Member",
        role=TeamRole.MEMBER,
        is_verified=True,
        is_active=True,
    )
    user.set_password("StrongPass1")
    db_session.add(user)
    db_session.flush()
    return user


def make_auth_headers(app: Flask, user: User) -> dict[str, str]:
    """Generate Authorization headers with a JWT for the given user."""
    with app.app_context():
        token = create_access_token(
            identity=str(user.id),
            additional_claims={"account_id": str(user.account_id), "role": user.role},
        )
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
