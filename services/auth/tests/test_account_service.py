"""Tests for account and team management service layer."""

import pytest
from unittest.mock import MagicMock

from services.auth.models.models import PlanTier, TeamRole, User
from services.auth.services.account_service import AccountService
from services.auth.services.auth_service import AuthServiceError


class TestAccountManagement:
    def test_get_account(self, db_session, app, sample_account, sample_owner):
        with app.app_context():
            svc = AccountService(db_session)
            result = svc.get_account(sample_account.id)
        assert result["name"] == "Test Business"
        assert result["plan_tier"] == PlanTier.FREE
        assert result["member_count"] >= 1

    def test_get_account_not_found(self, db_session, app):
        import uuid
        with app.app_context():
            svc = AccountService(db_session)
            with pytest.raises(AuthServiceError) as exc_info:
                svc.get_account(uuid.uuid4())
            assert exc_info.value.status_code == 404

    def test_update_account(self, db_session, app, sample_account, sample_owner):
        with app.app_context():
            svc = AccountService(db_session)
            result = svc.update_account(sample_account.id, sample_owner.id, name="Updated Name")
        assert result["name"] == "Updated Name"

    def test_delete_account(self, db_session, app, sample_account, sample_owner, mock_event_publisher):
        with app.app_context():
            svc = AccountService(db_session, event_publisher=mock_event_publisher)
            svc.delete_account(sample_account.id, sample_owner.id)
        assert sample_account.deleted_at is not None
        assert not sample_owner.is_active

    def test_delete_account_non_owner(self, db_session, app, sample_account, sample_member):
        with app.app_context():
            svc = AccountService(db_session)
            with pytest.raises(AuthServiceError) as exc_info:
                svc.delete_account(sample_account.id, sample_member.id)
            assert exc_info.value.status_code == 403


