"""Livestream sync routes."""

import uuid

from flask import Blueprint
from flask_jwt_extended import get_jwt, jwt_required

from services.shared.database import get_db
from services.shared.errors import error_response, success_response
from services.whatnot.graphql.client import WhatnotClient
from services.whatnot.services.livestream_service import LivestreamService, LivestreamServiceError
from services.whatnot.services.oauth_service import OAuthService, OAuthServiceError

livestream_bp = Blueprint("whatnot_livestreams", __name__)


def _get_account_id() -> uuid.UUID:
    return uuid.UUID(get_jwt()["account_id"])


def _get_whatnot_client(account_id: uuid.UUID) -> WhatnotClient:
    db = get_db()
    oauth_svc = OAuthService(db)
    access_token = oauth_svc.get_access_token(account_id)
    return WhatnotClient(access_token)


@livestream_bp.route("/sync", methods=["POST"])
@jwt_required()
def sync_livestreams():  # type: ignore[no-untyped-def]
    """Pull livestreams from Whatnot and sync to local shows."""
    account_id = _get_account_id()
    db = get_db()

    try:
        client = _get_whatnot_client(account_id)
    except OAuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    svc = LivestreamService(db, account_id, client)
    try:
        result = svc.pull_livestreams()
    except LivestreamServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)
