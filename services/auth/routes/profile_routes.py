"""User profile routes — view, update, and delete own profile."""

import uuid

from flask import Blueprint, current_app, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from services.auth.schemas.schemas import UserProfileUpdateSchema
from services.auth.services.account_service import AccountService
from services.auth.services.auth_service import AuthServiceError
from services.shared.database import get_db
from services.shared.errors import error_response, success_response

profile_bp = Blueprint("profile", __name__)


def _get_account_service() -> AccountService:
    db = get_db()
    publisher = current_app.config.get("_EVENT_PUBLISHER")
    return AccountService(db, event_publisher=publisher)


@profile_bp.route("/users/me", methods=["GET"])
@jwt_required()
def get_profile():  # type: ignore[no-untyped-def]
    """Get the current user's profile."""
    user_id = uuid.UUID(get_jwt_identity())

    svc = _get_account_service()
    try:
        result = svc.get_profile(user_id)
    except AuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@profile_bp.route("/users/me", methods=["PUT"])
@jwt_required()
def update_profile():  # type: ignore[no-untyped-def]
    """Update the current user's profile."""
    user_id = uuid.UUID(get_jwt_identity())
    claims = get_jwt()
    account_id = uuid.UUID(claims["account_id"])

    schema = UserProfileUpdateSchema()
    data = schema.load(request.get_json(force=True))

    svc = _get_account_service()
    try:
        result = svc.update_profile(user_id, account_id, updates=data)
    except AuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@profile_bp.route("/users/me", methods=["DELETE"])
@jwt_required()
def delete_account():  # type: ignore[no-untyped-def]
    """Delete the current user's account (owner only, soft-delete)."""
    user_id = uuid.UUID(get_jwt_identity())
    claims = get_jwt()
    account_id = uuid.UUID(claims["account_id"])

    svc = _get_account_service()
    try:
        svc.delete_account(account_id, actor_id=user_id)
    except AuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response({"message": "Account scheduled for deletion."})
