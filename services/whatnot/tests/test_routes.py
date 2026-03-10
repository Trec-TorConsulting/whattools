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

    @patch("services.whatnot.routes.oauth_routes.OAuthService")
    def test_connect(self, MockOAuth, client, whatnot_app, sample_owner, monkeypatch):
        monkeypatch.setenv("WHATNOT_CLIENT_ID", "test_client_id")
        mock_svc = MagicMock()
        mock_svc.get_authorize_url.return_value = {
            "url": "https://api.whatnot.com/auth?client_id=test",
            "state": "random_state",
        }
        MockOAuth.return_value = mock_svc

        headers = make_auth_headers(whatnot_app, sample_owner)
        resp = client.get("/api/v1/whatnot/connect", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "authorize_url" in data["data"]

    @patch("services.whatnot.routes.oauth_routes.OAuthService")
    def test_connect_error(self, MockOAuth, client, whatnot_app, sample_owner):
        from services.whatnot.services.oauth_service import OAuthServiceError

        mock_svc = MagicMock()
        mock_svc.get_authorize_url.side_effect = OAuthServiceError(
            "Not configured", "configuration_error", 500
        )
        MockOAuth.return_value = mock_svc

        headers = make_auth_headers(whatnot_app, sample_owner)
        resp = client.get("/api/v1/whatnot/connect", headers=headers)
        assert resp.status_code == 500

    def test_callback_missing_code(self, client, whatnot_app, sample_owner):
        headers = make_auth_headers(whatnot_app, sample_owner)
        resp = client.get("/api/v1/whatnot/callback", headers=headers)
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["errors"][0]["code"] == "missing_code"

    def test_callback_oauth_denied(self, client, whatnot_app, sample_owner):
        headers = make_auth_headers(whatnot_app, sample_owner)
        resp = client.get("/api/v1/whatnot/callback?error=access_denied", headers=headers)
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["errors"][0]["code"] == "oauth_denied"

    def test_callback_invalid_state(self, client, whatnot_app, sample_owner):
        headers = make_auth_headers(whatnot_app, sample_owner)
        resp = client.get(
            "/api/v1/whatnot/callback?code=auth_code&state=bad_state",
            headers=headers,
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["errors"][0]["code"] == "invalid_state"

    @patch("services.whatnot.routes.oauth_routes.OAuthService")
    def test_callback_success(self, MockOAuth, client, whatnot_app, sample_owner):
        mock_svc = MagicMock()
        mock_svc.exchange_code.return_value = {
            "connected": True,
            "whatnot_username": "seller1",
        }
        MockOAuth.return_value = mock_svc

        headers = make_auth_headers(whatnot_app, sample_owner)
        # Set the state in session by making a connect call first
        with client.session_transaction() as sess:
            sess["whatnot_oauth_state"] = "valid_state"

        resp = client.get(
            "/api/v1/whatnot/callback?code=auth_code_123&state=valid_state",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["connected"] is True

    @patch("services.whatnot.routes.oauth_routes.OAuthService")
    def test_callback_exchange_error(self, MockOAuth, client, whatnot_app, sample_owner):
        from services.whatnot.services.oauth_service import OAuthServiceError

        mock_svc = MagicMock()
        mock_svc.exchange_code.side_effect = OAuthServiceError("Failed", "oauth_error", 502)
        MockOAuth.return_value = mock_svc

        headers = make_auth_headers(whatnot_app, sample_owner)
        with client.session_transaction() as sess:
            sess["whatnot_oauth_state"] = "valid_state"

        resp = client.get(
            "/api/v1/whatnot/callback?code=bad_code&state=valid_state",
            headers=headers,
        )
        assert resp.status_code == 502

    def test_disconnect_connected(self, client, whatnot_app, sample_owner, sample_credential):
        headers = make_auth_headers(whatnot_app, sample_owner)
        resp = client.post("/api/v1/whatnot/disconnect", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "disconnected" in data["data"]["message"].lower()


class TestSyncRoutes:
    def test_sync_status_empty(self, client, whatnot_app, sample_owner):
        headers = make_auth_headers(whatnot_app, sample_owner)
        resp = client.get("/api/v1/whatnot/sync/status", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "latest" in data["data"]
        assert "history" in data["data"]

    @patch("services.whatnot.routes.sync_routes.LivestreamService")
    @patch("services.whatnot.routes.sync_routes.OrderSyncService")
    @patch("services.whatnot.routes.sync_routes.ProductService")
    @patch("services.whatnot.routes.sync_routes.OAuthService")
    def test_sync_now_success(self, MockOAuth, MockProduct, MockOrder, MockLive, client, whatnot_app, sample_owner):
        mock_oauth = MagicMock()
        mock_oauth.get_access_token.return_value = "test_token"
        MockOAuth.return_value = mock_oauth

        MockProduct.return_value.pull_products.return_value = {"total": 5}
        MockOrder.return_value.pull_orders.return_value = {"synced": 3}
        MockLive.return_value.pull_livestreams.return_value = {"synced": 1}

        headers = make_auth_headers(whatnot_app, sample_owner)
        resp = client.post("/api/v1/whatnot/sync/now", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["products"]["total"] == 5
        assert data["data"]["orders"]["synced"] == 3
        assert data["data"]["livestreams"]["synced"] == 1

    @patch("services.whatnot.routes.sync_routes.OAuthService")
    def test_sync_now_not_connected(self, MockOAuth, client, whatnot_app, sample_owner):
        from services.whatnot.services.oauth_service import OAuthServiceError

        mock_oauth = MagicMock()
        mock_oauth.get_access_token.side_effect = OAuthServiceError(
            "Not connected", "not_connected", 400
        )
        MockOAuth.return_value = mock_oauth

        headers = make_auth_headers(whatnot_app, sample_owner)
        resp = client.post("/api/v1/whatnot/sync/now", headers=headers)
        assert resp.status_code == 400

    @patch("services.whatnot.routes.sync_routes.ProductService")
    @patch("services.whatnot.routes.sync_routes.OAuthService")
    def test_sync_now_partial_failure(self, MockOAuth, MockProduct, client, whatnot_app, sample_owner):
        mock_oauth = MagicMock()
        mock_oauth.get_access_token.return_value = "test_token"
        MockOAuth.return_value = mock_oauth

        MockProduct.return_value.pull_products.side_effect = Exception("product sync failed")

        headers = make_auth_headers(whatnot_app, sample_owner)
        resp = client.post("/api/v1/whatnot/sync/now", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "error" in data["data"]["products"]
