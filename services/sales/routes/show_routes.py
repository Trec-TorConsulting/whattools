"""Show routes — CRUD, status transitions."""

import uuid

from flask import Blueprint, current_app, request
from flask_jwt_extended import get_jwt, jwt_required
from marshmallow import ValidationError

from services.sales.schemas.schemas import ShowCreateSchema, ShowListQuerySchema, ShowUpdateSchema
from services.sales.services.sales_service import SalesService, SalesServiceError
from services.shared.database import get_db
from services.shared.errors import error_response, success_response

shows_bp = Blueprint("shows", __name__)


def _get_service() -> SalesService:
    db = get_db()
    claims = get_jwt()
    account_id = uuid.UUID(claims["account_id"])
    publisher = current_app.config.get("_EVENT_PUBLISHER")
    return SalesService(db, account_id, event_publisher=publisher)


def _get_actor_id() -> uuid.UUID:
    claims = get_jwt()
    return uuid.UUID(claims["sub"])


@shows_bp.route("", methods=["POST"])
@jwt_required()
def create_show():  # type: ignore[no-untyped-def]
    """Create a new show."""
    schema = ShowCreateSchema()
    try:
        data = schema.load(request.get_json(force=True))
    except ValidationError as e:
        return error_response("validation_error", str(e.messages), status_code=422)

    svc = _get_service()
    try:
        result = svc.create_show(data, actor_id=_get_actor_id())
    except SalesServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result, status_code=201)


@shows_bp.route("", methods=["GET"])
@jwt_required()
def list_shows():  # type: ignore[no-untyped-def]
    """List shows with optional filters."""
    schema = ShowListQuerySchema()
    try:
        params = schema.load(request.args.to_dict())
    except ValidationError as e:
        return error_response("validation_error", str(e.messages), status_code=422)

    svc = _get_service()
    result = svc.list_shows(**params)
    return success_response(result)


@shows_bp.route("/<show_id>", methods=["GET"])
@jwt_required()
def get_show(show_id: str):  # type: ignore[no-untyped-def]
    """Get a single show by ID."""
    try:
        uid = uuid.UUID(show_id)
    except ValueError:
        return error_response("bad_request", "Invalid show ID.", status_code=400)

    svc = _get_service()
    try:
        result = svc.get_show(uid)
    except SalesServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@shows_bp.route("/<show_id>", methods=["PUT"])
@jwt_required()
def update_show(show_id: str):  # type: ignore[no-untyped-def]
    """Update a show."""
    try:
        uid = uuid.UUID(show_id)
    except ValueError:
        return error_response("bad_request", "Invalid show ID.", status_code=400)

    schema = ShowUpdateSchema()
    try:
        data = schema.load(request.get_json(force=True))
    except ValidationError as e:
        return error_response("validation_error", str(e.messages), status_code=422)

    svc = _get_service()
    try:
        result = svc.update_show(uid, data, actor_id=_get_actor_id())
    except SalesServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@shows_bp.route("/<show_id>", methods=["DELETE"])
@jwt_required()
def delete_show(show_id: str):  # type: ignore[no-untyped-def]
    """Soft-delete a show."""
    try:
        uid = uuid.UUID(show_id)
    except ValueError:
        return error_response("bad_request", "Invalid show ID.", status_code=400)

    svc = _get_service()
    try:
        svc.delete_show(uid, actor_id=_get_actor_id())
    except SalesServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response({"message": "Show deleted."})


@shows_bp.route("/<show_id>/start", methods=["POST"])
@jwt_required()
def start_show(show_id: str):  # type: ignore[no-untyped-def]
    """Start a planned show (transition to live)."""
    try:
        uid = uuid.UUID(show_id)
    except ValueError:
        return error_response("bad_request", "Invalid show ID.", status_code=400)

    svc = _get_service()
    try:
        result = svc.start_show(uid, actor_id=_get_actor_id())
    except SalesServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@shows_bp.route("/<show_id>/complete", methods=["POST"])
@jwt_required()
def complete_show(show_id: str):  # type: ignore[no-untyped-def]
    """Complete a live show."""
    try:
        uid = uuid.UUID(show_id)
    except ValueError:
        return error_response("bad_request", "Invalid show ID.", status_code=400)

    svc = _get_service()
    try:
        result = svc.complete_show(uid, actor_id=_get_actor_id())
    except SalesServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@shows_bp.route("/<show_id>/cancel", methods=["POST"])
@jwt_required()
def cancel_show(show_id: str):  # type: ignore[no-untyped-def]
    """Cancel a show and all its pending orders."""
    try:
        uid = uuid.UUID(show_id)
    except ValueError:
        return error_response("bad_request", "Invalid show ID.", status_code=400)

    svc = _get_service()
    try:
        result = svc.cancel_show(uid, actor_id=_get_actor_id())
    except SalesServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@shows_bp.route("/<show_id>/orders", methods=["GET"])
@jwt_required()
def list_show_orders(show_id: str):  # type: ignore[no-untyped-def]
    """List all orders for a specific show with summary."""
    try:
        uid = uuid.UUID(show_id)
    except ValueError:
        return error_response("bad_request", "Invalid show ID.", status_code=400)

    svc = _get_service()
    try:
        result = svc.list_show_orders(uid)
    except SalesServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)
