"""Integration tests for livestream routes."""

import json
import uuid
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token

from services.shared.errors import register_error_handlers
from services.whatnot.services.oauth_service import OAuthServiceError

TEST_ENCRYPTION_KEY = "I2z4QxvoJ-V-xCVM8R0gF8e0LJvQa6dKAnBUJbcvfwo="


@pytest.fixture(autouse=True)
def _set_env(monkeypatch):
    monkeypatch.setenv("WHATNOT_ENCRYPTION_KEY", TEST_ENCRYPTION_KEY)


@pytest.fixture()
def livestream_app(db_session):
    from services.whatnot.routes.livestream_routes import livestream_bp

    app = Flask("test")
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    app.config["JWT_SECRET_KEY"] = "test-jwt-secret"
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 900
    app.config["_EVENT_PUBLISHER"] = None
    JWTManager(app)
    register_error_handlers(app)
    app.register_blueprint(livestream_bp, url_prefix="/api/v1/whatnot/livestreams")

    @app.before_request
    def inject_db():
        from flask import g
        g.db_session = db_session

    return app


@pytest.fixture()
def client(livestream_app):
    return livestream_app.test_client()


def _make_auth_headers(app, account_id=None):
    aid = str(account_id or uuid.UUID("00000000-0000-0000-0000-000000000001"))
    with app.app_context():
        token = create_access_token(
            identity="test-user",
            additional_claims={"account_id": aid, "role": "owner"},
        )
    return {"Authorization": f"Bearer {token}"}


class TestLivestreamRoutes:
    @patch("services.whatnot.routes.livestream_routes.LivestreamService")
    @patch("services.whatnot.routes.livestream_routes.OAuthService")
    def test_sync_livestreams_success(self, MockOAuth, MockService, client, livestream_app, sample_account):
        mock_oauth = MagicMock()
        mock_oauth.get_access_token.return_value = "test_token"
        MockOAuth.return_value = mock_oauth

        mock_svc = MagicMock()
        mock_svc.pull_livestreams.return_value = {"synced": 3, "created": 2, "updated": 1}
        MockService.return_value = mock_svc

        headers = _make_auth_headers(livestream_app, sample_account.id)
        resp = client.post("/api/v1/whatnot/livestreams/sync", headers=headers)

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["synced"] == 3

    @patch("services.whatnot.routes.livestream_routes.OAuthService")
    def test_sync_livestreams_not_connected(self, MockOAuth, client, livestream_app, sample_account):
        mock_oauth = MagicMock()
        mock_oauth.get_access_token.side_effect = OAuthServiceError(
            "Whatnot account not connected", "not_connected", 400
        )
        MockOAuth.return_value = mock_oauth

        headers = _make_auth_headers(livestream_app, sample_account.id)
        resp = client.post("/api/v1/whatnot/livestreams/sync", headers=headers)

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["errors"][0]["code"] == "not_connected"

    @patch("services.whatnot.routes.livestream_routes.LivestreamService")
    @patch("services.whatnot.routes.livestream_routes.OAuthService")
    def test_sync_livestreams_service_error(self, MockOAuth, MockService, client, livestream_app, sample_account):
        from services.whatnot.services.livestream_service import LivestreamServiceError

        mock_oauth = MagicMock()
        mock_oauth.get_access_token.return_value = "test_token"
        MockOAuth.return_value = mock_oauth

        mock_svc = MagicMock()
        mock_svc.pull_livestreams.side_effect = LivestreamServiceError(
            "Failed to fetch", "livestream_error", 500
        )
        MockService.return_value = mock_svc

        headers = _make_auth_headers(livestream_app, sample_account.id)
        resp = client.post("/api/v1/whatnot/livestreams/sync", headers=headers)

        assert resp.status_code == 500
        data = resp.get_json()
        assert data["errors"][0]["code"] == "livestream_error"

    def test_sync_livestreams_unauthenticated(self, client):
        resp = client.post("/api/v1/whatnot/livestreams/sync")
        assert resp.status_code in (401, 422)
