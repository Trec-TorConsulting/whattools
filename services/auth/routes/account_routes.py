"""Account and team management routes."""

import uuid

from flask import Blueprint, current_app, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from services.auth.schemas.schemas import (
    AccountUpdateSchema,
    RoleUpdateSchema,
    TeamInviteSchema,
)
from services.auth.services.account_service import AccountService
from services.auth.services.auth_service import AuthServiceError
from services.shared.database import get_db
from services.shared.errors import error_response, success_response

account_bp = Blueprint("account", __name__)


def _get_account_service() -> AccountService:
    db = get_db()
    publisher = current_app.config.get("_EVENT_PUBLISHER")
    return AccountService(db, event_publisher=publisher)


def _require_role(*allowed_roles: str):  # type: ignore[no-untyped-def]
    """Check that the current user has one of the allowed roles."""
    claims = get_jwt()
    role = claims.get("role", "")
    if role not in allowed_roles:
        return error_response("forbidden", "You do not have permission to perform this action.", status_code=403)
    return None


# ── Account ─────────────────────────────────────────────────────────


@account_bp.route("/account", methods=["GET"])
@jwt_required()
def get_account():  # type: ignore[no-untyped-def]
    """View account details."""
    claims = get_jwt()
    account_id = uuid.UUID(claims["account_id"])

    svc = _get_account_service()
    try:
        result = svc.get_account(account_id)
    except AuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@account_bp.route("/account", methods=["PUT"])
@jwt_required()
def update_account():  # type: ignore[no-untyped-def]
    """Update account details (owner/admin only)."""
    role_err = _require_role("owner", "admin")
    if role_err:
        return role_err

    claims = get_jwt()
    account_id = uuid.UUID(claims["account_id"])
    actor_id = uuid.UUID(get_jwt_identity())

    schema = AccountUpdateSchema()
    data = schema.load(request.get_json(force=True))

    svc = _get_account_service()
    try:
        result = svc.update_account(account_id, actor_id, name=data["name"])
    except AuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


# ── Team Members ────────────────────────────────────────────────────


@account_bp.route("/account/members", methods=["GET"])
@jwt_required()
def list_members():  # type: ignore[no-untyped-def]
    """List all team members."""
    claims = get_jwt()
    account_id = uuid.UUID(claims["account_id"])

    svc = _get_account_service()
    members = svc.list_members(account_id)
    return success_response(members)


@account_bp.route("/account/invite", methods=["POST"])
@jwt_required()
def invite_member():  # type: ignore[no-untyped-def]
    """Invite a new team member."""
    role_err = _require_role("owner", "admin")
    if role_err:
        return role_err

    claims = get_jwt()
    account_id = uuid.UUID(claims["account_id"])
    actor_id = uuid.UUID(get_jwt_identity())

    schema = TeamInviteSchema()
    data = schema.load(request.get_json(force=True))

    svc = _get_account_service()
    try:
        result = svc.invite_member(
            account_id=account_id,
            actor_id=actor_id,
            email=data["email"],
            role=data.get("role", "member"),
        )
    except AuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result, status_code=201)


@account_bp.route("/account/members/<uuid:member_id>/role", methods=["PUT"])
@jwt_required()
def update_member_role(member_id: uuid.UUID):  # type: ignore[no-untyped-def]
    """Update a team member's role (owner only)."""
    role_err = _require_role("owner")
    if role_err:
        return role_err

    claims = get_jwt()
    account_id = uuid.UUID(claims["account_id"])
    actor_id = uuid.UUID(get_jwt_identity())

    schema = RoleUpdateSchema()
    data = schema.load(request.get_json(force=True))

    svc = _get_account_service()
    try:
        result = svc.update_member_role(
            account_id=account_id,
            actor_id=actor_id,
            member_id=member_id,
            new_role=data["role"],
        )
    except AuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@account_bp.route("/account/members/<uuid:member_id>", methods=["DELETE"])
@jwt_required()
def remove_member(member_id: uuid.UUID):  # type: ignore[no-untyped-def]
    """Remove a team member."""
    role_err = _require_role("owner", "admin")
    if role_err:
        return role_err

    claims = get_jwt()
    account_id = uuid.UUID(claims["account_id"])
    actor_id = uuid.UUID(get_jwt_identity())

    svc = _get_account_service()
    try:
        svc.remove_member(account_id=account_id, actor_id=actor_id, member_id=member_id)
    except AuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response({"message": "Member removed successfully."})
