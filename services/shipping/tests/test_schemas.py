"""Tests for shipping Marshmallow schemas."""

import uuid
from datetime import datetime, timezone

import pytest
from marshmallow import ValidationError

from services.shipping.schemas.schemas import (
    BulkShipmentCreateSchema,
    ShipmentCreateSchema,
    ShipmentListQuerySchema,
    ShipmentUpdateSchema,
)


class TestShipmentCreateSchema:
    """Tests for ShipmentCreateSchema."""

    def test_valid_minimal(self):
        schema = ShipmentCreateSchema()
        result = schema.load({"order_id": str(uuid.uuid4())})
        assert "order_id" in result
        assert result["carrier"] == ""
        assert result["country"] == "US"

    def test_valid_full(self):
        schema = ShipmentCreateSchema()
        result = schema.load({
            "order_id": str(uuid.uuid4()),
            "carrier": "usps",
            "tracking_number": "123456",
            "weight_oz": 12.5,
            "buyer_name": "John",
            "address_line1": "123 Main",
            "city": "Springfield",
            "state": "IL",
            "zip_code": "62701",
            "notes": "Handle with care",
        })
        assert result["carrier"] == "usps"
        assert result["weight_oz"] == 12.5

    def test_missing_order_id(self):
        schema = ShipmentCreateSchema()
        with pytest.raises(ValidationError):
            schema.load({})

    def test_negative_weight(self):
        schema = ShipmentCreateSchema()
        with pytest.raises(ValidationError):
            schema.load({"order_id": str(uuid.uuid4()), "weight_oz": -1.0})

    def test_carrier_too_long(self):
        schema = ShipmentCreateSchema()
        with pytest.raises(ValidationError):
            schema.load({"order_id": str(uuid.uuid4()), "carrier": "x" * 101})


class TestShipmentUpdateSchema:
    """Tests for ShipmentUpdateSchema."""

    def test_valid_partial(self):
        schema = ShipmentUpdateSchema()
        result = schema.load({"carrier": "fedex", "tracking_number": "789"})
        assert result["carrier"] == "fedex"
        assert result["tracking_number"] == "789"

    def test_empty_update(self):
        schema = ShipmentUpdateSchema()
        result = schema.load({})
        assert result == {}

    def test_invalid_weight(self):
        schema = ShipmentUpdateSchema()
        with pytest.raises(ValidationError):
            schema.load({"weight_oz": -5.0})


class TestShipmentListQuerySchema:
    """Tests for ShipmentListQuerySchema."""

    def test_defaults(self):
        schema = ShipmentListQuerySchema()
        result = schema.load({})
        assert result["cursor"] is None
        assert result["limit"] == 50
        assert result["status"] is None

    def test_valid_status_filter(self):
        schema = ShipmentListQuerySchema()
        result = schema.load({"status": "shipped"})
        assert result["status"] == "shipped"

    def test_invalid_status(self):
        schema = ShipmentListQuerySchema()
        with pytest.raises(ValidationError):
            schema.load({"status": "invalid_status"})

    def test_limit_bounds(self):
        schema = ShipmentListQuerySchema()
        with pytest.raises(ValidationError):
            schema.load({"limit": 0})
        with pytest.raises(ValidationError):
            schema.load({"limit": 101})


class TestBulkShipmentCreateSchema:
    """Tests for BulkShipmentCreateSchema."""

    def test_valid_minimal(self):
        schema = BulkShipmentCreateSchema()
        result = schema.load({"show_id": str(uuid.uuid4())})
        assert "show_id" in result
        assert result["carrier"] == ""

    def test_valid_with_carrier(self):
        schema = BulkShipmentCreateSchema()
        result = schema.load({
            "show_id": str(uuid.uuid4()),
            "carrier": "usps",
        })
        assert result["carrier"] == "usps"

    def test_missing_show_id(self):
        schema = BulkShipmentCreateSchema()
        with pytest.raises(ValidationError):
            schema.load({})
