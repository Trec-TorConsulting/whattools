"""Tests for auth models: Account, User, RefreshToken, TeamInvite."""

from datetime import datetime, timedelta, timezone

from services.auth.models.models import (
    Account,
    PlanTier,
    RefreshToken,
    TeamInvite,
    TeamRole,
    User,
)


class TestAccount:
    def test_create_account(self, db_session):
        account = Account(name="My Business", plan_tier=PlanTier.FREE)
        db_session.add(account)
        db_session.flush()
        assert account.id is not None
        assert account.name == "My Business"
        assert account.plan_tier == PlanTier.FREE

    def test_free_tier_limits(self):
        account = Account(name="Free", plan_tier=PlanTier.FREE)
        assert account.team_member_limit == 2
        assert account.inventory_item_limit == 50

    def test_paid_tier_limits(self):
        account = Account(name="Paid", plan_tier=PlanTier.PAID)
        assert account.team_member_limit == 100
        assert account.inventory_item_limit == -1

    def test_soft_delete(self, db_session):
        account = Account(name="To Delete", plan_tier=PlanTier.FREE)
        db_session.add(account)
        db_session.flush()
        assert account.deleted_at is None
        account.deleted_at = datetime.now(timezone.utc)
        db_session.flush()
        assert account.deleted_at is not None


class TestUser:
    def test_create_user(self, db_session, sample_account):
        user = User(
            account_id=sample_account.id,
            email="new@test.com",
            password_hash="",
            name="New User",
            role=TeamRole.MEMBER,
        )
        user.set_password("StrongPass1")
        db_session.add(user)
        db_session.flush()
        assert user.id is not None
        assert user.email == "new@test.com"
        assert user.role == TeamRole.MEMBER

    def test_password_hashing(self, sample_owner):
        assert sample_owner.check_password("StrongPass1")
        assert not sample_owner.check_password("WrongPassword1")

    def test_account_lockout(self, sample_owner):
        assert not sample_owner.is_locked
        for _ in range(4):
            locked = sample_owner.increment_failed_login()
            assert not locked
        locked = sample_owner.increment_failed_login()
        assert locked
        assert sample_owner.is_locked
        assert sample_owner.failed_login_attempts == 5

    def test_reset_failed_logins(self, sample_owner):
        sample_owner.increment_failed_login()
        sample_owner.increment_failed_login()
        assert sample_owner.failed_login_attempts == 2
        sample_owner.reset_failed_logins()
        assert sample_owner.failed_login_attempts == 0
        assert sample_owner.locked_until is None

    def test_lockout_expiry(self, sample_owner):
        sample_owner.locked_until = datetime.now(timezone.utc) - timedelta(minutes=1)
        assert not sample_owner.is_locked

    def test_user_not_verified_by_default(self, db_session, sample_account):
        user = User(
            account_id=sample_account.id,
            email="unverified@test.com",
            password_hash="hash",
        )
        assert not user.is_verified


class TestRefreshToken:
    def test_create_refresh_token(self, db_session, sample_owner, sample_account):
        token = RefreshToken(
            user_id=sample_owner.id,
            account_id=sample_account.id,
            token_hash="abc123hash",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db_session.add(token)
        db_session.flush()
        assert token.id is not None
        assert token.is_valid

    def test_expired_token(self, sample_owner, sample_account):
        token = RefreshToken(
            user_id=sample_owner.id,
            account_id=sample_account.id,
            token_hash="expired_hash",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        assert token.is_expired
        assert not token.is_valid

    def test_revoked_token(self, sample_owner, sample_account):
        token = RefreshToken(
            user_id=sample_owner.id,
            account_id=sample_account.id,
            token_hash="revoked_hash",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            is_revoked=True,
        )
        assert not token.is_valid


class TestTeamInvite:
    def test_create_invite(self, db_session, sample_account, sample_owner):
        invite = TeamInvite(
            account_id=sample_account.id,
            email="invited@test.com",
            role=TeamRole.MEMBER,
            invited_by=sample_owner.id,
            token="test-invite-token",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db_session.add(invite)
        db_session.flush()
        assert invite.id is not None
        assert invite.is_valid

    def test_expired_invite(self, sample_account, sample_owner):
        invite = TeamInvite(
            account_id=sample_account.id,
            email="expired@test.com",
            role=TeamRole.MEMBER,
            invited_by=sample_owner.id,
            token="expired-invite-token",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        assert invite.is_expired
        assert not invite.is_valid

    def test_accepted_invite(self, sample_account, sample_owner):
        invite = TeamInvite(
            account_id=sample_account.id,
            email="accepted@test.com",
            role=TeamRole.MEMBER,
            invited_by=sample_owner.id,
            token="accepted-invite-token",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            is_accepted=True,
        )
        assert not invite.is_valid
