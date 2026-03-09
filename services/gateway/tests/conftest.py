"""Test fixtures for gateway service tests."""

from typing import Any
from unittest.mock import MagicMock

import pytest
from flask import Flask

from services.gateway.app import create_app


@pytest.fixture()
def app() -> Flask:
    """Create a test gateway app."""
    return create_app(config_overrides={
        "TESTING": True,
        "SECRET_KEY": "test-secret",
    })


@pytest.fixture()
def client(app: Flask):  # type: ignore[no-untyped-def]
    """Create a test client."""
    return app.test_client()
