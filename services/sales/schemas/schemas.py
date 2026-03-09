"""Marshmallow schemas for sales service request/response validation."""

from marshmallow import Schema, fields, validate


class ShowCreateSchema(Schema):
    """Schema for creating a show."""

    title = fields.String(required=True, validate=validate.Length(min=1, max=255))
    platform = fields.String(load_default="whatnot", validate=validate.Length(max=50))
    scheduled_at = fields.DateTime(load_default=None, allow_none=True)
    scheduled_end_at = fields.DateTime(load_default=None, allow_none=True)
    notes = fields.String(load_default="", validate=validate.Length(max=5000))
    recurrence_rule = fields.String(
        load_default=None,
        allow_none=True,
        validate=validate.OneOf(["hourly", "daily", "weekly", "monthly"]),
    )
    recurrence_days = fields.String(
        load_default=None,
        allow_none=True,
        validate=validate.Length(max=100),
    )
    recurrence_weeks = fields.Integer(
        load_default=None,
        allow_none=True,
        validate=validate.Range(min=1, max=8),
    )


class ShowUpdateSchema(Schema):
    """Schema for updating a show."""

    title = fields.String(validate=validate.Length(min=1, max=255))
    platform = fields.String(validate=validate.Length(max=50))
    scheduled_at = fields.DateTime(allow_none=True)
    scheduled_end_at = fields.DateTime(allow_none=True)
    notes = fields.String(validate=validate.Length(max=5000))


class ShowResponseSchema(Schema):
    """Schema for show response."""

    id = fields.UUID(dump_only=True)
    account_id = fields.UUID(dump_only=True)
    title = fields.String(dump_only=True)
    platform = fields.String(dump_only=True)
    scheduled_at = fields.DateTime(dump_only=True, allow_none=True)
    scheduled_end_at = fields.DateTime(dump_only=True, allow_none=True)
    started_at = fields.DateTime(dump_only=True, allow_none=True)
    ended_at = fields.DateTime(dump_only=True, allow_none=True)
    status = fields.String(dump_only=True)
    notes = fields.String(dump_only=True)
    recurrence_rule = fields.String(dump_only=True, allow_none=True)
    recurrence_days = fields.String(dump_only=True, allow_none=True)
    recurrence_weeks = fields.Integer(dump_only=True, allow_none=True)
    recurrence_group_id = fields.UUID(dump_only=True, allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    deleted_at = fields.DateTime(dump_only=True, allow_none=True)


class ShowListQuerySchema(Schema):
    """Schema for show list query parameters."""

    cursor = fields.String(load_default=None)
    limit = fields.Integer(load_default=50, validate=validate.Range(min=1, max=100))
    status = fields.String(
        load_default=None,
        validate=validate.OneOf(["planned", "live", "completed", "cancelled"]),
    )


class OrderCreateSchema(Schema):
    """Schema for creating an order."""

    show_id = fields.UUID(required=True)
    inventory_item_id = fields.UUID(required=True)
    sale_price = fields.Float(required=True, validate=validate.Range(min=0))
    platform_fees = fields.Float(load_default=0.0, validate=validate.Range(min=0))
    shipping_cost = fields.Float(load_default=0.0, validate=validate.Range(min=0))
    buyer_username = fields.String(load_default="", validate=validate.Length(max=255))
    notes = fields.String(load_default="", validate=validate.Length(max=5000))


class OrderUpdateSchema(Schema):
    """Schema for updating an order."""

    sale_price = fields.Float(validate=validate.Range(min=0))
    platform_fees = fields.Float(validate=validate.Range(min=0))
    shipping_cost = fields.Float(validate=validate.Range(min=0))
    buyer_username = fields.String(validate=validate.Length(max=255))
    status = fields.String(validate=validate.OneOf(["pending", "shipped", "delivered"]))
    notes = fields.String(validate=validate.Length(max=5000))


class OrderResponseSchema(Schema):
    """Schema for order response."""

    id = fields.UUID(dump_only=True)
    account_id = fields.UUID(dump_only=True)
    show_id = fields.UUID(dump_only=True)
    inventory_item_id = fields.UUID(dump_only=True)
    sale_price = fields.Float(dump_only=True)
    platform_fees = fields.Float(dump_only=True)
    shipping_cost = fields.Float(dump_only=True)
    cost_basis = fields.Float(dump_only=True)
    profit = fields.Float(dump_only=True)
    buyer_username = fields.String(dump_only=True)
    status = fields.String(dump_only=True)
    notes = fields.String(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    deleted_at = fields.DateTime(dump_only=True, allow_none=True)


class OrderListQuerySchema(Schema):
    """Schema for order list query parameters."""

    cursor = fields.String(load_default=None)
    limit = fields.Integer(load_default=50, validate=validate.Range(min=1, max=100))
    show_id = fields.UUID(load_default=None)
    status = fields.String(
        load_default=None,
        validate=validate.OneOf(["pending", "shipped", "delivered", "cancelled"]),
    )
