"""Integration tests for product routes."""

import json
import uuid
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token

from services.auth.models.models import Account, PlanTier, TeamRole, User
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
def product_app(db_session):
    from services.whatnot.routes.product_routes import product_bp

    app = Flask("test")
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    app.config["JWT_SECRET_KEY"] = "test-jwt-secret"
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 900
    app.config["_EVENT_PUBLISHER"] = None
    JWTManager(app)
    register_error_handlers(app)
    app.register_blueprint(product_bp, url_prefix="/api/v1/whatnot")

    @app.before_request
    def inject_db():
        from flask import g
        g.db_session = db_session

    return app


@pytest.fixture()
def client(product_app):
    return product_app.test_client()


class TestProductPull:
    @patch("services.whatnot.routes.product_routes.OAuthService")
    @patch("services.whatnot.routes.product_routes.ProductService")
    def test_pull_products_success(self, mock_ps_cls, mock_oauth_cls, client, product_app, sample_owner):
        mock_oauth = MagicMock()
        mock_oauth.get_access_token.return_value = "fake_token"
        mock_oauth_cls.return_value = mock_oauth

        mock_svc = MagicMock()
        mock_svc.pull_products.return_value = {"created": 5, "updated": 2, "total": 7}
        mock_ps_cls.return_value = mock_svc

        headers = make_auth_headers(product_app, sample_owner)
        resp = client.post("/api/v1/whatnot/products/pull", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["total"] == 7

    @patch("services.whatnot.routes.product_routes.OAuthService")
    def test_pull_products_not_connected(self, mock_oauth_cls, client, product_app, sample_owner):
        from services.whatnot.services.oauth_service import OAuthServiceError
        mock_oauth = MagicMock()
        mock_oauth.get_access_token.side_effect = OAuthServiceError("Not connected", "not_connected", 400)
        mock_oauth_cls.return_value = mock_oauth

        headers = make_auth_headers(product_app, sample_owner)
        resp = client.post("/api/v1/whatnot/products/pull", headers=headers)
        assert resp.status_code == 400

    def test_pull_products_unauthenticated(self, client):
        resp = client.post("/api/v1/whatnot/products/pull")
        assert resp.status_code == 401


class TestProductPush:
    @patch("services.whatnot.routes.product_routes.OAuthService")
    @patch("services.whatnot.routes.product_routes.ProductService")
    def test_push_product_success(self, mock_ps_cls, mock_oauth_cls, client, product_app, sample_owner):
        mock_oauth = MagicMock()
        mock_oauth.get_access_token.return_value = "fake_token"
        mock_oauth_cls.return_value = mock_oauth

        mock_svc = MagicMock()
        mock_svc.push_product.return_value = {"whatnot_product_id": "prod_123"}
        mock_ps_cls.return_value = mock_svc

        headers = make_auth_headers(product_app, sample_owner)
        resp = client.post(
            "/api/v1/whatnot/products/push",
            headers=headers,
            data=json.dumps({"item_id": str(uuid.uuid4())}),
        )
        assert resp.status_code == 201

    def test_push_product_missing_item_id(self, client, product_app, sample_owner):
        headers = make_auth_headers(product_app, sample_owner)
        resp = client.post(
            "/api/v1/whatnot/products/push",
            headers=headers,
            data=json.dumps({}),
        )
        assert resp.status_code == 422

    @patch("services.whatnot.routes.product_routes.OAuthService")
    @patch("services.whatnot.routes.product_routes.ProductService")
    def test_push_product_service_error(self, mock_ps_cls, mock_oauth_cls, client, product_app, sample_owner):
        from services.whatnot.services.product_service import ProductServiceError
        mock_oauth = MagicMock()
        mock_oauth.get_access_token.return_value = "fake_token"
        mock_oauth_cls.return_value = mock_oauth

        mock_svc = MagicMock()
        mock_svc.push_product.side_effect = ProductServiceError("Item not found", "not_found", 404)
        mock_ps_cls.return_value = mock_svc

        headers = make_auth_headers(product_app, sample_owner)
        resp = client.post(
            "/api/v1/whatnot/products/push",
            headers=headers,
            data=json.dumps({"item_id": str(uuid.uuid4())}),
        )
        assert resp.status_code == 404


class TestProductSync:
    @patch("services.whatnot.routes.product_routes.OAuthService")
    @patch("services.whatnot.routes.product_routes.ProductService")
    def test_sync_product_success(self, mock_ps_cls, mock_oauth_cls, client, product_app, sample_owner):
        mock_oauth = MagicMock()
        mock_oauth.get_access_token.return_value = "fake_token"
        mock_oauth_cls.return_value = mock_oauth

        mock_svc = MagicMock()
        mock_svc.update_product.return_value = {"updated": True}
        mock_ps_cls.return_value = mock_svc

        headers = make_auth_headers(product_app, sample_owner)
        resp = client.post(f"/api/v1/whatnot/products/{uuid.uuid4()}/sync", headers=headers)
        assert resp.status_code == 200


class TestProductUnlink:
    @patch("services.whatnot.routes.product_routes.OAuthService")
    @patch("services.whatnot.routes.product_routes.ProductService")
    def test_unlink_product_success(self, mock_ps_cls, mock_oauth_cls, client, product_app, sample_owner):
        mock_oauth = MagicMock()
        mock_oauth.get_access_token.return_value = "fake_token"
        mock_oauth_cls.return_value = mock_oauth

        mock_svc = MagicMock()
        mock_svc.delete_product.return_value = {"deleted": True}
        mock_ps_cls.return_value = mock_svc

        headers = make_auth_headers(product_app, sample_owner)
        resp = client.post(f"/api/v1/whatnot/products/{uuid.uuid4()}/unlink", headers=headers)
        assert resp.status_code == 200


class TestTaxonomy:
    @patch("services.whatnot.routes.product_routes.OAuthService")
    @patch("services.whatnot.routes.product_routes.ProductService")
    def test_get_taxonomy(self, mock_ps_cls, mock_oauth_cls, client, product_app, sample_owner):
        mock_oauth = MagicMock()
        mock_oauth.get_access_token.return_value = "fake_token"
        mock_oauth_cls.return_value = mock_oauth

        mock_svc = MagicMock()
        mock_svc.get_taxonomy.return_value = [{"id": "node_1", "name": "Trading Cards"}]
        mock_ps_cls.return_value = mock_svc

        headers = make_auth_headers(product_app, sample_owner)
        resp = client.get("/api/v1/whatnot/taxonomy", headers=headers)
        assert resp.status_code == 200

    @patch("services.whatnot.routes.product_routes.OAuthService")
    @patch("services.whatnot.routes.product_routes.ProductService")
    def test_get_taxonomy_node(self, mock_ps_cls, mock_oauth_cls, client, product_app, sample_owner):
        mock_oauth = MagicMock()
        mock_oauth.get_access_token.return_value = "fake_token"
        mock_oauth_cls.return_value = mock_oauth

        mock_svc = MagicMock()
        mock_svc.get_taxonomy_node.return_value = {"id": "node_1", "name": "Cards"}
        mock_ps_cls.return_value = mock_svc

        headers = make_auth_headers(product_app, sample_owner)
        resp = client.get("/api/v1/whatnot/taxonomy/node_1", headers=headers)
        assert resp.status_code == 200

    @patch("services.whatnot.routes.product_routes.OAuthService")
    @patch("services.whatnot.routes.product_routes.ProductService")
    def test_get_taxonomy_attributes(self, mock_ps_cls, mock_oauth_cls, client, product_app, sample_owner):
        mock_oauth = MagicMock()
        mock_oauth.get_access_token.return_value = "fake_token"
        mock_oauth_cls.return_value = mock_oauth

        mock_svc = MagicMock()
        mock_svc.get_taxonomy_attributes.return_value = [{"name": "Condition"}]
        mock_ps_cls.return_value = mock_svc

        headers = make_auth_headers(product_app, sample_owner)
        resp = client.get("/api/v1/whatnot/taxonomy/node_1/attributes", headers=headers)
        assert resp.status_code == 200


class TestProductRouteErrors:
    """Test OAuthServiceError and ProductServiceError branches."""

    @pytest.mark.parametrize("method,path,body", [
        ("post", "/api/v1/whatnot/products/push", {"item_id": str(uuid.uuid4())}),
        ("post", f"/api/v1/whatnot/products/{uuid.uuid4()}/sync", None),
        ("post", f"/api/v1/whatnot/products/{uuid.uuid4()}/unlink", None),
        ("get", "/api/v1/whatnot/taxonomy", None),
        ("get", "/api/v1/whatnot/taxonomy/node_1", None),
        ("get", "/api/v1/whatnot/taxonomy/node_1/attributes", None),
    ])
    @patch("services.whatnot.routes.product_routes.OAuthService")
    def test_oauth_error(self, mock_oauth_cls, method, path, body, client, product_app, sample_owner):
        from services.whatnot.services.oauth_service import OAuthServiceError

        mock_oauth = MagicMock()
        mock_oauth.get_access_token.side_effect = OAuthServiceError("Not connected", "not_connected", 400)
        mock_oauth_cls.return_value = mock_oauth

        headers = make_auth_headers(product_app, sample_owner)
        fn = getattr(client, method)
        kwargs = {"headers": headers}
        if body:
            kwargs["data"] = json.dumps(body)
        resp = fn(path, **kwargs)
        assert resp.status_code == 400

    @pytest.mark.parametrize("method,path,body,svc_method", [
        ("post", "/api/v1/whatnot/products/pull", None, "pull_products"),
        ("post", f"/api/v1/whatnot/products/{uuid.uuid4()}/sync", None, "update_product"),
        ("post", f"/api/v1/whatnot/products/{uuid.uuid4()}/unlink", None, "delete_product"),
    ])
    @patch("services.whatnot.routes.product_routes.OAuthService")
    @patch("services.whatnot.routes.product_routes.ProductService")
    def test_service_error(self, mock_ps_cls, mock_oauth_cls, method, path, body, svc_method, client, product_app, sample_owner):
        from services.whatnot.services.product_service import ProductServiceError

        mock_oauth = MagicMock()
        mock_oauth.get_access_token.return_value = "fake_token"
        mock_oauth_cls.return_value = mock_oauth

        mock_svc = MagicMock()
        getattr(mock_svc, svc_method).side_effect = ProductServiceError("Error", "error", 500)
        mock_ps_cls.return_value = mock_svc

        headers = make_auth_headers(product_app, sample_owner)
        fn = getattr(client, method)
        kwargs = {"headers": headers}
        if body:
            kwargs["data"] = json.dumps(body)
        resp = fn(path, **kwargs)
        assert resp.status_code == 500
