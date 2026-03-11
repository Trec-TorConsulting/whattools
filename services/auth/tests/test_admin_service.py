"""Tests for platform admin service layer."""

import uuid

import pytest
from sqlalchemy.orm import Session

from services.auth.models.models import Account, PlanTier, TeamRole, User
from services.auth.services.admin_service import AdminService, AdminServiceError


class TestListAccounts:
    def test_list_all_accounts(self, db_session, sample_account, platform_admin):
        svc = AdminService(db_session)
        result = svc.list_accounts()
        assert len(result["accounts"]) >= 1
        assert result["pagination"]["total"] >= 1

    def test_list_accounts_with_search(self, db_session, sample_account, platform_admin):
        svc = AdminService(db_session)
        result = svc.list_accounts(search="Test Business")
        assert any(a["name"] == "Test Business" for a in result["accounts"])

    def test_list_accounts_no_search_match(self, db_session, sample_account, platform_admin):
        svc = AdminService(db_session)
        result = svc.list_accounts(search="NonexistentCorp")
        assert len(result["accounts"]) == 0

    def test_list_accounts_filter_plan(self, db_session, sample_account, platform_admin):
        svc = AdminService(db_session)
        result = svc.list_accounts(plan_tier="free")
        assert all(a["plan_tier"] == "free" for a in result["accounts"])

    def test_list_accounts_filter_suspended(self, db_session, sample_account, platform_admin):
        sample_account.is_suspended = True
        db_session.flush()
        svc = AdminService(db_session)
        result = svc.list_accounts(is_suspended=True)
        assert all(a["is_suspended"] for a in result["accounts"])

    def test_list_accounts_filter_not_suspended(self, db_session, sample_account, platform_admin):
        svc = AdminService(db_session)
        result = svc.list_accounts(is_suspended=False)
        assert all(not a["is_suspended"] for a in result["accounts"])

    def test_list_accounts_pagination(self, db_session, sample_account, platform_admin):
        svc = AdminService(db_session)
        result = svc.list_accounts(page=1, per_page=1)
        assert len(result["accounts"]) <= 1
        assert result["pagination"]["per_page"] == 1

    def test_list_accounts_page_two(self, db_session, sample_account, platform_admin_account):
        svc = AdminService(db_session)
        result = svc.list_accounts(page=2, per_page=1)
        assert len(result["accounts"]) <= 1
        assert result["pagination"]["page"] == 2

    def test_list_accounts_includes_user_count(self, db_session, sample_account, sample_owner, platform_admin):
        svc = AdminService(db_session)
        result = svc.list_accounts()
        sample_acct = next(a for a in result["accounts"] if a["id"] == str(sample_account.id))
        assert sample_acct["user_count"] >= 1


class TestGetAccount:
    def test_get_existing_account(self, db_session, sample_account):
        svc = AdminService(db_session)
        result = svc.get_account(sample_account.id)
        assert result["id"] == str(sample_account.id)
        assert result["name"] == "Test Business"
        assert "user_count" in result
        assert "plan_tier" in result

    def test_get_nonexistent_account(self, db_session):
        svc = AdminService(db_session)
        with pytest.raises(AdminServiceError) as exc_info:
            svc.get_account(uuid.uuid4())
        assert exc_info.value.status_code == 404


