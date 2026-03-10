"""Integration tests for listing routes."""

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
def listing_app(db_session):
    from services.whatnot.routes.listing_routes import listing_bp

    app = Flask("test")
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    app.config["JWT_SECRET_KEY"] = "test-jwt-secret"
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 900
    app.config["_EVENT_PUBLISHER"] = None
    JWTManager(app)
    register_error_handlers(app)
    app.register_blueprint(listing_bp, url_prefix="/api/v1/whatnot/listings")

    @app.before_request
    def inject_db():
        from flask import g
        g.db_session = db_session

    return app


@pytest.fixture()
def client(listing_app):
    return listing_app.test_client()


def _mock_oauth_and_service(mock_svc_cls, mock_oauth_cls):
    mock_oauth = MagicMock()
    mock_oauth.get_access_token.return_value = "fake_token"
    mock_oauth_cls.return_value = mock_oauth
    mock_svc = MagicMock()
    mock_svc_cls.return_value = mock_svc
    return mock_svc


class TestListListings:
    @patch("services.whatnot.routes.listing_routes.OAuthService")
    @patch("services.whatnot.routes.listing_routes.ListingService")
    def test_list_success(self, mock_svc_cls, mock_oauth_cls, client, listing_app, sample_owner):
        mock_svc = _mock_oauth_and_service(mock_svc_cls, mock_oauth_cls)
        mock_svc.list_listings.return_value = {"listings": [], "has_next": False}

        headers = make_auth_headers(listing_app, sample_owner)
        resp = client.get("/api/v1/whatnot/listings", headers=headers)
        assert resp.status_code == 200

    def test_list_unauthenticated(self, client):
        resp = client.get("/api/v1/whatnot/listings")
        assert resp.status_code == 401


class TestGetListing:
    @patch("services.whatnot.routes.listing_routes.OAuthService")
    @patch("services.whatnot.routes.listing_routes.ListingService")
    def test_get_success(self, mock_svc_cls, mock_oauth_cls, client, listing_app, sample_owner):
        mock_svc = _mock_oauth_and_service(mock_svc_cls, mock_oauth_cls)
        mock_svc.get_listing.return_value = {"id": "lst_1", "title": "Test"}

        headers = make_auth_headers(listing_app, sample_owner)
        resp = client.get("/api/v1/whatnot/listings/lst_1", headers=headers)
        assert resp.status_code == 200

    @patch("services.whatnot.routes.listing_routes.OAuthService")
    @patch("services.whatnot.routes.listing_routes.ListingService")
    def test_get_service_error(self, mock_svc_cls, mock_oauth_cls, client, listing_app, sample_owner):
        from services.whatnot.services.listing_service import ListingServiceError
        mock_svc = _mock_oauth_and_service(mock_svc_cls, mock_oauth_cls)
        mock_svc.get_listing.side_effect = ListingServiceError("Not found", "not_found", 404)

        headers = make_auth_headers(listing_app, sample_owner)
        resp = client.get("/api/v1/whatnot/listings/lst_999", headers=headers)
        assert resp.status_code == 404


class TestUpdateListing:
    @patch("services.whatnot.routes.listing_routes.OAuthService")
    @patch("services.whatnot.routes.listing_routes.ListingService")
    def test_update_success(self, mock_svc_cls, mock_oauth_cls, client, listing_app, sample_owner):
        mock_svc = _mock_oauth_and_service(mock_svc_cls, mock_oauth_cls)
        mock_svc.update_listing.return_value = {"id": "lst_1", "title": "Updated"}

        headers = make_auth_headers(listing_app, sample_owner)
        resp = client.put(
            "/api/v1/whatnot/listings/lst_1",
            headers=headers,
            data=json.dumps({"title": "Updated"}),
        )
        assert resp.status_code == 200


class TestDeleteListing:
    @patch("services.whatnot.routes.listing_routes.OAuthService")
    @patch("services.whatnot.routes.listing_routes.ListingService")
    def test_delete_success(self, mock_svc_cls, mock_oauth_cls, client, listing_app, sample_owner):
        mock_svc = _mock_oauth_and_service(mock_svc_cls, mock_oauth_cls)
        mock_svc.delete_listing.return_value = {"deleted": True}

        headers = make_auth_headers(listing_app, sample_owner)
        resp = client.delete("/api/v1/whatnot/listings/lst_1", headers=headers)
        assert resp.status_code == 200


