"""Auth routes — register, login, refresh, logout, password reset, email verification."""

from flask import Blueprint, current_app, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from marshmallow import ValidationError

from services.auth.schemas.schemas import (
    EmailVerificationSchema,
    LoginSchema,
    PasswordResetConfirmSchema,
    PasswordResetRequestSchema,
    RefreshTokenSchema,
    RegisterSchema,
)
from services.auth.services.auth_service import AuthService, AuthServiceError
from services.shared.database import get_db
from services.shared.errors import error_response, success_response

auth_bp = Blueprint("auth", __name__)


def _get_auth_service() -> AuthService:
    db = get_db()
    publisher = current_app.config.get("_EVENT_PUBLISHER")
    return AuthService(db, event_publisher=publisher)


@auth_bp.route("/register", methods=["POST"])
def register():  # type: ignore[no-untyped-def]
    """Register a new user and create their account."""
    schema = RegisterSchema()
    data = schema.load(request.get_json(force=True))

    svc = _get_auth_service()
    try:
        result = svc.register(
            email=data["email"],
            password=data["password"],
            account_name=data["account_name"],
            name=data.get("name", ""),
        )
    except AuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result, status_code=201)


@auth_bp.route("/login", methods=["POST"])
def login():  # type: ignore[no-untyped-def]
    """Authenticate and return JWT tokens."""
    schema = LoginSchema()
    data = schema.load(request.get_json(force=True))

    svc = _get_auth_service()
    try:
        tokens = svc.login(email=data["email"], password=data["password"])
    except AuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(tokens)


@auth_bp.route("/refresh", methods=["POST"])
def refresh():  # type: ignore[no-untyped-def]
    """Refresh JWT tokens using a valid refresh token."""
    schema = RefreshTokenSchema()
    data = schema.load(request.get_json(force=True))

    svc = _get_auth_service()
    try:
        tokens = svc.refresh(raw_refresh_token=data["refresh_token"])
    except AuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(tokens)


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():  # type: ignore[no-untyped-def]
    """Revoke the current refresh token."""
    schema = RefreshTokenSchema()
    data = schema.load(request.get_json(force=True))

    svc = _get_auth_service()
    svc.logout(raw_refresh_token=data["refresh_token"])
    return success_response({"message": "Logged out successfully."})


@auth_bp.route("/password-reset", methods=["POST"])
def request_password_reset():  # type: ignore[no-untyped-def]
    """Request a password reset email."""
    schema = PasswordResetRequestSchema()
    data = schema.load(request.get_json(force=True))

    svc = _get_auth_service()
    svc.request_password_reset(email=data["email"])
    return success_response({"message": "If the email exists, a reset link has been sent."})


@auth_bp.route("/password-reset/confirm", methods=["POST"])
def confirm_password_reset():  # type: ignore[no-untyped-def]
    """Complete a password reset with token and new password."""
    schema = PasswordResetConfirmSchema()
    data = schema.load(request.get_json(force=True))

    svc = _get_auth_service()
    try:
        svc.confirm_password_reset(token=data["token"], new_password=data["password"])
    except AuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response({"message": "Password reset successfully."})


@auth_bp.route("/verify-email", methods=["POST"])
def verify_email():  # type: ignore[no-untyped-def]
    """Verify a user's email with the verification token."""
    schema = EmailVerificationSchema()
    data = schema.load(request.get_json(force=True))

    svc = _get_auth_service()
    try:
        svc.verify_email(token=data["token"])
    except AuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response({"message": "Email verified successfully."})