class TestSuspendAccount:
    def test_suspend_account(self, db_session, sample_account, platform_admin):
        svc = AdminService(db_session)
        result = svc.suspend_account(sample_account.id, admin_id=platform_admin.id)
        assert result["is_suspended"] is True

    def test_suspend_creates_audit_log(self, db_session, sample_account, platform_admin):
        svc = AdminService(db_session)
        svc.suspend_account(sample_account.id, admin_id=platform_admin.id)
        logs = svc.list_audit_logs(action="account.suspended")
        assert len(logs["logs"]) == 1
        assert logs["logs"][0]["target_id"] == str(sample_account.id)

    def test_suspend_already_suspended(self, db_session, sample_account, platform_admin):
        sample_account.is_suspended = True
        db_session.flush()
        svc = AdminService(db_session)
        with pytest.raises(AdminServiceError) as exc_info:
            svc.suspend_account(sample_account.id, admin_id=platform_admin.id)
        assert exc_info.value.status_code == 409

    def test_suspend_nonexistent_account(self, db_session, platform_admin):
        svc = AdminService(db_session)
        with pytest.raises(AdminServiceError) as exc_info:
            svc.suspend_account(uuid.uuid4(), admin_id=platform_admin.id)
        assert exc_info.value.status_code == 404

    def test_suspend_with_ip_address(self, db_session, sample_account, platform_admin):
        svc = AdminService(db_session)
        svc.suspend_account(sample_account.id, admin_id=platform_admin.id, ip_address="10.0.0.1")
        logs = svc.list_audit_logs()
        assert logs["logs"][0]["ip_address"] == "10.0.0.1"


class TestUnsuspendAccount:
    def test_unsuspend_account(self, db_session, sample_account, platform_admin):
        sample_account.is_suspended = True
        db_session.flush()
        svc = AdminService(db_session)
        result = svc.unsuspend_account(sample_account.id, admin_id=platform_admin.id)
        assert result["is_suspended"] is False

    def test_unsuspend_creates_audit_log(self, db_session, sample_account, platform_admin):
        sample_account.is_suspended = True
        db_session.flush()
        svc = AdminService(db_session)
        svc.unsuspend_account(sample_account.id, admin_id=platform_admin.id)
        logs = svc.list_audit_logs(action="account.unsuspended")
        assert len(logs["logs"]) == 1

    def test_unsuspend_not_suspended(self, db_session, sample_account, platform_admin):
        svc = AdminService(db_session)
        with pytest.raises(AdminServiceError) as exc_info:
            svc.unsuspend_account(sample_account.id, admin_id=platform_admin.id)
        assert exc_info.value.status_code == 409

    def test_unsuspend_nonexistent(self, db_session, platform_admin):
        svc = AdminService(db_session)
        with pytest.raises(AdminServiceError) as exc_info:
            svc.unsuspend_account(uuid.uuid4(), admin_id=platform_admin.id)
        assert exc_info.value.status_code == 404


class TestUpdateAccountPlan:
    def test_change_to_paid(self, db_session, sample_account, platform_admin):
        svc = AdminService(db_session)
        result = svc.update_account_plan(
            sample_account.id, PlanTier.PAID, admin_id=platform_admin.id
        )
        assert result["plan_tier"] == "paid"

    def test_change_to_free(self, db_session, platform_admin_account, platform_admin):
        svc = AdminService(db_session)
        result = svc.update_account_plan(
            platform_admin_account.id, PlanTier.FREE, admin_id=platform_admin.id
        )
        assert result["plan_tier"] == "free"

    def test_creates_audit_log_with_changes(self, db_session, sample_account, platform_admin):
        svc = AdminService(db_session)
        svc.update_account_plan(sample_account.id, PlanTier.PAID, admin_id=platform_admin.id)
        logs = svc.list_audit_logs(action="account.plan_changed")
        assert len(logs["logs"]) == 1
        assert logs["logs"][0]["changes"]["plan_tier"]["old"] == "free"
        assert logs["logs"][0]["changes"]["plan_tier"]["new"] == "paid"

    def test_change_to_same_plan(self, db_session, sample_account, platform_admin):
        svc = AdminService(db_session)
        with pytest.raises(AdminServiceError) as exc_info:
            svc.update_account_plan(
                sample_account.id, PlanTier.FREE, admin_id=platform_admin.id
            )
        assert exc_info.value.status_code == 409

    def test_invalid_plan_tier(self, db_session, sample_account, platform_admin):
        svc = AdminService(db_session)
        with pytest.raises(AdminServiceError) as exc_info:
            svc.update_account_plan(
                sample_account.id, "enterprise", admin_id=platform_admin.id
            )
        assert exc_info.value.status_code == 400

    def test_nonexistent_account(self, db_session, platform_admin):
        svc = AdminService(db_session)
        with pytest.raises(AdminServiceError) as exc_info:
            svc.update_account_plan(uuid.uuid4(), PlanTier.PAID, admin_id=platform_admin.id)
        assert exc_info.value.status_code == 404


