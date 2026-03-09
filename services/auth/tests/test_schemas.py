"""Tests for Marshmallow schemas."""

import pytest
from marshmallow import ValidationError

from services.auth.schemas.schemas import (
    LoginSchema,
    PasswordResetConfirmSchema,
    RegisterSchema,
    RoleUpdateSchema,
    TeamInviteSchema,
    UserProfileUpdateSchema,
)


class TestRegisterSchema:
    def test_valid_registration(self):
        data = RegisterSchema().load({
            "email": "user@test.com",
            "password": "StrongPass1",
            "account_name": "My Business",
            "name": "Test User",
        })
        assert data["email"] == "user@test.com"
        assert data["account_name"] == "My Business"

    def test_missing_email(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterSchema().load({"password": "StrongPass1", "account_name": "Biz"})
        assert "email" in exc_info.value.messages

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            RegisterSchema().load({"email": "not-an-email", "password": "StrongPass1", "account_name": "Biz"})

    def test_weak_password_no_uppercase(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterSchema().load({"email": "u@t.com", "password": "weakpass1", "account_name": "Biz"})
        assert "password" in exc_info.value.messages

    def test_weak_password_no_digit(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterSchema().load({"email": "u@t.com", "password": "WeakPasss", "account_name": "Biz"})
        assert "password" in exc_info.value.messages

    def test_weak_password_too_short(self):
        with pytest.raises(ValidationError):
            RegisterSchema().load({"email": "u@t.com", "password": "Ab1", "account_name": "Biz"})

    def test_missing_account_name(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterSchema().load({"email": "u@t.com", "password": "StrongPass1"})
        assert "account_name" in exc_info.value.messages


class TestLoginSchema:
    def test_valid_login(self):
        data = LoginSchema().load({"email": "user@test.com", "password": "pass"})
        assert data["email"] == "user@test.com"

    def test_missing_fields(self):
        with pytest.raises(ValidationError):
            LoginSchema().load({})


class TestPasswordResetConfirmSchema:
    def test_valid_reset(self):
        data = PasswordResetConfirmSchema().load({"token": "abc123", "password": "NewStrong1"})
        assert data["token"] == "abc123"

    def test_weak_password(self):
        with pytest.raises(ValidationError):
            PasswordResetConfirmSchema().load({"token": "abc123", "password": "weak"})


class TestTeamInviteSchema:
    def test_valid_invite(self):
        data = TeamInviteSchema().load({"email": "invite@test.com", "role": "admin"})
        assert data["email"] == "invite@test.com"
        assert data["role"] == "admin"

    def test_default_role(self):
        data = TeamInviteSchema().load({"email": "invite@test.com"})
        assert data["role"] == "member"

    def test_invalid_role(self):
        with pytest.raises(ValidationError):
            TeamInviteSchema().load({"email": "invite@test.com", "role": "owner"})


class TestRoleUpdateSchema:
    def test_valid_role(self):
        data = RoleUpdateSchema().load({"role": "admin"})
        assert data["role"] == "admin"

    def test_invalid_role(self):
        with pytest.raises(ValidationError):
            RoleUpdateSchema().load({"role": "owner"})


class TestUserProfileUpdateSchema:
    def test_valid_update(self):
        data = UserProfileUpdateSchema().load({"name": "New Name", "email": "new@test.com"})
        assert data["name"] == "New Name"

    def test_partial_update(self):
        data = UserProfileUpdateSchema().load({"name": "Just Name"})
        assert data["name"] == "Just Name"
        assert "email" not in data
