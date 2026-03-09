"""Tests for auth repositories."""

import uuid
from datetime import datetime, timedelta, timezone

from services.auth.models.models import (
    Account,
    PlanTier,
    RefreshToken,
    TeamInvite,
    TeamRole,
    User,
)
from services.auth.repositories.auth_repository import (
    AccountRepository,
    RefreshTokenRepository,
    TeamInviteRepository,
    UserRepository,
)


class TestUserRepository:
    def test_get_by_email(self, db_session, sample_owner):
        repo = UserRepository(db_session)
        user = repo.get_by_email("owner@test.com")
        assert user is not None
        assert user.id == sample_owner.id

    def test_get_by_email_not_found(self, db_session):
        repo = UserRepository(db_session)
        assert repo.get_by_email("nonexistent@test.com") is None

    def test_get_by_id(self, db_session, sample_owner):
        repo = UserRepository(db_session)
        user = repo.get_by_id(sample_owner.id)
        assert user is not None
        assert user.email == "owner@test.com"

    def test_get_by_verification_token(self, db_session, sample_account):
        user = User(
            account_id=sample_account.id,
            email="verify@test.com",
            password_hash="hash",
            role=TeamRole.MEMBER,
        )
        user.verification_token = "test-verify-token"
        db_session.add(user)
        db_session.flush()

        repo = UserRepository(db_session)
        found = repo.get_by_verification_token("test-verify-token")
        assert found is not None
        assert found.email == "verify@test.com"

    def test_get_by_reset_token(self, db_session, sample_account):
        user = User(
            account_id=sample_account.id,
            email="reset@test.com",
            password_hash="hash",
            role=TeamRole.MEMBER,
        )
        user.reset_token = "test-reset-token"
        db_session.add(user)
        db_session.flush()

        repo = UserRepository(db_session)
        found = repo.get_by_reset_token("test-reset-token")
        assert found is not None
        assert found.email == "reset@test.com"

    def test_list_by_account(self, db_session, sample_account, sample_owner):
        repo = UserRepository(db_session)
        users = repo.list_by_account(sample_account.id)
        assert len(users) >= 1
        assert any(u.id == sample_owner.id for u in users)

    def test_list_by_account_excludes_inactive(self, db_session, sample_account):
        user = User(
            account_id=sample_account.id,
            email="inactive@test.com",
            password_hash="hash",
            role=TeamRole.MEMBER,
            is_active=False,
        )
        db_session.add(user)
        db_session.flush()

        repo = UserRepository(db_session)
        users = repo.list_by_account(sample_account.id)
        assert not any(u.email == "inactive@test.com" for u in users)

    def test_count_active_members(self, db_session, sample_account, sample_owner):
        repo = UserRepository(db_session)
        count = repo.count_active_members(sample_account.id)
        assert count >= 1

    def test_create_user(self, db_session, sample_account):
        repo = UserRepository(db_session)
        user = User(
            account_id=sample_account.id,
            email="created@test.com",
            password_hash="hash",
            role=TeamRole.MEMBER,
        )
        result = repo.create(user)
        assert result.id is not None
        assert result.email == "created@test.com"


class TestAccountRepository:
    def test_get_by_id(self, db_session, sample_account):
        repo = AccountRepository(db_session)
        account = repo.get_by_id(sample_account.id)
        assert account is not None
        assert account.name == "Test Business"

    def test_get_by_id_not_found(self, db_session):
        repo = AccountRepository(db_session)
        assert repo.get_by_id(uuid.uuid4()) is None

    def test_create_account(self, db_session):
        repo = AccountRepository(db_session)
        account = Account(name="New Account", plan_tier=PlanTier.PAID)
        result = repo.create(account)
        assert result.id is not None
        assert result.plan_tier == PlanTier.PAID


class TestRefreshTokenRepository:
    def test_hash_token(self):
        hash1 = RefreshTokenRepository.hash_token("my-token")
        hash2 = RefreshTokenRepository.hash_token("my-token")
        assert hash1 == hash2
        assert hash1 != "my-token"

    def test_create_and_get(self, db_session, sample_owner, sample_account):
        repo = RefreshTokenRepository(db_session)
        token = RefreshToken(
            user_id=sample_owner.id,
            account_id=sample_account.id,
            token_hash="unique-hash-123",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        repo.create(token)
        found = repo.get_by_token_hash("unique-hash-123")
        assert found is not None
        assert found.user_id == sample_owner.id

    def test_revoke(self, db_session, sample_owner, sample_account):
        repo = RefreshTokenRepository(db_session)
        token = RefreshToken(
            user_id=sample_owner.id,
            account_id=sample_account.id,
            token_hash="to-revoke-hash",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        repo.create(token)
        assert not token.is_revoked
        repo.revoke(token)
        assert token.is_revoked

    def test_revoke_all_for_user(self, db_session, sample_owner, sample_account):
        repo = RefreshTokenRepository(db_session)
        for i in range(3):
            token = RefreshToken(
                user_id=sample_owner.id,
                account_id=sample_account.id,
                token_hash=f"batch-revoke-{i}",
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            )
            repo.create(token)

        count = repo.revoke_all_for_user(sample_owner.id)
        assert count == 3


class TestTeamInviteRepository:
    def test_create_and_get_by_token(self, db_session, sample_account, sample_owner):
        repo = TeamInviteRepository(db_session)
        invite = TeamInvite(
            account_id=sample_account.id,
            email="new-invite@test.com",
            role=TeamRole.MEMBER,
            invited_by=sample_owner.id,
            token="repo-test-token",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        repo.create(invite)
        found = repo.get_by_token("repo-test-token")
        assert found is not None
        assert found.email == "new-invite@test.com"

    def test_get_pending_by_email_and_account(self, db_session, sample_account, sample_owner):
        repo = TeamInviteRepository(db_session)
        invite = TeamInvite(
            account_id=sample_account.id,
            email="pending@test.com",
            role=TeamRole.MEMBER,
            invited_by=sample_owner.id,
            token="pending-test-token",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        repo.create(invite)
        found = repo.get_pending_by_email_and_account("pending@test.com", sample_account.id)
        assert found is not None

    def test_list_by_account(self, db_session, sample_account, sample_owner):
        repo = TeamInviteRepository(db_session)
        invite = TeamInvite(
            account_id=sample_account.id,
            email="list@test.com",
            role=TeamRole.MEMBER,
            invited_by=sample_owner.id,
            token="list-test-token",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        repo.create(invite)
        invites = repo.list_by_account(sample_account.id)
        assert len(invites) >= 1
