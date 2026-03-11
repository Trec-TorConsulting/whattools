"""Integration tests for platform admin API routes."""

import json
import uuid

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager

from services.auth.models.models import Account, PlanTier, TeamRole, User
from services.auth.tests.conftest import make_auth_headers
from services.shared.database import get_db
from services.shared.errors import register_error_handlers


@pytest.fixture()
def admin_app(db_session, db_engine):
    """Create a test Flask app wired to admin routes with test DB session."""
    from services.auth.routes.admin_routes import admin_bp

    app = Flask("test")
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    app.config["JWT_SECRET_KEY"] = "test-jwt-secret"
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 900
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = 604800
    app.config["_EVENT_PUBLISHER"] = None
    JWTManager(app)
    register_error_handlers(app)

    app.register_blueprint(admin_bp, url_prefix="/api/v1/admin")

    @app.before_request
    def inject_db():  # type: ignore[no-untyped-def]
        from flask import g
        g.db_session = db_session

    return app


@pytest.fixture()
def admin_client(admin_app):
    return admin_app.test_client()


@pytest.fixture()
def admin_headers(admin_app, platform_admin):
    return make_auth_headers(admin_app, platform_admin)


@pytest.fixture()
def non_admin_headers(admin_app, sample_owner):
    return make_auth_headers(admin_app, sample_owner)


# ── Authorization ───────────────────────────────────────────────


class TestAdminAuth:
    """Verify all admin routes reject non-admin users."""

    def test_metrics_requires_admin(self, admin_client, non_admin_headers):
        resp = admin_client.get("/api/v1/admin/metrics", headers=non_admin_headers)
        assert resp.status_code == 403

    def test_list_accounts_requires_admin(self, admin_client, non_admin_headers):
        resp = admin_client.get("/api/v1/admin/accounts", headers=non_admin_headers)
        assert resp.status_code == 403

    def test_list_users_requires_admin(self, admin_client, non_admin_headers):
        resp = admin_client.get("/api/v1/admin/users", headers=non_admin_headers)
        assert resp.status_code == 403

    def test_audit_logs_requires_admin(self, admin_client, non_admin_headers):
        resp = admin_client.get("/api/v1/admin/audit-logs", headers=non_admin_headers)
        assert resp.status_code == 403

    def test_no_token_returns_401(self, admin_client):
        resp = admin_client.get("/api/v1/admin/metrics")
        assert resp.status_code in (401, 422)

    def test_suspend_requires_admin(self, admin_client, non_admin_headers, sample_account):
        resp = admin_client.post(
            f"/api/v1/admin/accounts/{sample_account.id}/suspend",
            headers=non_admin_headers,
        )
        assert resp.status_code == 403


# ── Metrics ─────────────────────────────────────────────────────


