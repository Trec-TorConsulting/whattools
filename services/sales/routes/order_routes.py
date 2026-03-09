"""Order routes — CRUD, cancel, soft-delete/restore."""

import uuid

from flask import Blueprint, current_app, request
from flask_jwt_extended import get_jwt, jwt_required
from marshmallow import ValidationError

from services.sales.schemas.schemas import OrderCreateSchema, OrderListQuerySchema, OrderUpdateSchema
from services.sales.services.sales_service import SalesService, SalesServiceError
from services.shared.database import get_db
from services.shared.errors import error_response, success_response

orders_bp = Blueprint("orders", __name__)


def _get_service() -> SalesService:
    db = get_db()
    claims = get_jwt()
    account_id = uuid.UUID(claims["account_id"])
    publisher = current_app.config.get("_EVENT_PUBLISHER")
    return SalesService(db, account_id, event_publisher=publisher)


def _get_actor_id() -> uuid.UUID:
    claims = get_jwt()
    return uuid.UUID(claims["sub"])


@orders_bp.route("", methods=["POST"])
@jwt_required()
def create_order():  # type: ignore[no-untyped-def]
    """Create a new order."""
    schema = OrderCreateSchema()
    try:
        data = schema.load(request.get_json(force=True))
    except ValidationError as e:
        return error_response("validation_error", str(e.messages), status_code=422)

    svc = _get_service()
    try:
        result = svc.create_order(data, actor_id=_get_actor_id())
    except SalesServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result, status_code=201)


@orders_bp.route("", methods=["GET"])
@jwt_required()
def list_orders():  # type: ignore[no-untyped-def]
    """List orders with optional filters."""
    schema = OrderListQuerySchema()
    try:
        params = schema.load(request.args.to_dict())
    except ValidationError as e:
        return error_response("validation_error", str(e.messages), status_code=422)

    svc = _get_service()
    result = svc.list_orders(**params)
    return success_response(result)


@orders_bp.route("/<order_id>", methods=["GET"])
@jwt_required()
def get_order(order_id: str):  # type: ignore[no-untyped-def]
    """Get a single order by ID."""
    try:
        uid = uuid.UUID(order_id)
    except ValueError:
        return error_response("bad_request", "Invalid order ID.", status_code=400)

    svc = _get_service()
    try:
        result = svc.get_order(uid)
    except SalesServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@orders_bp.route("/<order_id>", methods=["PUT"])
@jwt_required()
def update_order(order_id: str):  # type: ignore[no-untyped-def]
    """Update an order."""
    try:
        uid = uuid.UUID(order_id)
    except ValueError:
        return error_response("bad_request", "Invalid order ID.", status_code=400)

    schema = OrderUpdateSchema()
    try:
        data = schema.load(request.get_json(force=True))
    except ValidationError as e:
        return error_response("validation_error", str(e.messages), status_code=422)

    svc = _get_service()
    try:
        result = svc.update_order(uid, data, actor_id=_get_actor_id())
    except SalesServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@orders_bp.route("/<order_id>", methods=["DELETE"])
@jwt_required()
def delete_order(order_id: str):  # type: ignore[no-untyped-def]
    """Soft-delete an order."""
    try:
        uid = uuid.UUID(order_id)
    except ValueError:
        return error_response("bad_request", "Invalid order ID.", status_code=400)

    svc = _get_service()
    try:
        svc.delete_order(uid, actor_id=_get_actor_id())
    except SalesServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response({"message": "Order deleted."})


@orders_bp.route("/<order_id>/cancel", methods=["POST"])
@jwt_required()
def cancel_order(order_id: str):  # type: ignore[no-untyped-def]
    """Cancel an order and restore inventory item."""
    try:
        uid = uuid.UUID(order_id)
    except ValueError:
        return error_response("bad_request", "Invalid order ID.", status_code=400)

    svc = _get_service()
    try:
        result = svc.cancel_order(uid, actor_id=_get_actor_id())
    except SalesServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@orders_bp.route("/deleted", methods=["GET"])
@jwt_required()
def list_deleted():  # type: ignore[no-untyped-def]
    """List soft-deleted orders within 30-day retention."""
    svc = _get_service()
    result = svc.list_deleted_orders()
    return success_response({"items": result})


@orders_bp.route("/<order_id>/restore", methods=["POST"])
@jwt_required()
def restore_order(order_id: str):  # type: ignore[no-untyped-def]
    """Restore a soft-deleted order."""
    try:
        uid = uuid.UUID(order_id)
    except ValueError:
        return error_response("bad_request", "Invalid order ID.", status_code=400)

    svc = _get_service()
    try:
        result = svc.restore_order(uid, actor_id=_get_actor_id())
    except SalesServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)
