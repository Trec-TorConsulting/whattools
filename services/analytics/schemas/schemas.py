"""Marshmallow schemas for analytics export endpoints."""

from marshmallow import Schema, fields, validate

from services.analytics.models.models import VALID_FORMATS, VALID_REPORT_TYPES


class ExportCreateSchema(Schema):
    """Schema for creating an export job."""

    report_type = fields.String(
        required=True,
        validate=validate.OneOf(sorted(VALID_REPORT_TYPES)),
    )
    format = fields.String(
        required=True,
        validate=validate.OneOf(sorted(VALID_FORMATS)),
    )
    period = fields.String(
        load_default="30d",
        validate=validate.OneOf(["7d", "30d", "90d", "365d", "all"]),
    )


class ExportResponseSchema(Schema):
    """Schema for export job response."""

    id = fields.UUID(dump_only=True)
    account_id = fields.UUID(dump_only=True)
    report_type = fields.String()
    format = fields.String()
    period = fields.String()
    status = fields.String()
    file_size = fields.Integer()
    error_message = fields.String()
    expires_at = fields.DateTime()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
