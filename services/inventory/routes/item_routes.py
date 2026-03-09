"""Item routes — CRUD, search/filter, soft-delete/restore."""

import uuid

from flask import Blueprint, current_app, request
from flask_jwt_extended import get_jwt, jwt_required
from marshmallow import ValidationError

from services.inventory.schemas.schemas import (
    ItemCreateSchema,
    ItemListQuerySchema,
    ItemUpdateSchema,
)
from services.inventory.services.inventory_service import InventoryService, InventoryServiceError
from services.shared.database import get_db
from services.shared.errors import error_response, success_response

items_bp = Blueprint("items", __name__)


def _get_service() -> InventoryService:
    db = get_db()
    claims = get_jwt()
    account_id = uuid.UUID(claims["account_id"])
    publisher = current_app.config.get("_EVENT_PUBLISHER")
    item_limit = claims.get("item_limit", 50)
    return InventoryService(db, account_id, event_publisher=publisher, item_limit=item_limit)


def _get_actor_id() -> uuid.UUID:
    claims = get_jwt()
    return uuid.UUID(claims["sub"])


@items_bp.route("", methods=["POST"])
@jwt_required()
def create_item():  # type: ignore[no-untyped-def]
    """Create a new inventory item."""
    schema = ItemCreateSchema()
    try:
        data = schema.load(request.get_json(force=True))
    except ValidationError as e:
        return error_response("validation_error", str(e.messages), status_code=422)

    svc = _get_service()
    try:
        result = svc.create_item(data, actor_id=_get_actor_id())
    except InventoryServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result, status_code=201)


@items_bp.route("", methods=["GET"])
@jwt_required()
def list_items():  # type: ignore[no-untyped-def]
    """List items with optional search and filters."""
    schema = ItemListQuerySchema()
    try:
        params = schema.load(request.args.to_dict())
    except ValidationError as e:
        return error_response("validation_error", str(e.messages), status_code=422)

    svc = _get_service()
    result = svc.list_items(**params)
    return success_response(result)


@items_bp.route("/<item_id>", methods=["GET"])
@jwt_required()
def get_item(item_id: str):  # type: ignore[no-untyped-def]
    """Get a single item by ID."""
    try:
        uid = uuid.UUID(item_id)
    except ValueError:
        return error_response("bad_request", "Invalid item ID.", status_code=400)

    svc = _get_service()
    try:
        result = svc.get_item(uid)
    except InventoryServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@items_bp.route("/<item_id>", methods=["PUT"])
@jwt_required()
def update_item(item_id: str):  # type: ignore[no-untyped-def]
    """Update an inventory item."""
    try:
        uid = uuid.UUID(item_id)
    except ValueError:
        return error_response("bad_request", "Invalid item ID.", status_code=400)

    schema = ItemUpdateSchema()
    try:
        data = schema.load(request.get_json(force=True))
    except ValidationError as e:
        return error_response("validation_error", str(e.messages), status_code=422)

    svc = _get_service()
    try:
        result = svc.update_item(uid, data, actor_id=_get_actor_id())
    except InventoryServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@items_bp.route("/<item_id>", methods=["DELETE"])
@jwt_required()
def delete_item(item_id: str):  # type: ignore[no-untyped-def]
    """Soft-delete an inventory item."""
    try:
        uid = uuid.UUID(item_id)
    except ValueError:
        return error_response("bad_request", "Invalid item ID.", status_code=400)

    svc = _get_service()
    try:
        svc.delete_item(uid, actor_id=_get_actor_id())
    except InventoryServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response({"message": "Item deleted."})


@items_bp.route("/deleted", methods=["GET"])
@jwt_required()
def list_deleted():  # type: ignore[no-untyped-def]
    """List soft-deleted items within 30-day retention."""
    svc = _get_service()
    result = svc.list_deleted_items()
    return success_response({"items": result})


@items_bp.route("/<item_id>/restore", methods=["POST"])
@jwt_required()
def restore_item(item_id: str):  # type: ignore[no-untyped-def]
    """Restore a soft-deleted item."""
    try:
        uid = uuid.UUID(item_id)
    except ValueError:
        return error_response("bad_request", "Invalid item ID.", status_code=400)

    svc = _get_service()
    try:
        result = svc.restore_item(uid, actor_id=_get_actor_id())
    except InventoryServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)
