"""CSV import routes — upload, map columns, check status."""

import uuid

from flask import Blueprint, current_app, request
from flask_jwt_extended import get_jwt, jwt_required
from marshmallow import ValidationError

from services.inventory.schemas.schemas import CSVMappingSchema
from services.inventory.services.csv_import_service import CSVImportService, InventoryServiceError
from services.shared.database import get_db
from services.shared.errors import error_response, success_response

csv_bp = Blueprint("csv", __name__)


def _get_service() -> CSVImportService:
    db = get_db()
    claims = get_jwt()
    account_id = uuid.UUID(claims["account_id"])
    publisher = current_app.config.get("_EVENT_PUBLISHER")
    item_limit = claims.get("item_limit", 50)
    return CSVImportService(db, account_id, event_publisher=publisher, item_limit=item_limit)


def _get_actor_id() -> uuid.UUID:
    claims = get_jwt()
    return uuid.UUID(claims["sub"])


@csv_bp.route("/upload", methods=["POST"])
@jwt_required()
def upload_csv():  # type: ignore[no-untyped-def]
    """Upload a CSV file for import.

    Expects multipart/form-data with a 'file' field.
    """
    if "file" not in request.files:
        return error_response("bad_request", "No file provided.", status_code=400)

    file = request.files["file"]
    if not file.filename:
        return error_response("bad_request", "No filename.", status_code=400)

    if not file.filename.lower().endswith(".csv"):
        return error_response("bad_request", "File must be a CSV.", status_code=400)

    content = file.read()

    svc = _get_service()
    try:
        result = svc.upload_csv(content, file.filename, actor_id=_get_actor_id())
    except InventoryServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result, status_code=201)


@csv_bp.route("/<job_id>/map", methods=["POST"])
@jwt_required()
def submit_mapping(job_id: str):  # type: ignore[no-untyped-def]
    """Submit column mapping for a pending CSV import job."""
    try:
        uid = uuid.UUID(job_id)
    except ValueError:
        return error_response("bad_request", "Invalid job ID.", status_code=400)

    schema = CSVMappingSchema()
    try:
        data = schema.load(request.get_json(force=True))
    except ValidationError as e:
        return error_response("validation_error", str(e.messages), status_code=422)

    svc = _get_service()
    try:
        result = svc.submit_mapping(uid, data["mapping"], actor_id=_get_actor_id())
    except InventoryServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@csv_bp.route("/<job_id>", methods=["GET"])
@jwt_required()
def get_job_status(job_id: str):  # type: ignore[no-untyped-def]
    """Get the status of a CSV import job."""
    try:
        uid = uuid.UUID(job_id)
    except ValueError:
        return error_response("bad_request", "Invalid job ID.", status_code=400)

    svc = _get_service()
    try:
        result = svc.get_job_status(uid)
    except InventoryServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)
