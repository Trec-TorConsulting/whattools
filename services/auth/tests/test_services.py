"""Tests for auth service layer (register, login, token lifecycle, password reset)."""

import secrets

import pytest
from unittest.mock import MagicMock

from services.auth.models.models import TeamRole, User
from services.auth.repositories.auth_repository import RefreshTokenRepository
from services.auth.services.auth_service import AuthService, AuthServiceError


class TestRegistration:
    def test_successful_registration(self, db_session, app, mock_event_publisher):
        with app.app_context():
            svc = AuthService(db_session, event_publisher=mock_event_publisher)
            result = svc.register(
                email="newuser@test.com",
                password="StrongPass1",
                account_name="New Business",
                name="New User",
            )
        assert result["email"] == "newuser@test.com"
        assert result["role"] == TeamRole.OWNER
        assert result["is_verified"] is False
        mock_event_publisher.publish.assert_called_once()

    def test_duplicate_email(self, db_session, app, sample_owner, mock_event_publisher):
        with app.app_context():
            svc = AuthService(db_session, event_publisher=mock_event_publisher)
            with pytest.raises(AuthServiceError) as exc_info:
                svc.register(
                    email="owner@test.com",
                    password="StrongPass1",
                    account_name="Another Biz",
                )
            assert exc_info.value.status_code == 409


class TestLogin:
    def test_successful_login(self, db_session, app, sample_owner):
        with app.app_context():
            svc = AuthService(db_session)
            tokens = svc.login(email="owner@test.com", password="StrongPass1")
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"

    def test_invalid_email(self, db_session, app):
        with app.app_context():
            svc = AuthService(db_session)
            with pytest.raises(AuthServiceError) as exc_info:
                svc.login(email="nonexistent@test.com", password="StrongPass1")
            assert exc_info.value.status_code == 401

    def test_invalid_password(self, db_session, app, sample_owner):
        with app.app_context():
            svc = AuthService(db_session)
            with pytest.raises(AuthServiceError) as exc_info:
                svc.login(email="owner@test.com", password="WrongPassword1")
            assert exc_info.value.status_code == 401

    def test_unverified_email(self, db_session, app, sample_account):
        user = User(
            account_id=sample_account.id,
            email="unverified@test.com",
            password_hash="",
            name="Unverified",
            role=TeamRole.MEMBER,
            is_verified=False,
            is_active=True,
        )
        user.set_password("StrongPass1")
        db_session.add(user)
        db_session.flush()

        with app.app_context():
            svc = AuthService(db_session)
            with pytest.raises(AuthServiceError) as exc_info:
                svc.login(email="unverified@test.com", password="StrongPass1")
            assert exc_info.value.status_code == 403

    def test_account_lockout(self, db_session, app, sample_owner):
        with app.app_context():
            svc = AuthService(db_session)
            for _ in range(5):
                try:
                    svc.login(email="owner@test.com", password="WrongPassword1")
                except AuthServiceError:
                    pass

            with pytest.raises(AuthServiceError) as exc_info:
                svc.login(email="owner@test.com", password="StrongPass1")
            assert exc_info.value.status_code == 429

    def test_inactive_user(self, db_session, app, sample_account):
        user = User(
            account_id=sample_account.id,
            email="deactivated@test.com",
            password_hash="",
            name="Deactivated",
            role=TeamRole.MEMBER,
            is_verified=True,
            is_active=False,
        )
        user.set_password("StrongPass1")
        db_session.add(user)
        db_session.flush()

        with app.app_context():
            svc = AuthService(db_session)
            with pytest.raises(AuthServiceError) as exc_info:
                svc.login(email="deactivated@test.com", password="StrongPass1")
            assert exc_info.value.status_code == 401


class TestTokenRefresh:
    def test_successful_refresh(self, db_session, app, sample_owner):
        with app.app_context():
            svc = AuthService(db_session)
            tokens = svc.login(email="owner@test.com", password="StrongPass1")
            new_tokens = svc.refresh(tokens["refresh_token"])
        assert "access_token" in new_tokens
        assert new_tokens["refresh_token"] != tokens["refresh_token"]

    def test_refresh_with_invalid_token(self, db_session, app):
        with app.app_context():
            svc = AuthService(db_session)
            with pytest.raises(AuthServiceError) as exc_info:
                svc.refresh("totally-invalid-token")
            assert exc_info.value.status_code == 401

    def test_refresh_revoked_token(self, db_session, app, sample_owner):
        with app.app_context():
            svc = AuthService(db_session)
            tokens = svc.login(email="owner@test.com", password="StrongPass1")
            # First refresh works
            svc.refresh(tokens["refresh_token"])
            # Same token a second time should fail (rotation revokes old)
            with pytest.raises(AuthServiceError) as exc_info:
                svc.refresh(tokens["refresh_token"])
            assert exc_info.value.status_code == 401


class TestLogout:
    def test_successful_logout(self, db_session, app, sample_owner):
        with app.app_context():
            svc = AuthService(db_session)
            tokens = svc.login(email="owner@test.com", password="StrongPass1")
            svc.logout(tokens["refresh_token"])
            # Token should now be revoked
            with pytest.raises(AuthServiceError):
                svc.refresh(tokens["refresh_token"])

    def test_logout_with_invalid_token(self, db_session, app):
        with app.app_context():
            svc = AuthService(db_session)
            # Should not raise — graceful handling
            svc.logout("nonexistent-token")


class TestEmailVerification:
    def test_successful_verification(self, db_session, app, mock_event_publisher):
        with app.app_context():
            svc = AuthService(db_session, event_publisher=mock_event_publisher)
            result = svc.register(
                email="toverify@test.com",
                password="StrongPass1",
                account_name="Verify Business",
            )
            # Get the user to find the verification token
            from services.auth.repositories.auth_repository import UserRepository
            user = UserRepository(db_session).get_by_email("toverify@test.com")
            assert user is not None
            assert user.verification_token is not None

            svc.verify_email(user.verification_token)
            assert user.is_verified

    def test_invalid_verification_token(self, db_session, app):
        with app.app_context():
            svc = AuthService(db_session)
            with pytest.raises(AuthServiceError) as exc_info:
                svc.verify_email("invalid-token")
            assert exc_info.value.status_code == 400


class TestPasswordReset:
    def test_request_reset_existing_email(self, db_session, app, sample_owner):
        with app.app_context():
            svc = AuthService(db_session)
            svc.request_password_reset("owner@test.com")
            # Verify token was set
            from services.auth.repositories.auth_repository import UserRepository
            user = UserRepository(db_session).get_by_email("owner@test.com")
            assert user is not None
            assert user.reset_token is not None

    def test_request_reset_nonexistent_email(self, db_session, app):
        with app.app_context():
            svc = AuthService(db_session)
            # Should not raise — prevents enumeration
            svc.request_password_reset("nonexistent@test.com")

    def test_confirm_reset(self, db_session, app, sample_owner):
        with app.app_context():
            svc = AuthService(db_session)
            svc.request_password_reset("owner@test.com")

            from services.auth.repositories.auth_repository import UserRepository
            user = UserRepository(db_session).get_by_email("owner@test.com")
            assert user is not None and user.reset_token is not None

            svc.confirm_password_reset(user.reset_token, "NewStrongPass1")
            assert user.check_password("NewStrongPass1")
            assert user.reset_token is None

    def test_confirm_reset_invalid_token(self, db_session, app):
        with app.app_context():
            svc = AuthService(db_session)
            with pytest.raises(AuthServiceError) as exc_info:
                svc.confirm_password_reset("bad-token", "NewStrongPass1")
            assert exc_info.value.status_code == 400