class TestListUsers:
    def test_list_all_users(self, db_session, sample_owner, platform_admin):
        svc = AdminService(db_session)
        result = svc.list_users()
        assert len(result["users"]) >= 2
        assert result["pagination"]["total"] >= 2

    def test_list_users_with_search_email(self, db_session, sample_owner, platform_admin):
        svc = AdminService(db_session)
        result = svc.list_users(search="owner@test.com")
        assert any(u["email"] == "owner@test.com" for u in result["users"])

    def test_list_users_with_search_name(self, db_session, sample_owner, platform_admin):
        svc = AdminService(db_session)
        result = svc.list_users(search="Test Owner")
        assert any(u["name"] == "Test Owner" for u in result["users"])

    def test_list_users_no_search_match(self, db_session, sample_owner, platform_admin):
        svc = AdminService(db_session)
        result = svc.list_users(search="nonexistent@nowhere.com")
        assert len(result["users"]) == 0

    def test_list_users_filter_by_account(self, db_session, sample_owner, sample_account, platform_admin):
        svc = AdminService(db_session)
        result = svc.list_users(account_id=sample_account.id)
        assert all(u["account_id"] == str(sample_account.id) for u in result["users"])

    def test_list_users_filter_platform_admin(self, db_session, sample_owner, platform_admin):
        svc = AdminService(db_session)
        result = svc.list_users(is_platform_admin=True)
        assert all(u["is_platform_admin"] for u in result["users"])

    def test_list_users_filter_not_platform_admin(self, db_session, sample_owner, platform_admin):
        svc = AdminService(db_session)
        result = svc.list_users(is_platform_admin=False)
        assert all(not u["is_platform_admin"] for u in result["users"])

    def test_list_users_pagination(self, db_session, sample_owner, platform_admin):
        svc = AdminService(db_session)
        result = svc.list_users(page=1, per_page=1)
        assert len(result["users"]) <= 1
        assert result["pagination"]["per_page"] == 1


class TestGetUser:
    def test_get_existing_user(self, db_session, sample_owner):
        svc = AdminService(db_session)
        result = svc.get_user(sample_owner.id)
        assert result["email"] == "owner@test.com"
        assert result["name"] == "Test Owner"
        assert result["role"] == "owner"
        assert "is_platform_admin" in result

    def test_get_nonexistent_user(self, db_session):
        svc = AdminService(db_session)
        with pytest.raises(AdminServiceError) as exc_info:
            svc.get_user(uuid.uuid4())
        assert exc_info.value.status_code == 404


class TestResetUserPassword:
    def test_reset_password(self, db_session, sample_owner, platform_admin):
        svc = AdminService(db_session)
        result = svc.reset_user_password(sample_owner.id, admin_id=platform_admin.id)
        assert "reset_token" in result
        assert "expires_at" in result
        assert result["user_email"] == "owner@test.com"

    def test_reset_password_creates_audit_log(self, db_session, sample_owner, platform_admin):
        svc = AdminService(db_session)
        svc.reset_user_password(sample_owner.id, admin_id=platform_admin.id)
        logs = svc.list_audit_logs(action="user.password_reset_initiated")
        assert len(logs["logs"]) == 1

    def test_reset_nonexistent_user(self, db_session, platform_admin):
        svc = AdminService(db_session)
        with pytest.raises(AdminServiceError) as exc_info:
            svc.reset_user_password(uuid.uuid4(), admin_id=platform_admin.id)
        assert exc_info.value.status_code == 404


