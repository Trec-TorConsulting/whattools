"""Packing list routes — generate structured packing lists for shows."""

import uuid

from flask import Blueprint
from flask_jwt_extended import get_jwt, jwt_required

from services.shipping.services.shipping_service import ShippingService, ShippingServiceError
from services.shared.database import get_db
from services.shared.errors import error_response, success_response

from flask import current_app

packing_lists_bp = Blueprint("packing_lists", __name__)


def _get_service() -> ShippingService:
    db = get_db()
    claims = get_jwt()
    account_id = uuid.UUID(claims["account_id"])
    publisher = current_app.config.get("_EVENT_PUBLISHER")
    provider = current_app.config.get("_SHIPPING_PROVIDER")
    return ShippingService(db, account_id, event_publisher=publisher, shipping_provider=provider)


@packing_lists_bp.route("/<show_id>", methods=["GET"])
@jwt_required()
def get_packing_list(show_id: str):  # type: ignore[no-untyped-def]
    """Generate a packing list for a show."""
    try:
        uid = uuid.UUID(show_id)
    except ValueError:
        return error_response("bad_request", "Invalid show ID.", status_code=400)

    svc = _get_service()
    try:
        result = svc.generate_packing_list(uid)
    except ShippingServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)