class TestMetricsRoute:
    def test_get_metrics(self, admin_client, admin_headers, sample_account, sample_owner):
        resp = admin_client.get("/api/v1/admin/metrics", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert "total_accounts" in data
        assert "total_users" in data
        assert "mrr" in data


# ── Accounts ────────────────────────────────────────────────────


class TestListAccountsRoute:
    def test_list_accounts(self, admin_client, admin_headers, sample_account):
        resp = admin_client.get("/api/v1/admin/accounts", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data["data"], list)
        assert "pagination" in data["meta"]

    def test_list_accounts_with_search(self, admin_client, admin_headers, sample_account):
        resp = admin_client.get(
            "/api/v1/admin/accounts?search=Test+Business", headers=admin_headers
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert any(a["name"] == "Test Business" for a in data)

    def test_list_accounts_filter_plan(self, admin_client, admin_headers, sample_account):
        resp = admin_client.get(
            "/api/v1/admin/accounts?plan_tier=free", headers=admin_headers
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert all(a["plan_tier"] == "free" for a in data)

    def test_list_accounts_filter_suspended(self, admin_client, admin_headers, sample_account, db_session):
        sample_account.is_suspended = True
        db_session.flush()
        resp = admin_client.get(
            "/api/v1/admin/accounts?is_suspended=true", headers=admin_headers
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert all(a["is_suspended"] for a in data)

    def test_list_accounts_pagination(self, admin_client, admin_headers, sample_account):
        resp = admin_client.get(
            "/api/v1/admin/accounts?page=1&per_page=1", headers=admin_headers
        )
        assert resp.status_code == 200
        meta = resp.get_json()["meta"]["pagination"]
        assert meta["per_page"] == 1
        assert meta["page"] == 1


class TestGetAccountRoute:
    def test_get_account(self, admin_client, admin_headers, sample_account):
        resp = admin_client.get(
            f"/api/v1/admin/accounts/{sample_account.id}", headers=admin_headers
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["name"] == "Test Business"

    def test_get_nonexistent_account(self, admin_client, admin_headers):
        resp = admin_client.get(
            f"/api/v1/admin/accounts/{uuid.uuid4()}", headers=admin_headers
        )
        assert resp.status_code == 404


class TestSuspendAccountRoute:
    def test_suspend_account(self, admin_client, admin_headers, sample_account):
        resp = admin_client.post(
            f"/api/v1/admin/accounts/{sample_account.id}/suspend",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["is_suspended"] is True

    def test_suspend_already_suspended(self, admin_client, admin_headers, sample_account, db_session):
        sample_account.is_suspended = True
        db_session.flush()
        resp = admin_client.post(
            f"/api/v1/admin/accounts/{sample_account.id}/suspend",
            headers=admin_headers,
        )
        assert resp.status_code == 409

    def test_suspend_nonexistent(self, admin_client, admin_headers):
        resp = admin_client.post(
            f"/api/v1/admin/accounts/{uuid.uuid4()}/suspend",
            headers=admin_headers,
        )
        assert resp.status_code == 404


class TestUnsuspendAccountRoute:
    def test_unsuspend_account(self, admin_client, admin_headers, sample_account, db_session):
        sample_account.is_suspended = True
        db_session.flush()
        resp = admin_client.post(
            f"/api/v1/admin/accounts/{sample_account.id}/unsuspend",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["is_suspended"] is False

    def test_unsuspend_not_suspended(self, admin_client, admin_headers, sample_account):
        resp = admin_client.post(
            f"/api/v1/admin/accounts/{sample_account.id}/unsuspend",
            headers=admin_headers,
        )
        assert resp.status_code == 409


class TestUpdatePlanRoute:
    def test_change_plan(self, admin_client, admin_headers, sample_account):
        resp = admin_client.put(
            f"/api/v1/admin/accounts/{sample_account.id}/plan",
            headers=admin_headers,
            json={"plan_tier": "paid"},
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["plan_tier"] == "paid"

    def test_same_plan_conflict(self, admin_client, admin_headers, sample_account):
        resp = admin_client.put(
            f"/api/v1/admin/accounts/{sample_account.id}/plan",
            headers=admin_headers,
            json={"plan_tier": "free"},
        )
        assert resp.status_code == 409

    def test_invalid_plan(self, admin_client, admin_headers, sample_account):
        resp = admin_client.put(
            f"/api/v1/admin/accounts/{sample_account.id}/plan",
            headers=admin_headers,
            json={"plan_tier": "enterprise"},
        )
        assert resp.status_code == 400

    def test_missing_plan_tier(self, admin_client, admin_headers, sample_account):
        resp = admin_client.put(
            f"/api/v1/admin/accounts/{sample_account.id}/plan",
            headers=admin_headers,
            json={},
        )
        assert resp.status_code == 400


# ── Users ───────────────────────────────────────────────────────


class TestListUsersRoute:
    def test_list_users(self, admin_client, admin_headers, sample_owner):
        resp = admin_client.get("/api/v1/admin/users", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data["data"], list)
        assert "pagination" in data["meta"]

    def test_list_users_with_search(self, admin_client, admin_headers, sample_owner):
        resp = admin_client.get(
            "/api/v1/admin/users?search=owner", headers=admin_headers
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert any(u["email"] == "owner@test.com" for u in data)

    def test_list_users_filter_by_account(self, admin_client, admin_headers, sample_owner, sample_account):
        resp = admin_client.get(
            f"/api/v1/admin/users?account_id={sample_account.id}", headers=admin_headers
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert all(u["account_id"] == str(sample_account.id) for u in data)

    def test_list_users_filter_platform_admin(self, admin_client, admin_headers, sample_owner):
        resp = admin_client.get(
            "/api/v1/admin/users?is_platform_admin=true", headers=admin_headers
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert all(u["is_platform_admin"] for u in data)

    def test_list_users_pagination(self, admin_client, admin_headers, sample_owner):
        resp = admin_client.get(
            "/api/v1/admin/users?page=1&per_page=1", headers=admin_headers
        )
        assert resp.status_code == 200
        meta = resp.get_json()["meta"]["pagination"]
        assert meta["per_page"] == 1


class TestGetUserRoute:
    def test_get_user(self, admin_client, admin_headers, sample_owner):
        resp = admin_client.get(
            f"/api/v1/admin/users/{sample_owner.id}", headers=admin_headers
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["email"] == "owner@test.com"

    def test_get_nonexistent_user(self, admin_client, admin_headers):
        resp = admin_client.get(
            f"/api/v1/admin/users/{uuid.uuid4()}", headers=admin_headers
        )
        assert resp.status_code == 404


class TestResetPasswordRoute:
    def test_reset_password(self, admin_client, admin_headers, sample_owner):
        resp = admin_client.post(
            f"/api/v1/admin/users/{sample_owner.id}/reset-password",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert "reset_token" in data
        assert data["user_email"] == "owner@test.com"

    def test_reset_nonexistent_user(self, admin_client, admin_headers):
        resp = admin_client.post(
            f"/api/v1/admin/users/{uuid.uuid4()}/reset-password",
            headers=admin_headers,
        )
        assert resp.status_code == 404


class TestToggleAdminRoute:
    def test_promote_user(self, admin_client, admin_headers, sample_owner):
        resp = admin_client.post(
            f"/api/v1/admin/users/{sample_owner.id}/toggle-admin",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["is_platform_admin"] is True

    def test_cannot_demote_last_admin(self, admin_client, admin_headers, platform_admin):
        resp = admin_client.post(
            f"/api/v1/admin/users/{platform_admin.id}/toggle-admin",
            headers=admin_headers,
        )
        assert resp.status_code == 409

    def test_toggle_nonexistent_user(self, admin_client, admin_headers):
        resp = admin_client.post(
            f"/api/v1/admin/users/{uuid.uuid4()}/toggle-admin",
            headers=admin_headers,
        )
        assert resp.status_code == 404


# ── Impersonation ───────────────────────────────────────────────


class TestImpersonateRoute:
    def test_impersonate_user(self, admin_client, admin_headers, sample_owner):
        resp = admin_client.post(
            f"/api/v1/admin/users/{sample_owner.id}/impersonate",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert "access_token" in data
        assert data["user"]["email"] == "owner@test.com"

    def test_cannot_impersonate_admin(self, admin_client, admin_headers, platform_admin):
        resp = admin_client.post(
            f"/api/v1/admin/users/{platform_admin.id}/impersonate",
            headers=admin_headers,
        )
        assert resp.status_code == 403

    def test_impersonate_nonexistent(self, admin_client, admin_headers):
        resp = admin_client.post(
            f"/api/v1/admin/users/{uuid.uuid4()}/impersonate",
            headers=admin_headers,
        )
        assert resp.status_code == 404

    def test_impersonate_inactive_user(self, admin_client, admin_headers, sample_owner, db_session):
        sample_owner.is_active = False
        db_session.flush()
        resp = admin_client.post(
            f"/api/v1/admin/users/{sample_owner.id}/impersonate",
            headers=admin_headers,
        )
        assert resp.status_code == 400


# ── Audit Logs ──────────────────────────────────────────────────


class TestAuditLogsRoute:
    def test_list_empty_audit_logs(self, admin_client, admin_headers):
        resp = admin_client.get("/api/v1/admin/audit-logs", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"] == []

    def test_audit_logs_after_action(self, admin_client, admin_headers, sample_account):
        # Perform an action that creates an audit log
        admin_client.post(
            f"/api/v1/admin/accounts/{sample_account.id}/suspend",
            headers=admin_headers,
        )
        resp = admin_client.get("/api/v1/admin/audit-logs", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert len(data) >= 1
        assert data[0]["action"] == "account.suspended"

    def test_audit_logs_filter_by_action(self, admin_client, admin_headers, sample_account):
        admin_client.post(
            f"/api/v1/admin/accounts/{sample_account.id}/suspend",
            headers=admin_headers,
        )
        resp = admin_client.get(
            "/api/v1/admin/audit-logs?action=account.suspended",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert len(data) >= 1

    def test_audit_logs_pagination(self, admin_client, admin_headers):
        resp = admin_client.get(
            "/api/v1/admin/audit-logs?page=1&per_page=10", headers=admin_headers
        )
        assert resp.status_code == 200
        meta = resp.get_json()["meta"]["pagination"]
        assert meta["per_page"] == 10
        assert meta["page"] == 1
