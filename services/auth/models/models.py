"""Auth service database models: Account, User, RefreshToken, TeamInvite."""

import uuid
from datetime import datetime, timezone
from enum import StrEnum

import bcrypt
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.shared.models import BaseModel


class PlanTier(StrEnum):
    """Account plan tiers."""

    FREE = "free"
    PAID = "paid"


class TeamRole(StrEnum):
    """User roles within an account."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class Account(BaseModel):
    """Organization/business account. Every user belongs to exactly one account."""

    __tablename__ = "accounts"

    name: Mapped[str] = mapped_column(String(255))
    plan_tier: Mapped[str] = mapped_column(String(20), default=PlanTier.FREE)

    # Stripe billing
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None, init=False)
    subscription_status: Mapped[str | None] = mapped_column(String(50), nullable=True, default=None, init=False)

    @property
    def team_member_limit(self) -> int:
        """Maximum number of team members allowed for this plan."""
        if self.plan_tier == PlanTier.PAID:
            return 100
        return 2

    @property
    def inventory_item_limit(self) -> int:
        """Maximum number of inventory items allowed for this plan."""
        if self.plan_tier == PlanTier.PAID:
            return -1  # unlimited
        return 50


# Fix the relationship after User is defined — see bottom of file


class User(BaseModel):
    """User account with authentication credentials and team role."""

    __tablename__ = "users"

    account_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("accounts.id"), index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255), default="")
    role: Mapped[str] = mapped_column(String(20), default=TeamRole.MEMBER)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Account lockout
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, init=False)
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True, init=False
    )

    # Email verification / password reset tokens
    verification_token: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None, init=False)
    verification_token_expires: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, init=False
    )
    reset_token: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None, init=False)
    reset_token_expires: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, init=False
    )

    def set_password(self, password: str) -> None:
        """Hash and store a password using bcrypt."""
        self.password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def check_password(self, password: str) -> bool:
        """Verify a password against the stored hash."""
        return bcrypt.checkpw(password.encode(), self.password_hash.encode())

    @property
    def is_locked(self) -> bool:
        """Check if the account is currently locked due to failed login attempts."""
        if self.locked_until is None:
            return False
        locked = self.locked_until
        if locked.tzinfo is None:
            locked = locked.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) < locked

    def increment_failed_login(self, *, max_attempts: int = 5, lockout_minutes: int = 15) -> bool:
        """Record a failed login attempt. Returns True if account is now locked."""
        from datetime import timedelta

        self.failed_login_attempts += 1
        if self.failed_login_attempts >= max_attempts:
            self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=lockout_minutes)
            return True
        return False

    def reset_failed_logins(self) -> None:
        """Reset the failed login counter after a successful login."""
        self.failed_login_attempts = 0
        self.locked_until = None


class RefreshToken(BaseModel):
    """Stored refresh tokens for JWT revocation tracking and rotation."""

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    account_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("accounts.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)

    @property
    def is_expired(self) -> bool:
        """Check if the token has expired."""
        exp = self.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > exp

    @property
    def is_valid(self) -> bool:
        """Check if the token is neither revoked nor expired."""
        return not self.is_revoked and not self.is_expired


class TeamInvite(BaseModel):
    """Pending team invitation — links an email to an account before the user registers."""

    __tablename__ = "team_invites"

    account_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("accounts.id"), index=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    invited_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    token: Mapped[str] = mapped_column(String(255), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    role: Mapped[str] = mapped_column(String(20), default=TeamRole.MEMBER)
    is_accepted: Mapped[bool] = mapped_column(Boolean, default=False)

    @property
    def is_expired(self) -> bool:
        """Check if the invitation has expired."""
        exp = self.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > exp

    @property
    def is_valid(self) -> bool:
        """Check if the invitation is still usable."""
        return not self.is_accepted and not self.is_expired


# Configure Account.users relationship via backref after both classes exist.
# Using __mapper_args__ doesn't work well with MappedAsDataclass, so we
# configure the relationship directly on Account's mapper.
from sqlalchemy.orm import configure_mappers  # noqa: E402

Account.__mapper__.add_property(
    "users",
    relationship(User, backref="account", lazy="select", foreign_keys=[User.account_id]),
)

configure_mappers()