class TestTeamManagement:
    def test_list_members(self, db_session, app, sample_account, sample_owner):
        with app.app_context():
            svc = AccountService(db_session)
            members = svc.list_members(sample_account.id)
        assert len(members) >= 1
        assert any(m["email"] == "owner@test.com" for m in members)

    def test_invite_member(self, db_session, app, sample_account, sample_owner, mock_event_publisher):
        with app.app_context():
            svc = AccountService(db_session, event_publisher=mock_event_publisher)
            result = svc.invite_member(
                account_id=sample_account.id,
                actor_id=sample_owner.id,
                email="newinvite@test.com",
                role=TeamRole.MEMBER,
            )
        assert result["email"] == "newinvite@test.com"
        assert result["role"] == TeamRole.MEMBER

    def test_invite_member_permission_denied(self, db_session, app, sample_account, sample_member):
        with app.app_context():
            svc = AccountService(db_session)
            with pytest.raises(AuthServiceError) as exc_info:
                svc.invite_member(
                    account_id=sample_account.id,
                    actor_id=sample_member.id,
                    email="denied@test.com",
                )
            assert exc_info.value.status_code == 403

    def test_invite_member_free_tier_limit(self, db_session, app, sample_account, sample_owner, sample_member):
        """Free tier allows max 2 members. Owner + member = 2, so next invite should fail."""
        with app.app_context():
            svc = AccountService(db_session)
            with pytest.raises(AuthServiceError) as exc_info:
                svc.invite_member(
                    account_id=sample_account.id,
                    actor_id=sample_owner.id,
                    email="over-limit@test.com",
                )
            assert exc_info.value.status_code == 403

    def test_invite_duplicate_existing_member(self, db_session, app, sample_account, sample_owner, sample_member):
        with app.app_context():
            svc = AccountService(db_session)
            with pytest.raises(AuthServiceError) as exc_info:
                svc.invite_member(
                    account_id=sample_account.id,
                    actor_id=sample_owner.id,
                    email="member@test.com",
                )
            # Could be 403 (limit) or 409 (already member) — depends on check order
            assert exc_info.value.status_code in (403, 409)

    def test_update_member_role(self, db_session, app, sample_account, sample_owner, sample_member):
        with app.app_context():
            svc = AccountService(db_session)
            result = svc.update_member_role(
                account_id=sample_account.id,
                actor_id=sample_owner.id,
                member_id=sample_member.id,
                new_role=TeamRole.ADMIN,
            )
        assert result["role"] == TeamRole.ADMIN

    def test_update_role_non_owner(self, db_session, app, sample_account, sample_admin, sample_member):
        with app.app_context():
            svc = AccountService(db_session)
            with pytest.raises(AuthServiceError) as exc_info:
                svc.update_member_role(
                    account_id=sample_account.id,
                    actor_id=sample_admin.id,
                    member_id=sample_member.id,
                    new_role=TeamRole.ADMIN,
                )
            assert exc_info.value.status_code == 403

    def test_update_own_role(self, db_session, app, sample_account, sample_owner):
        with app.app_context():
            svc = AccountService(db_session)
            with pytest.raises(AuthServiceError) as exc_info:
                svc.update_member_role(
                    account_id=sample_account.id,
                    actor_id=sample_owner.id,
                    member_id=sample_owner.id,
                    new_role=TeamRole.MEMBER,
                )
            assert exc_info.value.status_code == 400

    def test_remove_member(self, db_session, app, sample_account, sample_owner, sample_member, mock_event_publisher):
        with app.app_context():
            svc = AccountService(db_session, event_publisher=mock_event_publisher)
            svc.remove_member(
                account_id=sample_account.id,
                actor_id=sample_owner.id,
                member_id=sample_member.id,
            )
        assert not sample_member.is_active

    def test_remove_member_permission_denied(self, db_session, app, sample_account, sample_member, sample_owner):
        with app.app_context():
            svc = AccountService(db_session)
            with pytest.raises(AuthServiceError) as exc_info:
                svc.remove_member(
                    account_id=sample_account.id,
                    actor_id=sample_member.id,
                    member_id=sample_owner.id,
                )
            assert exc_info.value.status_code == 403

    def test_cannot_remove_owner(self, db_session, app, sample_account, sample_admin, sample_owner):
        with app.app_context():
            svc = AccountService(db_session)
            with pytest.raises(AuthServiceError) as exc_info:
                svc.remove_member(
                    account_id=sample_account.id,
                    actor_id=sample_admin.id,
                    member_id=sample_owner.id,
                )
            assert exc_info.value.status_code == 403

    def test_cannot_remove_self(self, db_session, app, sample_account, sample_owner):
        with app.app_context():
            svc = AccountService(db_session)
            with pytest.raises(AuthServiceError) as exc_info:
                svc.remove_member(
                    account_id=sample_account.id,
                    actor_id=sample_owner.id,
                    member_id=sample_owner.id,
                )
            assert exc_info.value.status_code == 400


class TestUserProfile:
    def test_get_profile(self, db_session, app, sample_owner):
        with app.app_context():
            svc = AccountService(db_session)
            result = svc.get_profile(sample_owner.id)
        assert result["email"] == "owner@test.com"
        assert result["role"] == TeamRole.OWNER

    def test_update_profile_name(self, db_session, app, sample_owner, sample_account):
        with app.app_context():
            svc = AccountService(db_session)
            result = svc.update_profile(sample_owner.id, sample_account.id, {"name": "Updated Name"})
        assert result["name"] == "Updated Name"

    def test_update_profile_email(self, db_session, app, sample_owner, sample_account):
        with app.app_context():
            svc = AccountService(db_session)
            result = svc.update_profile(sample_owner.id, sample_account.id, {"email": "newemail@test.com"})
        assert result["email"] == "newemail@test.com"
        assert result["is_verified"] is False  # Requires re-verification

    def test_update_profile_duplicate_email(self, db_session, app, sample_owner, sample_account, sample_member):
        with app.app_context():
            svc = AccountService(db_session)
            with pytest.raises(AuthServiceError) as exc_info:
                svc.update_profile(sample_owner.id, sample_account.id, {"email": "member@test.com"})
            assert exc_info.value.status_code == 409