class TestPublishListing:
    @patch("services.whatnot.routes.listing_routes.OAuthService")
    @patch("services.whatnot.routes.listing_routes.ListingService")
    def test_publish_success(self, mock_svc_cls, mock_oauth_cls, client, listing_app, sample_owner):
        mock_svc = _mock_oauth_and_service(mock_svc_cls, mock_oauth_cls)
        mock_svc.publish.return_value = {"status": "published"}

        headers = make_auth_headers(listing_app, sample_owner)
        resp = client.post("/api/v1/whatnot/listings/lst_1/publish", headers=headers)
        assert resp.status_code == 200


class TestUnpublishListing:
    @patch("services.whatnot.routes.listing_routes.OAuthService")
    @patch("services.whatnot.routes.listing_routes.ListingService")
    def test_unpublish_success(self, mock_svc_cls, mock_oauth_cls, client, listing_app, sample_owner):
        mock_svc = _mock_oauth_and_service(mock_svc_cls, mock_oauth_cls)
        mock_svc.unpublish.return_value = {"status": "unpublished"}

        headers = make_auth_headers(listing_app, sample_owner)
        resp = client.post("/api/v1/whatnot/listings/lst_1/unpublish", headers=headers)
        assert resp.status_code == 200


class TestAssignToLivestream:
    @patch("services.whatnot.routes.listing_routes.OAuthService")
    @patch("services.whatnot.routes.listing_routes.ListingService")
    def test_assign_success(self, mock_svc_cls, mock_oauth_cls, client, listing_app, sample_owner):
        mock_svc = _mock_oauth_and_service(mock_svc_cls, mock_oauth_cls)
        mock_svc.assign_to_livestream.return_value = {"assigned": True}

        headers = make_auth_headers(listing_app, sample_owner)
        resp = client.post(
            "/api/v1/whatnot/listings/lst_1/assign-livestream",
            headers=headers,
            data=json.dumps({"livestream_id": "ls_1"}),
        )
        assert resp.status_code == 200

    def test_assign_missing_livestream_id(self, client, listing_app, sample_owner):
        headers = make_auth_headers(listing_app, sample_owner)
        resp = client.post(
            "/api/v1/whatnot/listings/lst_1/assign-livestream",
            headers=headers,
            data=json.dumps({}),
        )
        assert resp.status_code == 422


class TestRemoveFromLivestream:
    @patch("services.whatnot.routes.listing_routes.OAuthService")
    @patch("services.whatnot.routes.listing_routes.ListingService")
    def test_remove_success(self, mock_svc_cls, mock_oauth_cls, client, listing_app, sample_owner):
        mock_svc = _mock_oauth_and_service(mock_svc_cls, mock_oauth_cls)
        mock_svc.remove_from_livestream.return_value = {"removed": True}

        headers = make_auth_headers(listing_app, sample_owner)
        resp = client.post(
            "/api/v1/whatnot/listings/lst_1/remove-livestream",
            headers=headers,
            data=json.dumps({"livestream_id": "ls_1"}),
        )
        assert resp.status_code == 200

    def test_remove_missing_livestream_id(self, client, listing_app, sample_owner):
        headers = make_auth_headers(listing_app, sample_owner)
        resp = client.post(
            "/api/v1/whatnot/listings/lst_1/remove-livestream",
            headers=headers,
            data=json.dumps({}),
        )
        assert resp.status_code == 422