class TestTogglePlatformAdmin:
    def test_promote_user(self, db_session, sample_owner, platform_admin):
        svc = AdminService(db_session)
        result = svc.toggle_platform_admin(sample_owner.id, admin_id=platform_admin.id)
        assert result["is_platform_admin"] is True

    def test_promote_creates_audit_log(self, db_session, sample_owner, platform_admin):
        svc = AdminService(db_session)
        svc.toggle_platform_admin(sample_owner.id, admin_id=platform_admin.id)
        logs = svc.list_audit_logs(action="user.promoted_to_admin")
        assert len(logs["logs"]) == 1

    def test_demote_admin(self, db_session, sample_owner, platform_admin):
        # First promote so there are 2 admins
        sample_owner.is_platform_admin = True
        db_session.flush()
        svc = AdminService(db_session)
        result = svc.toggle_platform_admin(sample_owner.id, admin_id=platform_admin.id)
        assert result["is_platform_admin"] is False

    def test_demote_creates_audit_log(self, db_session, sample_owner, platform_admin):
        sample_owner.is_platform_admin = True
        db_session.flush()
        svc = AdminService(db_session)
        svc.toggle_platform_admin(sample_owner.id, admin_id=platform_admin.id)
        logs = svc.list_audit_logs(action="user.demoted_from_admin")
        assert len(logs["logs"]) == 1

    def test_cannot_demote_last_admin(self, db_session, platform_admin):
        svc = AdminService(db_session)
        with pytest.raises(AdminServiceError) as exc_info:
            svc.toggle_platform_admin(platform_admin.id, admin_id=platform_admin.id)
        assert exc_info.value.status_code == 409
        assert "last platform admin" in str(exc_info.value)

    def test_toggle_nonexistent_user(self, db_session, platform_admin):
        svc = AdminService(db_session)
        with pytest.raises(AdminServiceError) as exc_info:
            svc.toggle_platform_admin(uuid.uuid4(), admin_id=platform_admin.id)
        assert exc_info.value.status_code == 404


class TestImpersonateUser:
    def test_impersonate_user(self, db_session, app, sample_owner, platform_admin):
        with app.app_context():
            svc = AdminService(db_session)
            result = svc.impersonate_user(sample_owner.id, admin_id=platform_admin.id)
        assert "access_token" in result
        assert result["token_type"] == "bearer"
        assert result["user"]["email"] == "owner@test.com"

    def test_impersonate_creates_audit_log(self, db_session, app, sample_owner, platform_admin):
        with app.app_context():
            svc = AdminService(db_session)
            svc.impersonate_user(sample_owner.id, admin_id=platform_admin.id)
        logs = svc.list_audit_logs(action="user.impersonated")
        assert len(logs["logs"]) == 1

    def test_cannot_impersonate_platform_admin(self, db_session, app, platform_admin):
        with app.app_context():
            svc = AdminService(db_session)
            with pytest.raises(AdminServiceError) as exc_info:
                svc.impersonate_user(platform_admin.id, admin_id=platform_admin.id)
            assert exc_info.value.status_code == 403

    def test_cannot_impersonate_inactive(self, db_session, app, sample_owner, platform_admin):
        sample_owner.is_active = False
        db_session.flush()
        with app.app_context():
            svc = AdminService(db_session)
            with pytest.raises(AdminServiceError) as exc_info:
                svc.impersonate_user(sample_owner.id, admin_id=platform_admin.id)
            assert exc_info.value.status_code == 400

    def test_impersonate_nonexistent(self, db_session, app, platform_admin):
        with app.app_context():
            svc = AdminService(db_session)
            with pytest.raises(AdminServiceError) as exc_info:
                svc.impersonate_user(uuid.uuid4(), admin_id=platform_admin.id)
            assert exc_info.value.status_code == 404


