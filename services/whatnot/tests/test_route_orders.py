"""Integration tests for order routes."""

import json
import uuid
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token

from services.auth.models.models import TeamRole, User
from services.shared.errors import register_error_handlers

TEST_ENCRYPTION_KEY = "I2z4QxvoJ-V-xCVM8R0gF8e0LJvQa6dKAnBUJbcvfwo="


@pytest.fixture(autouse=True)
def _set_env(monkeypatch):
    monkeypatch.setenv("WHATNOT_ENCRYPTION_KEY", TEST_ENCRYPTION_KEY)
    monkeypatch.setenv("WHATNOT_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("WHATNOT_CLIENT_SECRET", "test_client_secret")


def make_auth_headers(app: Flask, user: User) -> dict[str, str]:
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
def order_app(db_session):
    from services.whatnot.routes.order_routes import order_bp

    app = Flask("test")
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    app.config["JWT_SECRET_KEY"] = "test-jwt-secret"
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 900
    app.config["_EVENT_PUBLISHER"] = None
    JWTManager(app)
    register_error_handlers(app)
    app.register_blueprint(order_bp, url_prefix="/api/v1/whatnot/orders")

    @app.before_request
    def inject_db():
        from flask import g
        g.db_session = db_session

    return app


@pytest.fixture()
def client(order_app):
    return order_app.test_client()


class TestOrderSync:
    @patch("services.whatnot.routes.order_routes.OAuthService")
    @patch("services.whatnot.routes.order_routes.OrderSyncService")
    def test_sync_orders_success(self, mock_svc_cls, mock_oauth_cls, client, order_app, sample_owner):
        mock_oauth = MagicMock()
        mock_oauth.get_access_token.return_value = "fake_token"
        mock_oauth_cls.return_value = mock_oauth

        mock_svc = MagicMock()
        mock_svc.pull_orders.return_value = {"created": 10, "updated": 0, "total": 10}
        mock_svc_cls.return_value = mock_svc

        headers = make_auth_headers(order_app, sample_owner)
        resp = client.post("/api/v1/whatnot/orders/sync", headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["total"] == 10

    @patch("services.whatnot.routes.order_routes.OAuthService")
    def test_sync_orders_not_connected(self, mock_oauth_cls, client, order_app, sample_owner):
        from services.whatnot.services.oauth_service import OAuthServiceError
        mock_oauth = MagicMock()
        mock_oauth.get_access_token.side_effect = OAuthServiceError("Not connected", "not_connected", 400)
        mock_oauth_cls.return_value = mock_oauth

        headers = make_auth_headers(order_app, sample_owner)
        resp = client.post("/api/v1/whatnot/orders/sync", headers=headers)
        assert resp.status_code == 400

    @patch("services.whatnot.routes.order_routes.OAuthService")
    @patch("services.whatnot.routes.order_routes.OrderSyncService")
    def test_sync_orders_service_error(self, mock_svc_cls, mock_oauth_cls, client, order_app, sample_owner):
        from services.whatnot.services.order_service import OrderServiceError
        mock_oauth = MagicMock()
        mock_oauth.get_access_token.return_value = "fake_token"
        mock_oauth_cls.return_value = mock_oauth

        mock_svc = MagicMock()
        mock_svc.pull_orders.side_effect = OrderServiceError("Sync failed", "sync_error", 500)
        mock_svc_cls.return_value = mock_svc

        headers = make_auth_headers(order_app, sample_owner)
        resp = client.post("/api/v1/whatnot/orders/sync", headers=headers)
        assert resp.status_code == 500

    def test_sync_orders_unauthenticated(self, client):
        resp = client.post("/api/v1/whatnot/orders/sync")
        assert resp.status_code == 401


class TestPushTracking:
    @patch("services.whatnot.routes.order_routes.OAuthService")
    @patch("services.whatnot.routes.order_routes.OrderSyncService")
    def test_push_tracking_success(self, mock_svc_cls, mock_oauth_cls, client, order_app, sample_owner):
        mock_oauth = MagicMock()
        mock_oauth.get_access_token.return_value = "fake_token"
        mock_oauth_cls.return_value = mock_oauth

        mock_svc = MagicMock()
        mock_svc.push_tracking.return_value = {"success": True}
        mock_svc_cls.return_value = mock_svc

        headers = make_auth_headers(order_app, sample_owner)
        order_id = str(uuid.uuid4())
        resp = client.post(
            f"/api/v1/whatnot/orders/{order_id}/tracking",
            headers=headers,
            data=json.dumps({"tracking_company": "USPS", "tracking_number": "1Z999AA10123456784"}),
        )
        assert resp.status_code == 200

    def test_push_tracking_missing_fields(self, client, order_app, sample_owner):
        headers = make_auth_headers(order_app, sample_owner)
        order_id = str(uuid.uuid4())
        resp = client.post(
            f"/api/v1/whatnot/orders/{order_id}/tracking",
            headers=headers,
            data=json.dumps({}),
        )
        assert resp.status_code == 422

    def test_push_tracking_missing_tracking_number(self, client, order_app, sample_owner):
        headers = make_auth_headers(order_app, sample_owner)
        order_id = str(uuid.uuid4())
        resp = client.post(
            f"/api/v1/whatnot/orders/{order_id}/tracking",
            headers=headers,
            data=json.dumps({"tracking_company": "USPS"}),
        )
        assert resp.status_code == 422


class TestCancelOrder:
    @patch("services.whatnot.routes.order_routes.OAuthService")
    @patch("services.whatnot.routes.order_routes.OrderSyncService")
    def test_cancel_order_success(self, mock_svc_cls, mock_oauth_cls, client, order_app, sample_owner):
        mock_oauth = MagicMock()
        mock_oauth.get_access_token.return_value = "fake_token"
        mock_oauth_cls.return_value = mock_oauth

        mock_svc = MagicMock()
        mock_svc.cancel_order.return_value = {"cancelled": True}
        mock_svc_cls.return_value = mock_svc

        headers = make_auth_headers(order_app, sample_owner)
        order_id = str(uuid.uuid4())
        resp = client.post(f"/api/v1/whatnot/orders/{order_id}/cancel", headers=headers)
        assert resp.status_code == 200

    @patch("services.whatnot.routes.order_routes.OAuthService")
    @patch("services.whatnot.routes.order_routes.OrderSyncService")
    def test_cancel_order_service_error(self, mock_svc_cls, mock_oauth_cls, client, order_app, sample_owner):
        from services.whatnot.services.order_service import OrderServiceError
        mock_oauth = MagicMock()
        mock_oauth.get_access_token.return_value = "fake_token"
        mock_oauth_cls.return_value = mock_oauth

        mock_svc = MagicMock()
        mock_svc.cancel_order.side_effect = OrderServiceError("Order not found", "not_found", 404)
        mock_svc_cls.return_value = mock_svc

        headers = make_auth_headers(order_app, sample_owner)
        order_id = str(uuid.uuid4())
        resp = client.post(f"/api/v1/whatnot/orders/{order_id}/cancel", headers=headers)
        assert resp.status_code == 404


class TestOrderRouteOAuthErrors:
    """Test OAuthServiceError branches for push_tracking and cancel_order."""

    @patch("services.whatnot.routes.order_routes.OAuthService")
    def test_push_tracking_oauth_error(self, mock_oauth_cls, client, order_app, sample_owner):
        from services.whatnot.services.oauth_service import OAuthServiceError

        mock_oauth = MagicMock()
        mock_oauth.get_access_token.side_effect = OAuthServiceError("Not connected", "not_connected", 400)
        mock_oauth_cls.return_value = mock_oauth

        headers = make_auth_headers(order_app, sample_owner)
        resp = client.post(
            f"/api/v1/whatnot/orders/{uuid.uuid4()}/tracking",
            headers=headers,
            data=json.dumps({"tracking_company": "USPS", "tracking_number": "1Z999"}),
        )
        assert resp.status_code == 400

    @patch("services.whatnot.routes.order_routes.OAuthService")
    @patch("services.whatnot.routes.order_routes.OrderSyncService")
    def test_push_tracking_service_error(self, mock_svc_cls, mock_oauth_cls, client, order_app, sample_owner):
        from services.whatnot.services.order_service import OrderServiceError

        mock_oauth = MagicMock()
        mock_oauth.get_access_token.return_value = "fake_token"
        mock_oauth_cls.return_value = mock_oauth

        mock_svc = MagicMock()
        mock_svc.push_tracking.side_effect = OrderServiceError("Fail", "error", 500)
        mock_svc_cls.return_value = mock_svc

        headers = make_auth_headers(order_app, sample_owner)
        resp = client.post(
            f"/api/v1/whatnot/orders/{uuid.uuid4()}/tracking",
            headers=headers,
            data=json.dumps({"tracking_company": "USPS", "tracking_number": "1Z999"}),
        )
        assert resp.status_code == 500

    @patch("services.whatnot.routes.order_routes.OAuthService")
    def test_cancel_order_oauth_error(self, mock_oauth_cls, client, order_app, sample_owner):
        from services.whatnot.services.oauth_service import OAuthServiceError

        mock_oauth = MagicMock()
        mock_oauth.get_access_token.side_effect = OAuthServiceError("Not connected", "not_connected", 400)
        mock_oauth_cls.return_value = mock_oauth

        headers = make_auth_headers(order_app, sample_owner)
        resp = client.post(f"/api/v1/whatnot/orders/{uuid.uuid4()}/cancel", headers=headers)
        assert resp.status_code == 400
