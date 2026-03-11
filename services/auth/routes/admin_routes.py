"""Platform admin routes — account management, user management, metrics, impersonation."""

import uuid

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity

from services.auth.decorators import require_platform_admin
from services.auth.services.admin_service import AdminService, AdminServiceError
from services.shared.database import get_db
from services.shared.errors import error_response, success_response

admin_bp = Blueprint("admin", __name__)


def _get_admin_service() -> AdminService:
    return AdminService(get_db())


def _get_client_ip() -> str | None:
    return request.headers.get("X-Forwarded-For", request.remote_addr)


# ── Metrics ─────────────────────────────────────────────────────


@admin_bp.route("/metrics", methods=["GET"])
@require_platform_admin
def get_metrics():  # type: ignore[no-untyped-def]
    """Get platform-wide metrics."""
    svc = _get_admin_service()
    return success_response(svc.get_platform_metrics())


# ── Accounts ────────────────────────────────────────────────────


@admin_bp.route("/accounts", methods=["GET"])
@require_platform_admin
def list_accounts():  # type: ignore[no-untyped-def]
    """List all accounts with pagination and filters."""
    svc = _get_admin_service()
    try:
        result = svc.list_accounts(
            page=request.args.get("page", 1, type=int),
            per_page=request.args.get("per_page", 25, type=int),
            search=request.args.get("search"),
            plan_tier=request.args.get("plan_tier"),
            is_suspended=request.args.get("is_suspended", type=lambda v: v.lower() == "true") if request.args.get("is_suspended") else None,
        )
    except AdminServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)
    return success_response(result["accounts"], meta={"pagination": result["pagination"]})


@admin_bp.route("/accounts/<uuid:account_id>", methods=["GET"])
@require_platform_admin
def get_account(account_id: uuid.UUID):  # type: ignore[no-untyped-def]
    """Get detailed account information."""
    svc = _get_admin_service()
    try:
        result = svc.get_account(account_id)
    except AdminServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)
    return success_response(result)


@admin_bp.route("/accounts/<uuid:account_id>/suspend", methods=["POST"])
@require_platform_admin
def suspend_account(account_id: uuid.UUID):  # type: ignore[no-untyped-def]
    """Suspend an account."""
    svc = _get_admin_service()
    admin_id = uuid.UUID(get_jwt_identity())
    try:
        result = svc.suspend_account(account_id, admin_id=admin_id, ip_address=_get_client_ip())
    except AdminServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)
    return success_response(result)


@admin_bp.route("/accounts/<uuid:account_id>/unsuspend", methods=["POST"])
@require_platform_admin
def unsuspend_account(account_id: uuid.UUID):  # type: ignore[no-untyped-def]
    """Unsuspend an account."""
    svc = _get_admin_service()
    admin_id = uuid.UUID(get_jwt_identity())
    try:
        result = svc.unsuspend_account(account_id, admin_id=admin_id, ip_address=_get_client_ip())
    except AdminServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)
    return success_response(result)


@admin_bp.route("/accounts/<uuid:account_id>/plan", methods=["PUT"])
@require_platform_admin
def update_account_plan(account_id: uuid.UUID):  # type: ignore[no-untyped-def]
    """Change an account's plan tier."""
    body = request.get_json(force=True)
    plan_tier = body.get("plan_tier")
    if not plan_tier:
        return error_response("bad_request", "plan_tier is required.", status_code=400)

    svc = _get_admin_service()
    admin_id = uuid.UUID(get_jwt_identity())
    try:
        result = svc.update_account_plan(
            account_id, plan_tier, admin_id=admin_id, ip_address=_get_client_ip()
        )
    except AdminServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)
    return success_response(result)


# ── Users ───────────────────────────────────────────────────────


@admin_bp.route("/users", methods=["GET"])
@require_platform_admin
def list_users():  # type: ignore[no-untyped-def]
    """List all users with pagination and filters."""
    svc = _get_admin_service()
    account_id_str = request.args.get("account_id")
    try:
        result = svc.list_users(
            page=request.args.get("page", 1, type=int),
            per_page=request.args.get("per_page", 25, type=int),
            search=request.args.get("search"),
            account_id=uuid.UUID(account_id_str) if account_id_str else None,
            is_platform_admin=request.args.get("is_platform_admin", type=lambda v: v.lower() == "true") if request.args.get("is_platform_admin") else None,
        )
    except AdminServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)
    return success_response(result["users"], meta={"pagination": result["pagination"]})


@admin_bp.route("/users/<uuid:user_id>", methods=["GET"])
@require_platform_admin
def get_user(user_id: uuid.UUID):  # type: ignore[no-untyped-def]
    """Get detailed user information."""
    svc = _get_admin_service()
    try:
        result = svc.get_user(user_id)
    except AdminServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)
    return success_response(result)


@admin_bp.route("/users/<uuid:user_id>/reset-password", methods=["POST"])
@require_platform_admin
def reset_user_password(user_id: uuid.UUID):  # type: ignore[no-untyped-def]
    """Generate a password reset token for a user."""
    svc = _get_admin_service()
    admin_id = uuid.UUID(get_jwt_identity())
    try:
        result = svc.reset_user_password(user_id, admin_id=admin_id, ip_address=_get_client_ip())
    except AdminServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)
    return success_response(result)


@admin_bp.route("/users/<uuid:user_id>/toggle-admin", methods=["POST"])
@require_platform_admin
def toggle_platform_admin(user_id: uuid.UUID):  # type: ignore[no-untyped-def]
    """Promote or demote a user as platform admin."""
    svc = _get_admin_service()
    admin_id = uuid.UUID(get_jwt_identity())
    try:
        result = svc.toggle_platform_admin(user_id, admin_id=admin_id, ip_address=_get_client_ip())
    except AdminServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)
    return success_response(result)


# ── Impersonation ───────────────────────────────────────────────


@admin_bp.route("/users/<uuid:user_id>/impersonate", methods=["POST"])
@require_platform_admin
def impersonate_user(user_id: uuid.UUID):  # type: ignore[no-untyped-def]
    """Generate an impersonation token for a user."""
    svc = _get_admin_service()
    admin_id = uuid.UUID(get_jwt_identity())
    try:
        result = svc.impersonate_user(user_id, admin_id=admin_id, ip_address=_get_client_ip())
    except AdminServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)
    return success_response(result)


# ── Audit Logs ──────────────────────────────────────────────────


@admin_bp.route("/audit-logs", methods=["GET"])
@require_platform_admin
def list_audit_logs():  # type: ignore[no-untyped-def]
    """List admin audit logs with pagination."""
    svc = _get_admin_service()
    admin_id_str = request.args.get("admin_id")
    try:
        result = svc.list_audit_logs(
            page=request.args.get("page", 1, type=int),
            per_page=request.args.get("per_page", 50, type=int),
            admin_id=uuid.UUID(admin_id_str) if admin_id_str else None,
            action=request.args.get("action"),
        )
    except AdminServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)
    return success_response(result["logs"], meta={"pagination": result["pagination"]})
