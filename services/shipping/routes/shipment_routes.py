"""Shipment routes — CRUD, status transitions, bulk, overdue, soft-delete/restore."""

import uuid

from flask import Blueprint, current_app, request
from flask_jwt_extended import get_jwt, jwt_required
from marshmallow import ValidationError

from services.shipping.schemas.schemas import (
    BulkShipmentCreateSchema,
    ShipmentCreateSchema,
    ShipmentListQuerySchema,
    ShipmentUpdateSchema,
)
from services.shipping.services.shipping_service import ShippingService, ShippingServiceError
from services.shared.database import get_db
from services.shared.errors import error_response, success_response

shipments_bp = Blueprint("shipments", __name__)


def _get_service() -> ShippingService:
    db = get_db()
    claims = get_jwt()
    account_id = uuid.UUID(claims["account_id"])
    publisher = current_app.config.get("_EVENT_PUBLISHER")
    provider = current_app.config.get("_SHIPPING_PROVIDER")
    return ShippingService(db, account_id, event_publisher=publisher, shipping_provider=provider)


def _get_actor_id() -> uuid.UUID:
    claims = get_jwt()
    return uuid.UUID(claims["sub"])


@shipments_bp.route("", methods=["POST"])
@jwt_required()
def create_shipment():  # type: ignore[no-untyped-def]
    """Create a new shipment."""
    schema = ShipmentCreateSchema()
    try:
        data = schema.load(request.get_json(force=True))
    except ValidationError as e:
        return error_response("validation_error", str(e.messages), status_code=422)

    svc = _get_service()
    try:
        result = svc.create_shipment(data, actor_id=_get_actor_id())
    except ShippingServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result, status_code=201)


@shipments_bp.route("", methods=["GET"])
@jwt_required()
def list_shipments():  # type: ignore[no-untyped-def]
    """List shipments with optional filters."""
    schema = ShipmentListQuerySchema()
    try:
        params = schema.load(request.args.to_dict())
    except ValidationError as e:
        return error_response("validation_error", str(e.messages), status_code=422)

    svc = _get_service()
    result = svc.list_shipments(**params)
    return success_response(result)


@shipments_bp.route("/<shipment_id>", methods=["GET"])
@jwt_required()
def get_shipment(shipment_id: str):  # type: ignore[no-untyped-def]
    """Get a single shipment by ID."""
    try:
        uid = uuid.UUID(shipment_id)
    except ValueError:
        return error_response("bad_request", "Invalid shipment ID.", status_code=400)

    svc = _get_service()
    try:
        result = svc.get_shipment(uid)
    except ShippingServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@shipments_bp.route("/<shipment_id>", methods=["PUT"])
@jwt_required()
def update_shipment(shipment_id: str):  # type: ignore[no-untyped-def]
    """Update a shipment."""
    try:
        uid = uuid.UUID(shipment_id)
    except ValueError:
        return error_response("bad_request", "Invalid shipment ID.", status_code=400)

    schema = ShipmentUpdateSchema()
    try:
        data = schema.load(request.get_json(force=True))
    except ValidationError as e:
        return error_response("validation_error", str(e.messages), status_code=422)

    svc = _get_service()
    try:
        result = svc.update_shipment(uid, data, actor_id=_get_actor_id())
    except ShippingServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@shipments_bp.route("/<shipment_id>", methods=["DELETE"])
@jwt_required()
def delete_shipment(shipment_id: str):  # type: ignore[no-untyped-def]
    """Soft-delete a shipment."""
    try:
        uid = uuid.UUID(shipment_id)
    except ValueError:
        return error_response("bad_request", "Invalid shipment ID.", status_code=400)

    svc = _get_service()
    try:
        svc.delete_shipment(uid, actor_id=_get_actor_id())
    except ShippingServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response({"message": "Shipment deleted."})


@shipments_bp.route("/<shipment_id>/ship", methods=["POST"])
@jwt_required()
def mark_shipped(shipment_id: str):  # type: ignore[no-untyped-def]
    """Mark a shipment as shipped."""
    try:
        uid = uuid.UUID(shipment_id)
    except ValueError:
        return error_response("bad_request", "Invalid shipment ID.", status_code=400)

    svc = _get_service()
    try:
        result = svc.transition_shipment(uid, "shipped", actor_id=_get_actor_id())
    except ShippingServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@shipments_bp.route("/<shipment_id>/deliver", methods=["POST"])
@jwt_required()
def mark_delivered(shipment_id: str):  # type: ignore[no-untyped-def]
    """Mark a shipment as delivered."""
    try:
        uid = uuid.UUID(shipment_id)
    except ValueError:
        return error_response("bad_request", "Invalid shipment ID.", status_code=400)

    svc = _get_service()
    try:
        result = svc.transition_shipment(uid, "delivered", actor_id=_get_actor_id())
    except ShippingServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@shipments_bp.route("/<shipment_id>/cancel", methods=["POST"])
@jwt_required()
def cancel_shipment(shipment_id: str):  # type: ignore[no-untyped-def]
    """Cancel a shipment."""
    try:
        uid = uuid.UUID(shipment_id)
    except ValueError:
        return error_response("bad_request", "Invalid shipment ID.", status_code=400)

    svc = _get_service()
    try:
        result = svc.transition_shipment(uid, "cancelled", actor_id=_get_actor_id())
    except ShippingServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@shipments_bp.route("/<shipment_id>/label", methods=["POST"])
@jwt_required()
def create_label(shipment_id: str):  # type: ignore[no-untyped-def]
    """Create a shipping label for a pending shipment."""
    try:
        uid = uuid.UUID(shipment_id)
    except ValueError:
        return error_response("bad_request", "Invalid shipment ID.", status_code=400)

    svc = _get_service()
    try:
        result = svc.create_label(uid, actor_id=_get_actor_id())
    except ShippingServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@shipments_bp.route("/bulk", methods=["POST"])
@jwt_required()
def bulk_create_shipments():  # type: ignore[no-untyped-def]
    """Bulk create shipments for all pending orders in a show."""
    schema = BulkShipmentCreateSchema()
    try:
        data = schema.load(request.get_json(force=True))
    except ValidationError as e:
        return error_response("validation_error", str(e.messages), status_code=422)

    svc = _get_service()
    try:
        result = svc.bulk_create_shipments(data["show_id"], data, actor_id=_get_actor_id())
    except ShippingServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result, status_code=201)


@shipments_bp.route("/overdue", methods=["GET"])
@jwt_required()
def list_overdue():  # type: ignore[no-untyped-def]
    """List overdue shipments past their ship-by date."""
    svc = _get_service()
    result = svc.list_overdue_shipments()
    return success_response({"items": result})


@shipments_bp.route("/deleted", methods=["GET"])
@jwt_required()
def list_deleted():  # type: ignore[no-untyped-def]
    """List soft-deleted shipments within 30-day retention."""
    svc = _get_service()
    result = svc.list_deleted_shipments()
    return success_response({"items": result})


@shipments_bp.route("/<shipment_id>/restore", methods=["POST"])
@jwt_required()
def restore_shipment(shipment_id: str):  # type: ignore[no-untyped-def]
    """Restore a soft-deleted shipment."""
    try:
        uid = uuid.UUID(shipment_id)
    except ValueError:
        return error_response("bad_request", "Invalid shipment ID.", status_code=400)

    svc = _get_service()
    try:
        result = svc.restore_shipment(uid, actor_id=_get_actor_id())
    except ShippingServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)
