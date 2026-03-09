"""Auth repository — User, RefreshToken, and TeamInvite data access."""

import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.auth.models.models import (
    Account,
    RefreshToken,
    TeamInvite,
    User,
)
from services.shared.audit import log_audit


class UserRepository:
    """Data access for User records."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.db.execute(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        ).scalar_one_or_none()

    def get_by_email(self, email: str) -> User | None:
        return self.db.execute(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        ).scalar_one_or_none()

    def get_by_verification_token(self, token: str) -> User | None:
        return self.db.execute(
            select(User).where(User.verification_token == token, User.deleted_at.is_(None))
        ).scalar_one_or_none()

    def get_by_reset_token(self, token: str) -> User | None:
        return self.db.execute(
            select(User).where(User.reset_token == token, User.deleted_at.is_(None))
        ).scalar_one_or_none()

    def list_by_account(self, account_id: uuid.UUID, *, include_inactive: bool = False) -> list[User]:
        query = select(User).where(User.account_id == account_id, User.deleted_at.is_(None))
        if not include_inactive:
            query = query.where(User.is_active.is_(True))
        return list(self.db.execute(query).scalars().all())

    def count_active_members(self, account_id: uuid.UUID) -> int:
        return self.db.execute(
            select(func.count())
            .select_from(User)
            .where(User.account_id == account_id, User.is_active.is_(True), User.deleted_at.is_(None))
        ).scalar_one()

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user

    def save(self) -> None:
        self.db.flush()


class AccountRepository:
    """Data access for Account records."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, account_id: uuid.UUID) -> Account | None:
        return self.db.execute(
            select(Account).where(Account.id == account_id, Account.deleted_at.is_(None))
        ).scalar_one_or_none()

    def create(self, account: Account) -> Account:
        self.db.add(account)
        self.db.flush()
        return account

    def save(self) -> None:
        self.db.flush()


class RefreshTokenRepository:
    """Data access for RefreshToken records."""

    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def hash_token(raw_token: str) -> str:
        """Create a SHA-256 hash of a raw refresh token for storage."""
        return hashlib.sha256(raw_token.encode()).hexdigest()

    def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        return self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

    def create(self, token: RefreshToken) -> RefreshToken:
        self.db.add(token)
        self.db.flush()
        return token

    def revoke(self, token: RefreshToken) -> None:
        token.is_revoked = True
        self.db.flush()

    def revoke_all_for_user(self, user_id: uuid.UUID) -> int:
        """Revoke all active refresh tokens for a user. Returns count revoked."""
        tokens = self.db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked.is_(False),
                RefreshToken.deleted_at.is_(None),
            )
        ).scalars().all()
        count = 0
        for t in tokens:
            t.is_revoked = True
            count += 1
        self.db.flush()
        return count

    def save(self) -> None:
        self.db.flush()


class TeamInviteRepository:
    """Data access for TeamInvite records."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_token(self, token: str) -> TeamInvite | None:
        return self.db.execute(
            select(TeamInvite).where(TeamInvite.token == token, TeamInvite.deleted_at.is_(None))
        ).scalar_one_or_none()

    def get_pending_by_email_and_account(self, email: str, account_id: uuid.UUID) -> TeamInvite | None:
        return self.db.execute(
            select(TeamInvite).where(
                TeamInvite.email == email,
                TeamInvite.account_id == account_id,
                TeamInvite.is_accepted.is_(False),
                TeamInvite.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

    def list_by_account(self, account_id: uuid.UUID, *, pending_only: bool = True) -> list[TeamInvite]:
        query = select(TeamInvite).where(TeamInvite.account_id == account_id, TeamInvite.deleted_at.is_(None))
        if pending_only:
            query = query.where(TeamInvite.is_accepted.is_(False))
        return list(self.db.execute(query).scalars().all())

    def create(self, invite: TeamInvite) -> TeamInvite:
        self.db.add(invite)
        self.db.flush()
        return invite

    def save(self) -> None:
        self.db.flush()
