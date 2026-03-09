"""Category routes — CRUD for item categories."""

import uuid

from flask import Blueprint, current_app, request
from flask_jwt_extended import get_jwt, jwt_required
from marshmallow import ValidationError

from services.inventory.schemas.schemas import CategoryCreateSchema, CategoryUpdateSchema
from services.inventory.services.inventory_service import InventoryService, InventoryServiceError
from services.shared.database import get_db
from services.shared.errors import error_response, success_response

categories_bp = Blueprint("categories", __name__)


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


@categories_bp.route("", methods=["POST"])
@jwt_required()
def create_category():  # type: ignore[no-untyped-def]
    """Create a new category."""
    schema = CategoryCreateSchema()
    try:
        data = schema.load(request.get_json(force=True))
    except ValidationError as e:
        return error_response("validation_error", str(e.messages), status_code=422)

    svc = _get_service()
    try:
        result = svc.create_category(data, actor_id=_get_actor_id())
    except InventoryServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result, status_code=201)


@categories_bp.route("", methods=["GET"])
@jwt_required()
def list_categories():  # type: ignore[no-untyped-def]
    """List all categories for the account."""
    svc = _get_service()
    result = svc.list_categories()
    return success_response({"categories": result})


@categories_bp.route("/<category_id>", methods=["GET"])
@jwt_required()
def get_category(category_id: str):  # type: ignore[no-untyped-def]
    """Get a single category by ID."""
    try:
        uid = uuid.UUID(category_id)
    except ValueError:
        return error_response("bad_request", "Invalid category ID.", status_code=400)

    svc = _get_service()
    try:
        result = svc.get_category(uid)
    except InventoryServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@categories_bp.route("/<category_id>", methods=["PUT"])
@jwt_required()
def update_category(category_id: str):  # type: ignore[no-untyped-def]
    """Update a category."""
    try:
        uid = uuid.UUID(category_id)
    except ValueError:
        return error_response("bad_request", "Invalid category ID.", status_code=400)

    schema = CategoryUpdateSchema()
    try:
        data = schema.load(request.get_json(force=True))
    except ValidationError as e:
        return error_response("validation_error", str(e.messages), status_code=422)

    svc = _get_service()
    try:
        result = svc.update_category(uid, data, actor_id=_get_actor_id())
    except InventoryServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@categories_bp.route("/<category_id>", methods=["DELETE"])
@jwt_required()
def delete_category(category_id: str):  # type: ignore[no-untyped-def]
    """Soft-delete a category."""
    try:
        uid = uuid.UUID(category_id)
    except ValueError:
        return error_response("bad_request", "Invalid category ID.", status_code=400)

    svc = _get_service()
    try:
        svc.delete_category(uid, actor_id=_get_actor_id())
    except InventoryServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response({"message": "Category deleted."})
