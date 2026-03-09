"""Marshmallow schemas for inventory service request/response validation."""

from marshmallow import Schema, fields, validate


class ItemCreateSchema(Schema):
    """Schema for creating an inventory item."""

    name = fields.String(required=True, validate=validate.Length(min=1, max=255))
    description = fields.String(load_default="", validate=validate.Length(max=5000))
    category_id = fields.UUID(load_default=None, allow_none=True)
    cogs = fields.Float(load_default=0.0, validate=validate.Range(min=0))
    quantity = fields.Integer(load_default=1, validate=validate.Range(min=0))
    status = fields.String(
        load_default="available",
        validate=validate.OneOf(["available", "sold", "reserved", "listed"]),
    )


class ItemUpdateSchema(Schema):
    """Schema for updating an inventory item (partial)."""

    name = fields.String(validate=validate.Length(min=1, max=255))
    description = fields.String(validate=validate.Length(max=5000))
    category_id = fields.UUID(allow_none=True)
    cogs = fields.Float(validate=validate.Range(min=0))
    quantity = fields.Integer(validate=validate.Range(min=0))
    status = fields.String(
        validate=validate.OneOf(["available", "sold", "reserved", "listed"]),
    )


class ItemResponseSchema(Schema):
    """Schema for inventory item response."""

    id = fields.UUID(dump_only=True)
    account_id = fields.UUID(dump_only=True)
    name = fields.String(dump_only=True)
    description = fields.String(dump_only=True)
    category_id = fields.UUID(dump_only=True, allow_none=True)
    cogs = fields.Float(dump_only=True)
    quantity = fields.Integer(dump_only=True)
    status = fields.String(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    deleted_at = fields.DateTime(dump_only=True, allow_none=True)


class ItemListQuerySchema(Schema):
    """Schema for item list/search query parameters."""

    cursor = fields.String(load_default=None)
    limit = fields.Integer(load_default=50, validate=validate.Range(min=1, max=100))
    search = fields.String(load_default=None)
    category_id = fields.UUID(load_default=None)
    status = fields.String(
        load_default=None,
        validate=validate.OneOf(["available", "sold", "reserved", "listed"]),
    )
    min_cogs = fields.Float(load_default=None, validate=validate.Range(min=0))
    max_cogs = fields.Float(load_default=None, validate=validate.Range(min=0))


class CategoryCreateSchema(Schema):
    """Schema for creating a category."""

    name = fields.String(required=True, validate=validate.Length(min=1, max=255))
    description = fields.String(load_default="", validate=validate.Length(max=2000))


class CategoryUpdateSchema(Schema):
    """Schema for updating a category."""

    name = fields.String(validate=validate.Length(min=1, max=255))
    description = fields.String(validate=validate.Length(max=2000))


class CategoryResponseSchema(Schema):
    """Schema for category response."""

    id = fields.UUID(dump_only=True)
    account_id = fields.UUID(dump_only=True)
    name = fields.String(dump_only=True)
    description = fields.String(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class CSVUploadResponseSchema(Schema):
    """Schema for CSV upload response (headers + preview)."""

    job_id = fields.UUID(dump_only=True)
    headers = fields.List(fields.String(), dump_only=True)
    preview_rows = fields.List(fields.Dict(), dump_only=True)
    status = fields.String(dump_only=True)


class CSVMappingSchema(Schema):
    """Schema for submitting column mapping for a CSV import job."""

    mapping = fields.Dict(
        keys=fields.String(),
        values=fields.String(validate=validate.OneOf([
            "name", "description", "category", "cogs", "quantity", "status",
        ])),
        required=True,
    )


class CSVJobStatusSchema(Schema):
    """Schema for CSV import job status response."""

    job_id = fields.UUID(dump_only=True)
    status = fields.String(dump_only=True)
    total_rows = fields.Integer(dump_only=True)
    success_count = fields.Integer(dump_only=True)
    error_count = fields.Integer(dump_only=True)
    skipped_count = fields.Integer(dump_only=True)
    row_errors = fields.List(fields.Dict(), dump_only=True, allow_none=True)
