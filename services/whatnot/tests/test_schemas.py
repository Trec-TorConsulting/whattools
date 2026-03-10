"""Tests for Marshmallow schemas."""

import uuid

import pytest
from marshmallow import ValidationError

from services.whatnot.schemas import (
    CheckoutSchema,
    ListingAdjustQuantitySchema,
    ListingAssignLivestreamSchema,
    ListingUpdateSchema,
    OAuthConnectResponseSchema,
    OAuthStatusSchema,
    OrderCancelSchema,
    OrderTrackingSchema,
    PortalSchema,
    ProductPullResponseSchema,
    ProductPushSchema,
    SubscriptionStatusSchema,
    SyncHistoryResponseSchema,
    SyncStatusResponseSchema,
)


class TestOAuthSchemas:
    def test_connect_response_dump(self):
        schema = OAuthConnectResponseSchema()
        result = schema.dump({"authorize_url": "https://example.com/auth", "state": "abc123"})
        assert result["authorize_url"] == "https://example.com/auth"
        assert result["state"] == "abc123"

    def test_status_dump(self):
        schema = OAuthStatusSchema()
        result = schema.dump({
            "connected": True,
            "whatnot_username": "seller1",
            "scopes": "read:inventory",
        })
        assert result["connected"] is True
        assert result["whatnot_username"] == "seller1"

    def test_status_dump_not_connected(self):
        schema = OAuthStatusSchema()
        result = schema.dump({"connected": False})
        assert result["connected"] is False


class TestProductSchemas:
    def test_pull_response_dump(self):
        schema = ProductPullResponseSchema()
        result = schema.dump({"created": 5, "updated": 2, "total": 7})
        assert result["total"] == 7

    def test_push_schema_valid(self):
        schema = ProductPushSchema()
        result = schema.load({"inventory_item_id": str(uuid.uuid4())})
        assert "inventory_item_id" in result

    def test_push_schema_missing_id(self):
        schema = ProductPushSchema()
        with pytest.raises(ValidationError):
            schema.load({})

    def test_push_schema_invalid_uuid(self):
        schema = ProductPushSchema()
        with pytest.raises(ValidationError):
            schema.load({"inventory_item_id": "not-a-uuid"})


class TestListingSchemas:
    def test_update_valid(self):
        schema = ListingUpdateSchema()
        result = schema.load({"title": "My Item", "price": 19.99})
        assert result["title"] == "My Item"
        assert result["price"] == 19.99

    def test_update_title_too_long(self):
        schema = ListingUpdateSchema()
        with pytest.raises(ValidationError):
            schema.load({"title": "x" * 256})

    def test_assign_livestream_valid(self):
        schema = ListingAssignLivestreamSchema()
        result = schema.load({"livestream_id": "live_123"})
        assert result["livestream_id"] == "live_123"

    def test_assign_livestream_missing(self):
        schema = ListingAssignLivestreamSchema()
        with pytest.raises(ValidationError):
            schema.load({})

    def test_adjust_quantity_valid(self):
        schema = ListingAdjustQuantitySchema()
        result = schema.load({"quantity_delta": -5})
        assert result["quantity_delta"] == -5

    def test_adjust_quantity_missing(self):
        schema = ListingAdjustQuantitySchema()
        with pytest.raises(ValidationError):
            schema.load({})


class TestOrderSchemas:
    def test_tracking_valid(self):
        schema = OrderTrackingSchema()
        result = schema.load({"carrier": "USPS", "tracking_number": "9400111"})
        assert result["carrier"] == "USPS"

    def test_tracking_invalid_carrier(self):
        schema = OrderTrackingSchema()
        with pytest.raises(ValidationError):
            schema.load({"carrier": "DHL", "tracking_number": "123"})

    def test_tracking_missing_number(self):
        schema = OrderTrackingSchema()
        with pytest.raises(ValidationError):
            schema.load({"carrier": "UPS"})

    def test_tracking_empty_number(self):
        schema = OrderTrackingSchema()
        with pytest.raises(ValidationError):
            schema.load({"carrier": "FEDEX", "tracking_number": ""})

    def test_cancel_schema_accepts_empty(self):
        schema = OrderCancelSchema()
        result = schema.load({})
        assert result == {}


class TestSyncSchemas:
    def test_sync_status_dump(self):
        schema = SyncStatusResponseSchema()
        result = schema.dump({
            "sync_type": "products",
            "status": "completed",
            "items_synced": 10,
            "items_created": 5,
            "items_updated": 5,
            "items_failed": 0,
        })
        assert result["sync_type"] == "products"
        assert result["items_synced"] == 10

    def test_sync_history_dump(self):
        schema = SyncHistoryResponseSchema()
        result = schema.dump({
            "latest": {"products": {"sync_type": "products", "status": "completed"}},
            "recent": [{"sync_type": "orders", "status": "running"}],
        })
        assert "products" in result["latest"]
        assert len(result["recent"]) == 1


class TestBillingSchemas:
    def test_checkout_valid(self):
        schema = CheckoutSchema()
        result = schema.load({
            "success_url": "https://example.com/success",
            "cancel_url": "https://example.com/cancel",
        })
        assert "success_url" in result

    def test_checkout_invalid_url(self):
        schema = CheckoutSchema()
        with pytest.raises(ValidationError):
            schema.load({"success_url": "not-a-url", "cancel_url": "https://example.com"})

    def test_portal_valid(self):
        schema = PortalSchema()
        result = schema.load({"return_url": "https://example.com/dashboard"})
        assert result["return_url"] == "https://example.com/dashboard"

    def test_subscription_status_dump(self):
        schema = SubscriptionStatusSchema()
        result = schema.dump({
            "plan_tier": "pro",
            "subscription_status": "active",
            "inventory_item_limit": 500,
            "team_member_limit": 10,
        })
        assert result["plan_tier"] == "pro"
        assert result["inventory_item_limit"] == 500
