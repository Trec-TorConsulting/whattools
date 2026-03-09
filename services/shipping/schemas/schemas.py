"""Marshmallow schemas for shipping service request/response validation."""

from marshmallow import Schema, fields, validate


class ShipmentCreateSchema(Schema):
    """Schema for creating a shipment."""

    order_id = fields.UUID(required=True)
    carrier = fields.String(load_default="", validate=validate.Length(max=100))
    tracking_number = fields.String(load_default="", validate=validate.Length(max=255))
    label_url = fields.String(load_default="", validate=validate.Length(max=1024))
    ship_by_date = fields.DateTime(load_default=None, allow_none=True)
    weight_oz = fields.Float(load_default=0.0, validate=validate.Range(min=0))
    buyer_name = fields.String(load_default="", validate=validate.Length(max=255))
    address_line1 = fields.String(load_default="", validate=validate.Length(max=255))
    address_line2 = fields.String(load_default="", validate=validate.Length(max=255))
    city = fields.String(load_default="", validate=validate.Length(max=100))
    state = fields.String(load_default="", validate=validate.Length(max=50))
    zip_code = fields.String(load_default="", validate=validate.Length(max=20))
    country = fields.String(load_default="US", validate=validate.Length(max=50))
    notes = fields.String(load_default="", validate=validate.Length(max=5000))


class ShipmentUpdateSchema(Schema):
    """Schema for updating a shipment."""

    carrier = fields.String(validate=validate.Length(max=100))
    tracking_number = fields.String(validate=validate.Length(max=255))
    label_url = fields.String(validate=validate.Length(max=1024))
    ship_by_date = fields.DateTime(allow_none=True)
    weight_oz = fields.Float(validate=validate.Range(min=0))
    buyer_name = fields.String(validate=validate.Length(max=255))
    address_line1 = fields.String(validate=validate.Length(max=255))
    address_line2 = fields.String(validate=validate.Length(max=255))
    city = fields.String(validate=validate.Length(max=100))
    state = fields.String(validate=validate.Length(max=50))
    zip_code = fields.String(validate=validate.Length(max=20))
    country = fields.String(validate=validate.Length(max=50))
    notes = fields.String(validate=validate.Length(max=5000))


class ShipmentResponseSchema(Schema):
    """Schema for shipment response."""

    id = fields.UUID(dump_only=True)
    account_id = fields.UUID(dump_only=True)
    order_id = fields.UUID(dump_only=True)
    carrier = fields.String(dump_only=True)
    tracking_number = fields.String(dump_only=True)
    label_url = fields.String(dump_only=True)
    ship_by_date = fields.DateTime(dump_only=True, allow_none=True)
    shipped_at = fields.DateTime(dump_only=True, allow_none=True)
    delivered_at = fields.DateTime(dump_only=True, allow_none=True)
    weight_oz = fields.Float(dump_only=True)
    buyer_name = fields.String(dump_only=True)
    address_line1 = fields.String(dump_only=True)
    address_line2 = fields.String(dump_only=True)
    city = fields.String(dump_only=True)
    state = fields.String(dump_only=True)
    zip_code = fields.String(dump_only=True)
    country = fields.String(dump_only=True)
    status = fields.String(dump_only=True)
    notes = fields.String(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    deleted_at = fields.DateTime(dump_only=True, allow_none=True)


class ShipmentListQuerySchema(Schema):
    """Schema for shipment list query parameters."""

    cursor = fields.String(load_default=None)
    limit = fields.Integer(load_default=50, validate=validate.Range(min=1, max=100))
    status = fields.String(
        load_default=None,
        validate=validate.OneOf(["pending", "label_created", "shipped", "delivered", "cancelled"]),
    )
    order_id = fields.UUID(load_default=None)


class BulkShipmentCreateSchema(Schema):
    """Schema for bulk shipment creation from a show."""

    show_id = fields.UUID(required=True)
    carrier = fields.String(load_default="", validate=validate.Length(max=100))
    ship_by_date = fields.DateTime(load_default=None, allow_none=True)
