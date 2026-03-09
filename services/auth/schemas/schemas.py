"""Marshmallow schemas for auth service request/response validation."""

import re

from marshmallow import Schema, fields, validate, validates, ValidationError


# Password validation regex: min 8 chars, at least one uppercase, one digit
PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Z])(?=.*\d).{8,}$")


class RegisterSchema(Schema):
    """Schema for user registration."""

    email = fields.Email(required=True)
    password = fields.String(required=True, load_only=True)
    name = fields.String(required=False, validate=validate.Length(max=255))
    account_name = fields.String(required=True, validate=validate.Length(min=1, max=255))

    @validates("password")
    def validate_password(self, value: str) -> None:
        if not PASSWORD_PATTERN.match(value):
            raise ValidationError(
                "Password must be at least 8 characters with at least one uppercase letter and one digit."
            )


class LoginSchema(Schema):
    """Schema for user login."""

    email = fields.Email(required=True)
    password = fields.String(required=True, load_only=True)


class TokenResponseSchema(Schema):
    """Schema for token pair response."""

    access_token = fields.String(dump_only=True)
    refresh_token = fields.String(dump_only=True)
    token_type = fields.String(dump_only=True, dump_default="bearer")


class RefreshTokenSchema(Schema):
    """Schema for token refresh request."""

    refresh_token = fields.String(required=True)


class PasswordResetRequestSchema(Schema):
    """Schema for requesting a password reset."""

    email = fields.Email(required=True)


class PasswordResetConfirmSchema(Schema):
    """Schema for completing a password reset."""

    token = fields.String(required=True)
    password = fields.String(required=True, load_only=True)

    @validates("password")
    def validate_password(self, value: str) -> None:
        if not PASSWORD_PATTERN.match(value):
            raise ValidationError(
                "Password must be at least 8 characters with at least one uppercase letter and one digit."
            )


class EmailVerificationSchema(Schema):
    """Schema for email verification."""

    token = fields.String(required=True)


class UserProfileSchema(Schema):
    """Schema for user profile response and update."""

    id = fields.UUID(dump_only=True)
    email = fields.Email()
    name = fields.String(validate=validate.Length(max=255))
    role = fields.String(dump_only=True)
    is_verified = fields.Boolean(dump_only=True)
    account_id = fields.UUID(dump_only=True)
    created_at = fields.DateTime(dump_only=True)


class UserProfileUpdateSchema(Schema):
    """Schema for updating user profile."""

    email = fields.Email()
    name = fields.String(validate=validate.Length(max=255))


class AccountSchema(Schema):
    """Schema for account details response."""

    id = fields.UUID(dump_only=True)
    name = fields.String()
    plan_tier = fields.String(dump_only=True)
    member_count = fields.Integer(dump_only=True)
    created_at = fields.DateTime(dump_only=True)


class AccountUpdateSchema(Schema):
    """Schema for updating account details."""

    name = fields.String(required=True, validate=validate.Length(min=1, max=255))


class TeamInviteSchema(Schema):
    """Schema for inviting a team member."""

    email = fields.Email(required=True)
    role = fields.String(validate=validate.OneOf(["admin", "member"]), load_default="member")


class TeamMemberSchema(Schema):
    """Schema for team member response."""

    id = fields.UUID(dump_only=True)
    email = fields.String(dump_only=True)
    name = fields.String(dump_only=True)
    role = fields.String(dump_only=True)
    is_verified = fields.Boolean(dump_only=True)
    is_active = fields.Boolean(dump_only=True)
    created_at = fields.DateTime(dump_only=True)


class RoleUpdateSchema(Schema):
    """Schema for updating a team member's role."""

    role = fields.String(required=True, validate=validate.OneOf(["admin", "member"]))
