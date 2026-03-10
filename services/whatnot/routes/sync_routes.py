"""Sync management routes — trigger syncs, get status/history."""

import uuid

from flask import Blueprint
from flask_jwt_extended import get_jwt, jwt_required

from services.shared.database import get_db
from services.shared.errors import error_response, success_response
from services.whatnot.graphql.client import WhatnotClient
from services.whatnot.repositories.whatnot_repository import SyncLogRepository
from services.whatnot.services.livestream_service import LivestreamService
from services.whatnot.services.oauth_service import OAuthService, OAuthServiceError
from services.whatnot.services.order_service import OrderSyncService
from services.whatnot.services.product_service import ProductService

sync_bp = Blueprint("whatnot_sync", __name__)


def _get_account_id() -> uuid.UUID:
    return uuid.UUID(get_jwt()["account_id"])


def _get_whatnot_client(account_id: uuid.UUID) -> WhatnotClient:
    db = get_db()
    oauth_svc = OAuthService(db)
    access_token = oauth_svc.get_access_token(account_id)
    return WhatnotClient(access_token)


@sync_bp.route("/now", methods=["POST"])
@jwt_required()
def sync_now():  # type: ignore[no-untyped-def]
    """Trigger an immediate full sync of all data types."""
    account_id = _get_account_id()
    db = get_db()

    try:
        client = _get_whatnot_client(account_id)
    except OAuthServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    results = {}

    # Sync products
    try:
        product_svc = ProductService(db, account_id, client)
        results["products"] = product_svc.pull_products()
    except Exception as exc:
        results["products"] = {"error": str(exc)}

    # Sync orders
    try:
        order_svc = OrderSyncService(db, account_id, client)
        results["orders"] = order_svc.pull_orders()
    except Exception as exc:
        results["orders"] = {"error": str(exc)}

    # Sync livestreams
    try:
        livestream_svc = LivestreamService(db, account_id, client)
        results["livestreams"] = livestream_svc.pull_livestreams()
    except Exception as exc:
        results["livestreams"] = {"error": str(exc)}

    return success_response(results)


@sync_bp.route("/status", methods=["GET"])
@jwt_required()
def sync_status():  # type: ignore[no-untyped-def]
    """Get sync history and status."""
    account_id = _get_account_id()
    db = get_db()

    repo = SyncLogRepository(db, account_id)
    logs = repo.get_latest(limit=50)

    # Get latest per type
    latest = {}
    for sync_type in ("products", "orders", "livestreams", "listings", "full"):
        last = repo.get_last_successful(sync_type)
        if last:
            latest[sync_type] = {
                "completed_at": last.completed_at.isoformat() if last.completed_at else None,
                "items_synced": last.items_synced,
            }

    history = [
        {
            "id": str(log.id),
            "sync_type": log.sync_type,
            "status": log.status,
            "started_at": log.started_at.isoformat(),
            "completed_at": log.completed_at.isoformat() if log.completed_at else None,
            "items_synced": log.items_synced,
            "items_created": log.items_created,
            "items_updated": log.items_updated,
            "items_failed": log.items_failed,
            "error_message": log.error_message,
        }
        for log in logs
    ]

    return success_response({
        "latest": latest,
        "history": history,
    })
