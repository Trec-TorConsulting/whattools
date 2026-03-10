"""Order sync routes — pull orders, push tracking, cancel orders."""

import uuid

from flask import Blueprint, request
from flask_jwt_extended import get_jwt, jwt_required

from services.shared.database import get_db
from services.shared.errors import error_response, success_response
from services.whatnot.graphql.client import WhatnotClient
from services.whatnot.services.oauth_service import OAuthService, OAuthServiceError
from services.whatnot.services.order_service import OrderSyncService, OrderServiceError

order_bp = Blueprint("whatnot_orders", __name__)


def _get_account_id() -> uuid.UUID:
    return uuid.UUID(get_jwt()["account_id"])


def _get_whatnot_client(account_id: uuid.UUID) -> WhatnotClient:
    db = get_db()
    oauth_svc = OAuthService(db)
    access_token = oauth_svc.get_access_token(account_id)
    return WhatnotClient(access_token)


@order_bp.route("/sync", methods=["POST"])
@jwt_required()
def sync_orders():  # type: ignore[no-untyped-def]
    """Pull orders from Whatnot and sync to local database."""
    account_id = _get_account_id()
    db = get_db()

    try:
        client = _get_whatnot_client(account_id)
    except OAuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    svc = OrderSyncService(db, account_id, client)
    try:
        result = svc.pull_orders()
    except OrderServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@order_bp.route("/<order_id>/tracking", methods=["POST"])
@jwt_required()
def push_tracking(order_id: str):  # type: ignore[no-untyped-def]
    """Push a tracking code to Whatnot for an order."""
    account_id = _get_account_id()
    data = request.get_json(force=True)
    tracking_company = data.get("tracking_company", "")
    tracking_number = data.get("tracking_number", "")

    if not tracking_company or not tracking_number:
        return error_response(
            "validation_error",
            "tracking_company and tracking_number are required",
            status_code=422,
        )

    db = get_db()
    try:
        client = _get_whatnot_client(account_id)
    except OAuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    svc = OrderSyncService(db, account_id, client)
    try:
        result = svc.push_tracking(uuid.UUID(order_id), tracking_company, tracking_number)
    except OrderServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@order_bp.route("/<order_id>/cancel", methods=["POST"])
@jwt_required()
def cancel_order(order_id: str):  # type: ignore[no-untyped-def]
    """Cancel an order on Whatnot."""
    account_id = _get_account_id()
    db = get_db()

    try:
        client = _get_whatnot_client(account_id)
    except OAuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    svc = OrderSyncService(db, account_id, client)
    try:
        result = svc.cancel_order(uuid.UUID(order_id))
    except OrderServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)
