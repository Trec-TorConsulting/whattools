"""Integration tests for auth API routes."""

import json

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager

from services.auth.models.models import Account, PlanTier, TeamRole, User
from services.auth.tests.conftest import make_auth_headers
from services.shared.database import get_db
from services.shared.errors import register_error_handlers


@pytest.fixture()
def auth_app(db_session, db_engine):
    """Create a test Flask app wired to the auth routes with test DB session."""
    from services.auth.routes.auth_routes import auth_bp
    from services.auth.routes.account_routes import account_bp
    from services.auth.routes.profile_routes import profile_bp

    app = Flask("test")
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    app.config["JWT_SECRET_KEY"] = "test-jwt-secret"
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 900
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = 604800
    app.config["_EVENT_PUBLISHER"] = None
    JWTManager(app)
    register_error_handlers(app)

    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
    app.register_blueprint(account_bp, url_prefix="/api/v1")
    app.register_blueprint(profile_bp, url_prefix="/api/v1")

    # Wire get_db to return our test session
    @app.before_request
    def inject_db():  # type: ignore[no-untyped-def]
        from flask import g
        g.db_session = db_session

    return app


@pytest.fixture()
def client(auth_app):
    return auth_app.test_client()


class TestRegisterRoute:
    def test_successful_register(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "route-test@test.com",
            "password": "StrongPass1",
            "account_name": "Route Test Biz",
            "name": "Route Test",
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["data"]["email"] == "route-test@test.com"
        assert data["data"]["is_verified"] is False

    def test_register_invalid_password(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "weak@test.com",
            "password": "weak",
            "account_name": "Biz",
        })
        assert resp.status_code == 422

    def test_register_missing_fields(self, client):
        resp = client.post("/api/v1/auth/register", json={})
        assert resp.status_code == 422


class TestLoginRoute:
    def test_successful_login(self, client, sample_owner):
        resp = client.post("/api/v1/auth/login", json={
            "email": "owner@test.com",
            "password": "StrongPass1",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]

    def test_login_invalid_credentials(self, client, sample_owner):
        resp = client.post("/api/v1/auth/login", json={
            "email": "owner@test.com",
            "password": "WrongPassword1",
        })
        assert resp.status_code == 401

    def test_login_missing_fields(self, client):
        resp = client.post("/api/v1/auth/login", json={})
        assert resp.status_code == 422


class TestRefreshRoute:
    def test_successful_refresh(self, client, sample_owner):
        # Login first
        login_resp = client.post("/api/v1/auth/login", json={
            "email": "owner@test.com",
            "password": "StrongPass1",
        })
        tokens = login_resp.get_json()["data"]

        resp = client.post("/api/v1/auth/refresh", json={
            "refresh_token": tokens["refresh_token"],
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert "access_token" in data["data"]

    def test_refresh_invalid_token(self, client):
        resp = client.post("/api/v1/auth/refresh", json={
            "refresh_token": "invalid-token",
        })
        assert resp.status_code == 401


class TestLogoutRoute:
    def test_successful_logout(self, client, auth_app, sample_owner):
        # Login first
        login_resp = client.post("/api/v1/auth/login", json={
            "email": "owner@test.com",
            "password": "StrongPass1",
        })
        tokens = login_resp.get_json()["data"]
        headers = make_auth_headers(auth_app, sample_owner)

        resp = client.post("/api/v1/auth/logout", json={
            "refresh_token": tokens["refresh_token"],
        }, headers=headers)
        assert resp.status_code == 200


class TestPasswordResetRoutes:
    def test_request_reset(self, client, sample_owner):
        resp = client.post("/api/v1/auth/password-reset", json={
            "email": "owner@test.com",
        })
        assert resp.status_code == 200

    def test_request_reset_nonexistent(self, client):
        resp = client.post("/api/v1/auth/password-reset", json={
            "email": "doesnotexist@test.com",
        })
        # Always returns 200 to prevent enumeration
        assert resp.status_code == 200


class TestVerifyEmailRoute:
    def test_verify_invalid_token(self, client):
        resp = client.post("/api/v1/auth/verify-email", json={
            "token": "invalid-token",
        })
        assert resp.status_code == 400


class TestAccountRoutes:
    def test_get_account(self, client, auth_app, sample_owner, sample_account):
        headers = make_auth_headers(auth_app, sample_owner)
        resp = client.get("/api/v1/account", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["name"] == "Test Business"

    def test_update_account(self, client, auth_app, sample_owner, sample_account):
        headers = make_auth_headers(auth_app, sample_owner)
        resp = client.put("/api/v1/account", json={"name": "New Name"}, headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["name"] == "New Name"

    def test_update_account_forbidden_for_member(self, client, auth_app, sample_member, sample_account):
        headers = make_auth_headers(auth_app, sample_member)
        resp = client.put("/api/v1/account", json={"name": "Nope"}, headers=headers)
        assert resp.status_code == 403

    def test_list_members(self, client, auth_app, sample_owner, sample_account):
        headers = make_auth_headers(auth_app, sample_owner)
        resp = client.get("/api/v1/account/members", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data["data"], list)

    def test_invite_member_forbidden_for_member(self, client, auth_app, sample_member, sample_account):
        headers = make_auth_headers(auth_app, sample_member)
        resp = client.post("/api/v1/account/invite", json={
            "email": "invite@test.com",
        }, headers=headers)
        assert resp.status_code == 403


class TestProfileRoutes:
    def test_get_profile(self, client, auth_app, sample_owner):
        headers = make_auth_headers(auth_app, sample_owner)
        resp = client.get("/api/v1/users/me", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["email"] == "owner@test.com"

    def test_update_profile(self, client, auth_app, sample_owner):
        headers = make_auth_headers(auth_app, sample_owner)
        resp = client.put("/api/v1/users/me", json={"name": "Updated Owner"}, headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["name"] == "Updated Owner"

    def test_unauthenticated_access(self, client):
        resp = client.get("/api/v1/users/me")
        assert resp.status_code == 401


class TestSecurityTests:
    """Security-focused tests (auth bypass, IDOR, etc.)."""

    def test_no_auth_header_rejected(self, client):
        resp = client.get("/api/v1/account")
        assert resp.status_code == 401

    def test_invalid_jwt_rejected(self, client):
        resp = client.get("/api/v1/users/me", headers={"Authorization": "Bearer invalid.jwt.token"})
        assert resp.status_code == 422  # JWT decode error

    def test_register_does_not_return_tokens(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "sec-test@test.com",
            "password": "StrongPass1",
            "account_name": "Sec Test",
        })
        data = resp.get_json()
        assert "access_token" not in data.get("data", {})
        assert "refresh_token" not in data.get("data", {})

    def test_password_not_in_response(self, client, auth_app, sample_owner):
        headers = make_auth_headers(auth_app, sample_owner)
        resp = client.get("/api/v1/users/me", headers=headers)
        data = resp.get_json()
        assert "password" not in str(data)
        assert "password_hash" not in str(data)
