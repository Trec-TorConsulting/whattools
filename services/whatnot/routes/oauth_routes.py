"""OAuth routes — Whatnot connection management (connect, callback, disconnect, status)."""

import os

from flask import Blueprint, current_app, request, session
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from services.shared.database import get_db
from services.shared.errors import error_response, success_response
from services.whatnot.services.oauth_service import OAuthService, OAuthServiceError

oauth_bp = Blueprint("whatnot_oauth", __name__)


def _get_account_id() -> str:
    return get_jwt()["account_id"]


@oauth_bp.route("/connect", methods=["GET"])
@jwt_required()
def connect():  # type: ignore[no-untyped-def]
    """Initiate Whatnot OAuth flow — returns authorization URL."""
    import uuid

    account_id = uuid.UUID(_get_account_id())
    redirect_uri = os.environ.get(
        "WHATNOT_REDIRECT_URI",
        request.host_url.rstrip("/") + "/api/v1/whatnot/callback",
    )

    db = get_db()
    svc = OAuthService(db)

    try:
        result = svc.get_authorize_url(account_id, redirect_uri)
    except OAuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    # Store state in session for CSRF validation
    session["whatnot_oauth_state"] = result["state"]

    return success_response({
        "authorize_url": result["url"],
    })


@oauth_bp.route("/callback", methods=["GET"])
@jwt_required()
def callback():  # type: ignore[no-untyped-def]
    """Handle OAuth callback — exchange code for tokens."""
    import uuid

    code = request.args.get("code")
    state = request.args.get("state")
    error = request.args.get("error")

    if error:
        return error_response("oauth_denied", f"Whatnot authorization denied: {error}", status_code=400)

    if not code:
        return error_response("missing_code", "Authorization code is required", status_code=400)

    # Validate CSRF state
    expected_state = session.pop("whatnot_oauth_state", None)
    if not expected_state or state != expected_state:
        return error_response("invalid_state", "Invalid OAuth state parameter", status_code=400)

    account_id = uuid.UUID(_get_account_id())
    redirect_uri = os.environ.get(
        "WHATNOT_REDIRECT_URI",
        request.host_url.rstrip("/") + "/api/v1/whatnot/callback",
    )

    db = get_db()
    svc = OAuthService(db)

    try:
        result = svc.exchange_code(code, redirect_uri, account_id)
    except OAuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@oauth_bp.route("/disconnect", methods=["POST"])
@jwt_required()
def disconnect():  # type: ignore[no-untyped-def]
    """Disconnect Whatnot account."""
    import uuid

    account_id = uuid.UUID(_get_account_id())
    db = get_db()
    svc = OAuthService(db)
    svc.disconnect(account_id)
    return success_response({"message": "Whatnot account disconnected."})


@oauth_bp.route("/status", methods=["GET"])
@jwt_required()
def status():  # type: ignore[no-untyped-def]
    """Get Whatnot connection status."""
    import uuid

    account_id = uuid.UUID(_get_account_id())
    db = get_db()
    svc = OAuthService(db)

    try:
        result = svc.get_status(account_id)
    except OAuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)
