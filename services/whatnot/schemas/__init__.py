"""Marshmallow schemas for whatnot service request/response validation."""

from marshmallow import Schema, fields, validate


# ── OAuth ────────────────────────────────────────────────────────────────────

class OAuthConnectResponseSchema(Schema):
    """Response with Whatnot OAuth authorize URL."""

    authorize_url = fields.String(dump_only=True)
    state = fields.String(dump_only=True)


class OAuthStatusSchema(Schema):
    """Response for Whatnot connection status."""

    connected = fields.Boolean(dump_only=True)
    whatnot_username = fields.String(dump_only=True)
    scopes = fields.String(dump_only=True)
    last_sync_at = fields.DateTime(dump_only=True)


# ── Products ─────────────────────────────────────────────────────────────────

class ProductPullResponseSchema(Schema):
    """Response for pulling products from Whatnot."""

    created = fields.Integer(dump_only=True)
    updated = fields.Integer(dump_only=True)
    total = fields.Integer(dump_only=True)


class ProductPushSchema(Schema):
    """Request to push an inventory item to Whatnot."""

    inventory_item_id = fields.UUID(required=True)


class ProductSyncSchema(Schema):
    """Request to sync a product with Whatnot."""

    pass


class ProductUnlinkSchema(Schema):
    """Request to unlink a product from Whatnot."""

    pass


# ── Listings ─────────────────────────────────────────────────────────────────

class ListingUpdateSchema(Schema):
    """Request to update a listing on Whatnot."""

    title = fields.String(validate=validate.Length(max=255))
    description = fields.String()
    price = fields.Float()


class ListingAssignLivestreamSchema(Schema):
    """Request to assign a listing to a livestream."""

    livestream_id = fields.String(required=True)


class ListingAdjustQuantitySchema(Schema):
    """Request to adjust listing quantity."""

    quantity_delta = fields.Integer(required=True)


# ── Orders ───────────────────────────────────────────────────────────────────

class OrderTrackingSchema(Schema):
    """Request to push tracking info to Whatnot."""

    carrier = fields.String(required=True, validate=validate.OneOf(["USPS", "UPS", "FEDEX"]))
    tracking_number = fields.String(required=True, validate=validate.Length(min=1, max=100))


class OrderCancelSchema(Schema):
    """Request to cancel an order."""

    pass


# ── Sync ─────────────────────────────────────────────────────────────────────

class SyncStatusResponseSchema(Schema):
    """Response for sync status."""

    sync_type = fields.String(dump_only=True)
    status = fields.String(dump_only=True)
    started_at = fields.DateTime(dump_only=True)
    completed_at = fields.DateTime(dump_only=True)
    items_synced = fields.Integer(dump_only=True)
    items_created = fields.Integer(dump_only=True)
    items_updated = fields.Integer(dump_only=True)
    items_failed = fields.Integer(dump_only=True)
    error_message = fields.String(dump_only=True)


class SyncHistoryResponseSchema(Schema):
    """Response wrapper for sync history."""

    latest = fields.Dict(keys=fields.String(), values=fields.Nested(SyncStatusResponseSchema), dump_only=True)
    recent = fields.List(fields.Nested(SyncStatusResponseSchema), dump_only=True)


# ── Billing ──────────────────────────────────────────────────────────────────

class CheckoutSchema(Schema):
    """Request to create a Stripe Checkout session."""

    success_url = fields.Url(required=True)
    cancel_url = fields.Url(required=True)


class PortalSchema(Schema):
    """Request to create a Stripe Customer Portal session."""

    return_url = fields.Url(required=True)


class SubscriptionStatusSchema(Schema):
    """Response for subscription status."""

    plan_tier = fields.String(dump_only=True)
    subscription_status = fields.String(dump_only=True)
    stripe_customer_id = fields.String(dump_only=True)
    inventory_item_limit = fields.Integer(dump_only=True)
    team_member_limit = fields.Integer(dump_only=True)
