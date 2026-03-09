"""Export routes — async report generation endpoints."""

import os
import uuid
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, request, send_file
from flask_jwt_extended import get_jwt, jwt_required

from services.analytics.models.models import ExportJob, ExportStatus, VALID_REPORT_TYPES, VALID_FORMATS
from services.analytics.repositories.export_repository import ExportRepository
from services.analytics.schemas.schemas import ExportCreateSchema, ExportResponseSchema
from services.shared.database import get_db
from services.shared.errors import error_response, success_response

export_bp = Blueprint("exports", __name__)

_create_schema = ExportCreateSchema()
_response_schema = ExportResponseSchema()


@export_bp.route("", methods=["POST"])
@jwt_required()
def create_export():  # type: ignore[no-untyped-def]
    """Create a new async export job."""
    data = request.get_json(silent=True) or {}
    errors = _create_schema.validate(data)
    if errors:
        return error_response("validation_error", errors, status_code=422)

    parsed = _create_schema.load(data)
    claims = get_jwt()
    account_id = uuid.UUID(claims["account_id"])
    db = get_db()
    repo = ExportRepository(db)

    now = datetime.now(timezone.utc)
    job = ExportJob(
        account_id=account_id,
        report_type=parsed["report_type"],
        format=parsed["format"],
        period=parsed.get("period", "30d"),
        status=ExportStatus.PENDING,
        expires_at=now + timedelta(days=7),
    )
    repo.create(job)
    db.commit()

    # Enqueue Celery task
    try:
        from services.analytics.tasks.export_tasks import generate_export
        generate_export.delay(
            str(job.id),
            str(account_id),
            job.report_type,
            job.format,
            job.period,
        )
    except Exception:
        # If Celery broker is unavailable, still return the job (it can be retried)
        pass

    return success_response(_response_schema.dump(job), status_code=201)


@export_bp.route("", methods=["GET"])
@jwt_required()
def list_exports():  # type: ignore[no-untyped-def]
    """List all export jobs for the authenticated account."""
    claims = get_jwt()
    account_id = uuid.UUID(claims["account_id"])
    db = get_db()
    repo = ExportRepository(db)

    jobs = repo.list_by_account(account_id)
    return success_response([_response_schema.dump(j) for j in jobs])


@export_bp.route("/<export_id>", methods=["GET"])
@jwt_required()
def get_export(export_id: str):  # type: ignore[no-untyped-def]
    """Get the status of an export job."""
    try:
        eid = uuid.UUID(export_id)
    except ValueError:
        return error_response("validation_error", "Invalid export ID", status_code=422)

    claims = get_jwt()
    account_id = uuid.UUID(claims["account_id"])
    db = get_db()
    repo = ExportRepository(db)

    job = repo.get_by_id(eid, account_id)
    if job is None:
        return error_response("not_found", "Export job not found", status_code=404)

    return success_response(_response_schema.dump(job))


@export_bp.route("/<export_id>/download", methods=["GET"])
@jwt_required()
def download_export(export_id: str):  # type: ignore[no-untyped-def]
    """Download the generated export file."""
    try:
        eid = uuid.UUID(export_id)
    except ValueError:
        return error_response("validation_error", "Invalid export ID", status_code=422)

    claims = get_jwt()
    account_id = uuid.UUID(claims["account_id"])
    db = get_db()
    repo = ExportRepository(db)

    job = repo.get_by_id(eid, account_id)
    if job is None:
        return error_response("not_found", "Export job not found", status_code=404)

    if job.status != ExportStatus.COMPLETED:
        return error_response("conflict", f"Export is {job.status}, not ready for download", status_code=409)

    if not job.file_path or not os.path.exists(job.file_path):
        return error_response("not_found", "Export file no longer available", status_code=404)

    # Determine mimetype
    if job.file_path.endswith(".pdf"):
        mimetype = "application/pdf"
    elif job.file_path.endswith(".zip"):
        mimetype = "application/zip"
    else:
        mimetype = "text/csv"

    filename = os.path.basename(job.file_path)
    return send_file(job.file_path, mimetype=mimetype, as_attachment=True, download_name=filename)
