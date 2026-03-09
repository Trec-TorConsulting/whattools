"""Shared test fixtures for all WhatTools services."""

import os
import uuid
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock

import pytest
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from services.shared.models import Base


@pytest.fixture(scope="session")
def db_engine() -> Any:
    """Create a test database engine using SQLite in-memory."""
    engine = create_engine("sqlite:///:memory:", echo=False)
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
    """Provide a consistent test account ID."""
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture()
def test_user_id() -> uuid.UUID:
    """Provide a consistent test user ID."""
    return uuid.UUID("00000000-0000-0000-0000-000000000002")


@pytest.fixture()
def mock_redis() -> MagicMock:
    """Provide a mocked Redis client."""
    return MagicMock()


@pytest.fixture()
def app() -> Flask:
    """Create a minimal Flask app for testing."""
    test_app = Flask("test")
    test_app.config["TESTING"] = True
    test_app.config["SECRET_KEY"] = "test-secret"
    test_app.config["JWT_SECRET_KEY"] = "test-jwt-secret"
    return test_app
