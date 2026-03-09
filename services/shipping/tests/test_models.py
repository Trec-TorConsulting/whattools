"""Tests for Shipment model."""

import uuid

from services.shipping.models.models import Shipment, ShipmentStatus, SHIPMENT_TRANSITIONS


class TestShipmentModel:
    """Tests for the Shipment model."""

    def test_create_shipment(self, db_session, sample_account, sample_order):
        """Test creating a Shipment with required fields."""
        shipment = Shipment(
            account_id=sample_account.id,
            order_id=sample_order.id,
        )
        db_session.add(shipment)
        db_session.flush()

        assert shipment.id is not None
        assert shipment.account_id == sample_account.id
        assert shipment.order_id == sample_order.id
        assert shipment.status == ShipmentStatus.PENDING
        assert shipment.carrier == ""
        assert shipment.tracking_number == ""
        assert shipment.country == "US"
        assert shipment.created_at is not None
        assert shipment.deleted_at is None

    def test_shipment_defaults(self, db_session, sample_account, sample_order):
        """Test that Shipment defaults are properly set."""
        shipment = Shipment(
            account_id=sample_account.id,
            order_id=sample_order.id,
        )
        db_session.add(shipment)
        db_session.flush()

        assert shipment.label_url == ""
        assert shipment.ship_by_date is None
        assert shipment.shipped_at is None
        assert shipment.delivered_at is None
        assert float(shipment.weight_oz) == 0.0
        assert shipment.buyer_name == ""
        assert shipment.address_line1 == ""
        assert shipment.address_line2 == ""
        assert shipment.city == ""
        assert shipment.state == ""
        assert shipment.zip_code == ""
        assert shipment.notes == ""

    def test_shipment_with_all_fields(self, db_session, sample_account, sample_order):
        """Test creating a Shipment with all fields populated."""
        shipment = Shipment(
            account_id=sample_account.id,
            order_id=sample_order.id,
            carrier="usps",
            tracking_number="1Z999AA10123456784",
            label_url="https://labels.example.com/123.pdf",
            weight_oz=12.5,
            buyer_name="John Doe",
            address_line1="123 Main St",
            address_line2="Apt 4B",
            city="Springfield",
            state="IL",
            zip_code="62701",
            country="US",
            notes="Fragile",
        )
        db_session.add(shipment)
        db_session.flush()

        assert shipment.carrier == "usps"
        assert shipment.tracking_number == "1Z999AA10123456784"
        assert float(shipment.weight_oz) == 12.5
        assert shipment.buyer_name == "John Doe"
        assert shipment.city == "Springfield"


class TestShipmentStatus:
    """Tests for ShipmentStatus enum."""

    def test_status_values(self):
        """Test that all expected status values exist."""
        assert ShipmentStatus.PENDING == "pending"
        assert ShipmentStatus.LABEL_CREATED == "label_created"
        assert ShipmentStatus.SHIPPED == "shipped"
        assert ShipmentStatus.DELIVERED == "delivered"
        assert ShipmentStatus.CANCELLED == "cancelled"

    def test_transitions(self):
        """Test that valid transitions are defined for each status."""
        assert ShipmentStatus.LABEL_CREATED in SHIPMENT_TRANSITIONS[ShipmentStatus.PENDING]
        assert ShipmentStatus.CANCELLED in SHIPMENT_TRANSITIONS[ShipmentStatus.PENDING]
        assert ShipmentStatus.SHIPPED in SHIPMENT_TRANSITIONS[ShipmentStatus.LABEL_CREATED]
        assert ShipmentStatus.DELIVERED in SHIPMENT_TRANSITIONS[ShipmentStatus.SHIPPED]
        assert SHIPMENT_TRANSITIONS[ShipmentStatus.DELIVERED] == []
        assert SHIPMENT_TRANSITIONS[ShipmentStatus.CANCELLED] == []