class TestPlatformMetrics:
    def test_get_metrics_structure(self, db_session, sample_account, sample_owner, platform_admin):
        svc = AdminService(db_session)
        result = svc.get_platform_metrics()
        assert "total_accounts" in result
        assert "active_accounts" in result
        assert "suspended_accounts" in result
        assert "total_users" in result
        assert "active_users" in result
        assert "free_accounts" in result
        assert "paid_accounts" in result
        assert "mrr" in result
        assert "recent_signups" in result

    def test_get_metrics_counts(self, db_session, sample_account, sample_owner, platform_admin):
        svc = AdminService(db_session)
        result = svc.get_platform_metrics()
        assert result["total_accounts"] >= 2  # sample + platform_admin
        assert result["total_users"] >= 2  # sample_owner + platform_admin
        assert result["active_users"] >= 2

    def test_mrr_calculation(self, db_session, platform_admin_account, platform_admin, sample_account):
        svc = AdminService(db_session)
        result = svc.get_platform_metrics()
        assert result["paid_accounts"] >= 1
        assert result["mrr"] >= 29.99

    def test_suspended_accounts_count(self, db_session, sample_account, sample_owner, platform_admin):
        sample_account.is_suspended = True
        db_session.flush()
        svc = AdminService(db_session)
        result = svc.get_platform_metrics()
        assert result["suspended_accounts"] >= 1

    def test_free_vs_paid_adds_up(self, db_session, sample_account, sample_owner, platform_admin):
        svc = AdminService(db_session)
        result = svc.get_platform_metrics()
        assert result["free_accounts"] + result["paid_accounts"] == result["total_accounts"]


class TestAuditLogs:
    def test_list_audit_logs_empty(self, db_session):
        svc = AdminService(db_session)
        result = svc.list_audit_logs()
        assert result["logs"] == []
        assert result["pagination"]["total"] == 0

    def test_audit_logs_created_on_suspend(self, db_session, sample_account, platform_admin):
        svc = AdminService(db_session)
        svc.suspend_account(sample_account.id, admin_id=platform_admin.id)
        result = svc.list_audit_logs()
        assert len(result["logs"]) == 1
        assert result["logs"][0]["action"] == "account.suspended"
        assert result["logs"][0]["admin_id"] == str(platform_admin.id)
        assert result["logs"][0]["target_type"] == "account"

    def test_audit_logs_filter_by_action(self, db_session, sample_account, platform_admin):
        svc = AdminService(db_session)
        svc.suspend_account(sample_account.id, admin_id=platform_admin.id)
        result = svc.list_audit_logs(action="account.suspended")
        assert len(result["logs"]) == 1
        result = svc.list_audit_logs(action="nonexistent.action")
        assert len(result["logs"]) == 0

    def test_audit_logs_filter_by_admin_id(self, db_session, sample_account, platform_admin):
        svc = AdminService(db_session)
        svc.suspend_account(sample_account.id, admin_id=platform_admin.id)
        result = svc.list_audit_logs(admin_id=platform_admin.id)
        assert len(result["logs"]) == 1
        result = svc.list_audit_logs(admin_id=uuid.uuid4())
        assert len(result["logs"]) == 0

    def test_audit_logs_pagination(self, db_session, sample_account, platform_admin):
        svc = AdminService(db_session)
        # Create multiple logs
        svc.suspend_account(sample_account.id, admin_id=platform_admin.id)
        svc.unsuspend_account(sample_account.id, admin_id=platform_admin.id)
        result = svc.list_audit_logs(page=1, per_page=1)
        assert len(result["logs"]) == 1
        assert result["pagination"]["total"] == 2
        assert result["pagination"]["pages"] == 2

    def test_audit_log_entry_fields(self, db_session, sample_account, platform_admin):
        svc = AdminService(db_session)
        svc.suspend_account(sample_account.id, admin_id=platform_admin.id)
        result = svc.list_audit_logs()
        log = result["logs"][0]
        assert "id" in log
        assert "admin_id" in log
        assert "action" in log
        assert "target_type" in log
        assert "target_id" in log
        assert "description" in log
        assert "timestamp" in log