class TestAdjustQuantity:
    @patch("services.whatnot.routes.listing_routes.OAuthService")
    @patch("services.whatnot.routes.listing_routes.ListingService")
    def test_adjust_success(self, mock_svc_cls, mock_oauth_cls, client, listing_app, sample_owner):
        mock_svc = _mock_oauth_and_service(mock_svc_cls, mock_oauth_cls)
        mock_svc.adjust_quantity.return_value = {"new_quantity": 15}

        headers = make_auth_headers(listing_app, sample_owner)
        resp = client.post(
            "/api/v1/whatnot/listings/lst_1/adjust-quantity",
            headers=headers,
            data=json.dumps({"quantity_delta": 5}),
        )
        assert resp.status_code == 200

    def test_adjust_missing_delta(self, client, listing_app, sample_owner):
        headers = make_auth_headers(listing_app, sample_owner)
        resp = client.post(
            "/api/v1/whatnot/listings/lst_1/adjust-quantity",
            headers=headers,
            data=json.dumps({}),
        )
        assert resp.status_code == 422


class TestListingRouteOAuthErrors:
    """Test OAuthServiceError branches for all listing endpoints."""

    @pytest.mark.parametrize("method,path,body", [
        ("get", "/api/v1/whatnot/listings", None),
        ("get", "/api/v1/whatnot/listings/lst_1", None),
        ("put", "/api/v1/whatnot/listings/lst_1", {"title": "X"}),
        ("delete", "/api/v1/whatnot/listings/lst_1", None),
        ("post", "/api/v1/whatnot/listings/lst_1/publish", None),
        ("post", "/api/v1/whatnot/listings/lst_1/unpublish", None),
        ("post", "/api/v1/whatnot/listings/lst_1/assign-livestream", {"livestream_id": "ls_1"}),
        ("post", "/api/v1/whatnot/listings/lst_1/remove-livestream", {"livestream_id": "ls_1"}),
        ("post", "/api/v1/whatnot/listings/lst_1/adjust-quantity", {"quantity_delta": 1}),
    ])
    @patch("services.whatnot.routes.listing_routes.OAuthService")
    def test_oauth_error(self, mock_oauth_cls, method, path, body, client, listing_app, sample_owner):
        from services.whatnot.services.oauth_service import OAuthServiceError

        mock_oauth = MagicMock()
        mock_oauth.get_access_token.side_effect = OAuthServiceError("Not connected", "not_connected", 400)
        mock_oauth_cls.return_value = mock_oauth

        headers = make_auth_headers(listing_app, sample_owner)
        fn = getattr(client, method)
        kwargs = {"headers": headers}
        if body:
            kwargs["data"] = json.dumps(body)
        resp = fn(path, **kwargs)
        assert resp.status_code == 400


class TestListingRouteServiceErrors:
    """Test ListingServiceError branches for all listing endpoints."""

    @pytest.mark.parametrize("method,path,body,svc_method", [
        ("get", "/api/v1/whatnot/listings", None, "list_listings"),
        ("put", "/api/v1/whatnot/listings/lst_1", {"title": "X"}, "update_listing"),
        ("delete", "/api/v1/whatnot/listings/lst_1", None, "delete_listing"),
        ("post", "/api/v1/whatnot/listings/lst_1/publish", None, "publish"),
        ("post", "/api/v1/whatnot/listings/lst_1/unpublish", None, "unpublish"),
        ("post", "/api/v1/whatnot/listings/lst_1/assign-livestream", {"livestream_id": "ls_1"}, "assign_to_livestream"),
        ("post", "/api/v1/whatnot/listings/lst_1/remove-livestream", {"livestream_id": "ls_1"}, "remove_from_livestream"),
        ("post", "/api/v1/whatnot/listings/lst_1/adjust-quantity", {"quantity_delta": 1}, "adjust_quantity"),
    ])
    @patch("services.whatnot.routes.listing_routes.OAuthService")
    @patch("services.whatnot.routes.listing_routes.ListingService")
    def test_service_error(self, mock_svc_cls, mock_oauth_cls, method, path, body, svc_method, client, listing_app, sample_owner):
        from services.whatnot.services.listing_service import ListingServiceError

        mock_svc = _mock_oauth_and_service(mock_svc_cls, mock_oauth_cls)
        getattr(mock_svc, svc_method).side_effect = ListingServiceError("Failed", "service_error", 500)

        headers = make_auth_headers(listing_app, sample_owner)
        fn = getattr(client, method)
        kwargs = {"headers": headers}
        if body:
            kwargs["data"] = json.dumps(body)
        resp = fn(path, **kwargs)
        assert resp.status_code == 500
