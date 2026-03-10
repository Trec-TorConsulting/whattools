"""Integration tests for whatnot API routes."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token

from services.auth.models.models import Account, PlanTier, TeamRole, User
from services.shared.errors import register_error_handlers

TEST_ENCRYPTION_KEY = "I2z4QxvoJ-V-xCVM8R0gF8e0LJvQa6dKAnBUJbcvfwo="


@pytest.fixture(autouse=True)
def _set_encryption_key(monkeypatch):
    monkeypatch.setenv("WHATNOT_ENCRYPTION_KEY", TEST_ENCRYPTION_KEY)


def make_auth_headers(app: Flask, user: User) -> dict[str, str]:
    """Generate Authorization headers with a JWT for the given user."""
    with app.app_context():
        token = create_access_token(
            identity=str(user.id),
            additional_claims={"account_id": str(user.account_id), "role": user.role},
        )
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture()
def sample_owner(db_session, sample_account):
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
def whatnot_app(db_session, db_engine):
    """Create a test Flask app wired to the whatnot routes."""
    from services.whatnot.routes.oauth_routes import oauth_bp
    from services.whatnot.routes.sync_routes import sync_bp

    app = Flask("test")
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    app.config["JWT_SECRET_KEY"] = "test-jwt-secret"
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 900
    app.config["_EVENT_PUBLISHER"] = None
    JWTManager(app)
    register_error_handlers(app)

    app.register_blueprint(oauth_bp, url_prefix="/api/v1/whatnot")
    app.register_blueprint(sync_bp, url_prefix="/api/v1/whatnot/sync")

    @app.before_request
    def inject_db():  # type: ignore[no-untyped-def]
        from flask import g
        g.db_session = db_session

    return app


@pytest.fixture()
def client(whatnot_app):
    return whatnot_app.test_client()


class TestOAuthRoutes:
    def test_status_not_connected(self, client, whatnot_app, sample_owner):
        headers = make_auth_headers(whatnot_app, sample_owner)
        resp = client.get("/api/v1/whatnot/status", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["connected"] is False

    def test_status_connected(self, client, whatnot_app, sample_owner, sample_credential):
        headers = make_auth_headers(whatnot_app, sample_owner)
        resp = client.get("/api/v1/whatnot/status", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["connected"] is True
        assert data["data"]["whatnot_username"] == "testuser"

    def test_disconnect_not_connected(self, client, whatnot_app, sample_owner):
        headers = make_auth_headers(whatnot_app, sample_owner)
        resp = client.post("/api/v1/whatnot/disconnect", headers=headers)
        # disconnect is a no-op when not connected — returns 200
        assert resp.status_code == 200

    def test_status_unauthenticated(self, client):
        resp = client.get("/api/v1/whatnot/status")
        assert resp.status_code == 401


class TestSyncRoutes:
    def test_sync_status_empty(self, client, whatnot_app, sample_owner):
        headers = make_auth_headers(whatnot_app, sample_owner)
        resp = client.get("/api/v1/whatnot/sync/status", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "latest" in data["data"]
        assert "history" in data["data"]
