"""Auth service layer — registration, login, token management, password reset."""

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from flask_jwt_extended import create_access_token, create_refresh_token
from sqlalchemy.orm import Session

from services.auth.models.models import (
    Account,
    PlanTier,
    RefreshToken,
    TeamRole,
    User,
)
from services.auth.repositories.auth_repository import (
    AccountRepository,
    RefreshTokenRepository,
    UserRepository,
)
from services.shared.audit import log_audit
from services.shared.events import EventPublisher
from services.shared.logging import get_logger

logger = get_logger("auth_service")


def _ensure_aware(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware (default to UTC if naive)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class AuthServiceError(Exception):
    """Base exception for auth service errors."""

    def __init__(self, message: str, code: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class AuthService:
    """Handles registration, login, token lifecycle, and password reset."""

    def __init__(
        self,
        db: Session,
        event_publisher: EventPublisher | None = None,
    ) -> None:
        self.db = db
        self.user_repo = UserRepository(db)
        self.account_repo = AccountRepository(db)
        self.token_repo = RefreshTokenRepository(db)
        self.event_publisher = event_publisher

    # ── Registration ────────────────────────────────────────────────

    def register(self, email: str, password: str, account_name: str, name: str = "") -> dict[str, Any]:
        """Register a new user and create their account.

        Returns:
            Dict with user profile data (no tokens until verified).

        Raises:
            AuthServiceError: If email already exists.
        """
        existing = self.user_repo.get_by_email(email)
        if existing is not None:
            raise AuthServiceError("An account with this email already exists.", "conflict", 409)

        account = Account(name=account_name)
        self.account_repo.create(account)

        user = User(
            account_id=account.id,
            email=email,
            password_hash="",  # Set via set_password below
            name=name,
            role=TeamRole.OWNER,
        )
        user.set_password(password)
        user.verification_token = secrets.token_urlsafe(32)
        user.verification_token_expires = datetime.now(timezone.utc) + timedelta(hours=24)
        self.user_repo.create(user)

        self.db.commit()

        self._publish_event("user.created", {
            "user_id": str(user.id),
            "account_id": str(account.id),
            "email": user.email,
            "role": user.role,
        })

        return {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "account_id": str(account.id),
            "is_verified": user.is_verified,
        }

    # ── Email Verification ──────────────────────────────────────────

    def verify_email(self, token: str) -> None:
        """Verify a user's email using the verification token.

        Raises:
            AuthServiceError: If the token is invalid or expired.
        """
        user = self.user_repo.get_by_verification_token(token)
        if user is None:
            raise AuthServiceError("Invalid or expired verification token.", "bad_request", 400)

        if user.verification_token_expires and datetime.now(timezone.utc) > _ensure_aware(user.verification_token_expires):
            raise AuthServiceError("Invalid or expired verification token.", "bad_request", 400)

        user.is_verified = True
        user.verification_token = None
        user.verification_token_expires = None
        self.user_repo.save()
        self.db.commit()

        self._publish_event("user.verified", {
            "user_id": str(user.id),
            "account_id": str(user.account_id),
        })

    # ── Login ───────────────────────────────────────────────────────

    def login(self, email: str, password: str) -> dict[str, str]:
        """Authenticate a user and return JWT tokens.

        Returns:
            Dict with access_token, refresh_token, and token_type.

        Raises:
            AuthServiceError: On invalid credentials, unverified email, or account lockout.
        """
        user = self.user_repo.get_by_email(email)
        if user is None:
            raise AuthServiceError("Invalid email or password.", "unauthorized", 401)

        if not user.is_active:
            raise AuthServiceError("Invalid email or password.", "unauthorized", 401)

        if user.is_locked:
            raise AuthServiceError("Account is temporarily locked. Try again later.", "rate_limited", 429)

        if not user.check_password(password):
            locked = user.increment_failed_login()
            self.user_repo.save()
            self.db.commit()
            if locked:
                logger.warning("account_locked", user_id=str(user.id), email=user.email)
                raise AuthServiceError("Account is temporarily locked. Try again later.", "rate_limited", 429)
            raise AuthServiceError("Invalid email or password.", "unauthorized", 401)

        if not user.is_verified:
            raise AuthServiceError("Email verification required.", "forbidden", 403)

        # Successful login — reset failed attempts
        user.reset_failed_logins()
        self.user_repo.save()

        # Create JWTs
        identity = str(user.id)
        additional_claims = {"account_id": str(user.account_id), "role": user.role}
        access_token = create_access_token(identity=identity, additional_claims=additional_claims)
        raw_refresh = create_refresh_token(identity=identity, additional_claims=additional_claims)

        # Store hashed refresh token
        self._store_refresh_token(user, raw_refresh)
        self.db.commit()

        return {
            "access_token": access_token,
            "refresh_token": raw_refresh,
            "token_type": "bearer",
        }

    # ── Token Refresh ───────────────────────────────────────────────

    def refresh(self, raw_refresh_token: str) -> dict[str, str]:
        """Rotate refresh token and return new token pair.

        Raises:
            AuthServiceError: If the token is invalid, revoked, or expired.
        """
        token_hash = RefreshTokenRepository.hash_token(raw_refresh_token)
        stored = self.token_repo.get_by_token_hash(token_hash)

        if stored is None or not stored.is_valid:
            raise AuthServiceError("Invalid or expired refresh token.", "unauthorized", 401)

        # Revoke old token (rotation)
        self.token_repo.revoke(stored)

        user = self.user_repo.get_by_id(stored.user_id)
        if user is None or not user.is_active:
            raise AuthServiceError("Invalid or expired refresh token.", "unauthorized", 401)

        # Issue new tokens
        identity = str(user.id)
        additional_claims = {"account_id": str(user.account_id), "role": user.role}
        access_token = create_access_token(identity=identity, additional_claims=additional_claims)
        raw_refresh = create_refresh_token(identity=identity, additional_claims=additional_claims)

        self._store_refresh_token(user, raw_refresh)
        self.db.commit()

        return {
            "access_token": access_token,
            "refresh_token": raw_refresh,
            "token_type": "bearer",
        }

    # ── Logout ──────────────────────────────────────────────────────

    def logout(self, raw_refresh_token: str) -> None:
        """Revoke the given refresh token.

        Raises:
            AuthServiceError: If the token is not found.
        """
        token_hash = RefreshTokenRepository.hash_token(raw_refresh_token)
        stored = self.token_repo.get_by_token_hash(token_hash)
        if stored is not None:
            self.token_repo.revoke(stored)
        self.db.commit()

    # ── Password Reset ──────────────────────────────────────────────

    def request_password_reset(self, email: str) -> None:
        """Send a password reset email. Always returns success to prevent enumeration."""
        user = self.user_repo.get_by_email(email)
        if user is None:
            return  # Silent — prevent email enumeration

        user.reset_token = secrets.token_urlsafe(32)
        user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        self.user_repo.save()
        self.db.commit()

        # TODO: Send actual email (Phase 2)
        logger.info("password_reset_requested", user_id=str(user.id))

    def confirm_password_reset(self, token: str, new_password: str) -> None:
        """Complete a password reset using a valid token.

        Raises:
            AuthServiceError: If the token is invalid or expired.
        """
        user = self.user_repo.get_by_reset_token(token)
        if user is None:
            raise AuthServiceError("Invalid or expired reset token.", "bad_request", 400)

        if user.reset_token_expires and datetime.now(timezone.utc) > _ensure_aware(user.reset_token_expires):
            raise AuthServiceError("Invalid or expired reset token.", "bad_request", 400)

        user.set_password(new_password)
        user.reset_token = None
        user.reset_token_expires = None
        self.user_repo.save()

        # Revoke all refresh tokens
        self.token_repo.revoke_all_for_user(user.id)
        self.db.commit()

        logger.info("password_reset_completed", user_id=str(user.id))

    # ── Helpers ─────────────────────────────────────────────────────

    def _store_refresh_token(self, user: User, raw_token: str) -> RefreshToken:
        """Hash and store a refresh token in the database."""
        token_hash = RefreshTokenRepository.hash_token(raw_token)
        refresh_record = RefreshToken(
            user_id=user.id,
            account_id=user.account_id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        return self.token_repo.create(refresh_record)

    def _publish_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Publish an event to Redis Pub/Sub if publisher is available."""
        if self.event_publisher is not None:
            self.event_publisher.publish(event_type, payload, source_service="auth")
