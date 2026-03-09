"""Tests for ShippingService — CRUD, transitions, bulk, packing lists, overdue."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from services.inventory.models.models import InventoryItem, ItemStatus
from services.sales.models.models import Order, OrderStatus, Show, ShowStatus
from services.shipping.models.models import Shipment, ShipmentStatus
from services.shipping.providers.base import LabelResult
from services.shipping.services.shipping_service import ShippingService, ShippingServiceError


class TestCreateShipment:
    """Tests for shipment creation."""

    def test_create_shipment_success(self, db_session, sample_account, sample_order, sample_user, mock_event_publisher):
        svc = ShippingService(db_session, sample_account.id, event_publisher=mock_event_publisher)
        result = svc.create_shipment(
            {"order_id": sample_order.id, "carrier": "usps", "buyer_name": "John"},
            actor_id=sample_user.id,
        )
        assert result["order_id"] == str(sample_order.id)
        assert result["carrier"] == "usps"
        assert result["status"] == "pending"
        mock_event_publisher.publish.assert_called_once()

    def test_create_shipment_order_not_found(self, db_session, sample_account, sample_user):
        svc = ShippingService(db_session, sample_account.id)
        with pytest.raises(ShippingServiceError) as exc_info:
            svc.create_shipment({"order_id": uuid.uuid4()}, actor_id=sample_user.id)
        assert exc_info.value.code == "not_found"

    def test_create_shipment_duplicate(self, db_session, sample_account, sample_order, sample_shipment, sample_user):
        svc = ShippingService(db_session, sample_account.id)
        with pytest.raises(ShippingServiceError) as exc_info:
            svc.create_shipment({"order_id": sample_order.id}, actor_id=sample_user.id)
        assert exc_info.value.code == "conflict"

    def test_create_shipment_cross_account(self, db_session, sample_account, other_account, sample_order, sample_user):
        svc = ShippingService(db_session, other_account.id)
        with pytest.raises(ShippingServiceError) as exc_info:
            svc.create_shipment({"order_id": sample_order.id}, actor_id=sample_user.id)
        assert exc_info.value.code == "not_found"


class TestGetShipment:
    """Tests for getting a shipment."""

    def test_get_shipment_success(self, db_session, sample_account, sample_shipment):
        svc = ShippingService(db_session, sample_account.id)
        result = svc.get_shipment(sample_shipment.id)
        assert result["id"] == str(sample_shipment.id)
        assert result["carrier"] == "usps"

    def test_get_shipment_not_found(self, db_session, sample_account):
        svc = ShippingService(db_session, sample_account.id)
        with pytest.raises(ShippingServiceError) as exc_info:
            svc.get_shipment(uuid.uuid4())
        assert exc_info.value.code == "not_found"


class TestListShipments:
    """Tests for listing shipments."""

    def test_list_shipments_empty(self, db_session, sample_account):
        svc = ShippingService(db_session, sample_account.id)
        result = svc.list_shipments()
        assert result["items"] == []
        assert result["total_count"] == 0

    def test_list_shipments_with_data(self, db_session, sample_account, sample_shipment):
        svc = ShippingService(db_session, sample_account.id)
        result = svc.list_shipments()
        assert result["total_count"] == 1
        assert len(result["items"]) == 1

    def test_list_shipments_filter_status(self, db_session, sample_account, sample_shipment):
        svc = ShippingService(db_session, sample_account.id)
        result = svc.list_shipments(status="pending")
        assert result["total_count"] == 1

        result = svc.list_shipments(status="shipped")
        assert result["total_count"] == 0


class TestUpdateShipment:
    """Tests for updating shipments."""

    def test_update_shipment_success(self, db_session, sample_account, sample_shipment, sample_user, mock_event_publisher):
        svc = ShippingService(db_session, sample_account.id, event_publisher=mock_event_publisher)
        result = svc.update_shipment(
            sample_shipment.id,
            {"tracking_number": "TRACK123", "carrier": "fedex"},
            actor_id=sample_user.id,
        )
        assert result["tracking_number"] == "TRACK123"
        assert result["carrier"] == "fedex"
        mock_event_publisher.publish.assert_called_once()

    def test_update_shipment_no_changes(self, db_session, sample_account, sample_shipment, sample_user):
        svc = ShippingService(db_session, sample_account.id)
        result = svc.update_shipment(
            sample_shipment.id,
            {"carrier": "usps"},  # Same as existing
            actor_id=sample_user.id,
        )
        assert result["carrier"] == "usps"

    def test_update_cancelled_shipment(self, db_session, sample_account, sample_shipment, sample_user):
        sample_shipment.status = ShipmentStatus.CANCELLED
        db_session.flush()
        svc = ShippingService(db_session, sample_account.id)
        with pytest.raises(ShippingServiceError) as exc_info:
            svc.update_shipment(sample_shipment.id, {"carrier": "fedex"}, actor_id=sample_user.id)
        assert exc_info.value.code == "conflict"

    def test_update_shipment_not_found(self, db_session, sample_account, sample_user):
        svc = ShippingService(db_session, sample_account.id)
        with pytest.raises(ShippingServiceError):
            svc.update_shipment(uuid.uuid4(), {"carrier": "fedex"}, actor_id=sample_user.id)


class TestDeleteShipment:
    """Tests for soft-deleting shipments."""

    def test_delete_shipment_success(self, db_session, sample_account, sample_shipment, sample_user):
        svc = ShippingService(db_session, sample_account.id)
        svc.delete_shipment(sample_shipment.id, actor_id=sample_user.id)
        assert sample_shipment.deleted_at is not None

    def test_delete_shipment_not_found(self, db_session, sample_account, sample_user):
        svc = ShippingService(db_session, sample_account.id)
        with pytest.raises(ShippingServiceError):
            svc.delete_shipment(uuid.uuid4(), actor_id=sample_user.id)


class TestRestoreShipment:
    """Tests for restoring soft-deleted shipments."""

    def test_restore_shipment_success(self, db_session, sample_account, sample_shipment, sample_user):
        sample_shipment.deleted_at = datetime.now(timezone.utc)
        db_session.flush()
        svc = ShippingService(db_session, sample_account.id)
        result = svc.restore_shipment(sample_shipment.id, actor_id=sample_user.id)
        assert result["deleted_at"] is None

    def test_restore_active_shipment(self, db_session, sample_account, sample_shipment, sample_user):
        svc = ShippingService(db_session, sample_account.id)
        with pytest.raises(ShippingServiceError) as exc_info:
            svc.restore_shipment(sample_shipment.id, actor_id=sample_user.id)
        assert exc_info.value.code == "not_found"


class TestListDeletedShipments:
    """Tests for listing soft-deleted shipments."""

    def test_list_deleted_empty(self, db_session, sample_account):
        svc = ShippingService(db_session, sample_account.id)
        result = svc.list_deleted_shipments()
        assert result == []

    def test_list_deleted_with_data(self, db_session, sample_account, sample_shipment):
        sample_shipment.deleted_at = datetime.now(timezone.utc)
        db_session.flush()
        svc = ShippingService(db_session, sample_account.id)
        result = svc.list_deleted_shipments()
        assert len(result) == 1


class TestTransitionShipment:
    """Tests for shipment status transitions."""

    def test_transition_to_label_created(self, db_session, sample_account, sample_shipment, sample_user, mock_event_publisher):
        svc = ShippingService(db_session, sample_account.id, event_publisher=mock_event_publisher)
        result = svc.transition_shipment(sample_shipment.id, "label_created", actor_id=sample_user.id)
        assert result["status"] == "label_created"

    def test_transition_to_shipped(self, db_session, sample_account, sample_shipment, sample_order, sample_user, mock_event_publisher):
        sample_shipment.status = ShipmentStatus.LABEL_CREATED
        db_session.flush()
        svc = ShippingService(db_session, sample_account.id, event_publisher=mock_event_publisher)
        result = svc.transition_shipment(sample_shipment.id, "shipped", actor_id=sample_user.id)
        assert result["status"] == "shipped"
        assert result["shipped_at"] is not None
        # Verify order status updated
        db_session.refresh(sample_order)
        assert sample_order.status == OrderStatus.SHIPPED

    def test_transition_to_delivered(self, db_session, sample_account, sample_shipment, sample_order, sample_user):
        sample_shipment.status = ShipmentStatus.SHIPPED
        db_session.flush()
        svc = ShippingService(db_session, sample_account.id)
        result = svc.transition_shipment(sample_shipment.id, "delivered", actor_id=sample_user.id)
        assert result["status"] == "delivered"
        assert result["delivered_at"] is not None
        db_session.refresh(sample_order)
        assert sample_order.status == OrderStatus.DELIVERED

    def test_transition_to_cancelled(self, db_session, sample_account, sample_shipment, sample_user):
        svc = ShippingService(db_session, sample_account.id)
        result = svc.transition_shipment(sample_shipment.id, "cancelled", actor_id=sample_user.id)
        assert result["status"] == "cancelled"

    def test_invalid_transition(self, db_session, sample_account, sample_shipment, sample_user):
        svc = ShippingService(db_session, sample_account.id)
        with pytest.raises(ShippingServiceError) as exc_info:
            svc.transition_shipment(sample_shipment.id, "delivered", actor_id=sample_user.id)
        assert exc_info.value.code == "conflict"

    def test_transition_not_found(self, db_session, sample_account, sample_user):
        svc = ShippingService(db_session, sample_account.id)
        with pytest.raises(ShippingServiceError):
            svc.transition_shipment(uuid.uuid4(), "shipped", actor_id=sample_user.id)


class TestCreateLabel:
    """Tests for label creation via provider."""

    def test_create_label_success(self, db_session, sample_account, sample_shipment, sample_user, mock_event_publisher):
        mock_provider = MagicMock()
        mock_provider.create_label.return_value = LabelResult(
            success=True, label_url="https://labels.example.com/abc.pdf", tracking_number="TRACK001"
        )
        svc = ShippingService(
            db_session, sample_account.id,
            event_publisher=mock_event_publisher,
            shipping_provider=mock_provider,
        )
        result = svc.create_label(sample_shipment.id, actor_id=sample_user.id)
        assert result["status"] == "label_created"
        assert result["label_url"] == "https://labels.example.com/abc.pdf"
        assert result["tracking_number"] == "TRACK001"

    def test_create_label_not_pending(self, db_session, sample_account, sample_shipment, sample_user):
        sample_shipment.status = ShipmentStatus.LABEL_CREATED
        db_session.flush()
        svc = ShippingService(db_session, sample_account.id)
        with pytest.raises(ShippingServiceError) as exc_info:
            svc.create_label(sample_shipment.id, actor_id=sample_user.id)
        assert exc_info.value.code == "conflict"

    def test_create_label_provider_failure(self, db_session, sample_account, sample_shipment, sample_user):
        mock_provider = MagicMock()
        mock_provider.create_label.return_value = LabelResult(
            success=False, label_url="", tracking_number="", error="API error"
        )
        svc = ShippingService(db_session, sample_account.id, shipping_provider=mock_provider)
        with pytest.raises(ShippingServiceError) as exc_info:
            svc.create_label(sample_shipment.id, actor_id=sample_user.id)
        assert exc_info.value.code == "provider_error"

    def test_create_label_not_found(self, db_session, sample_account, sample_user):
        svc = ShippingService(db_session, sample_account.id)
        with pytest.raises(ShippingServiceError):
            svc.create_label(uuid.uuid4(), actor_id=sample_user.id)


class TestBulkCreateShipments:
    """Tests for bulk shipment creation."""

    def test_bulk_create_success(self, db_session, sample_account, sample_show, sample_order, sample_order2, sample_user, mock_event_publisher):
        svc = ShippingService(db_session, sample_account.id, event_publisher=mock_event_publisher)
        result = svc.bulk_create_shipments(
            sample_show.id, {"carrier": "usps"}, actor_id=sample_user.id
        )
        assert result["summary"]["created_count"] == 2
        assert result["summary"]["skipped_count"] == 0
        assert len(result["created"]) == 2

    def test_bulk_create_with_existing(self, db_session, sample_account, sample_show, sample_order, sample_order2, sample_shipment, sample_user):
        svc = ShippingService(db_session, sample_account.id)
        result = svc.bulk_create_shipments(
            sample_show.id, {}, actor_id=sample_user.id
        )
        assert result["summary"]["created_count"] == 1
        assert result["summary"]["skipped_count"] == 1
        assert result["skipped"][0]["reason"] == "Shipment already exists."

    def test_bulk_create_show_not_found(self, db_session, sample_account, sample_user):
        svc = ShippingService(db_session, sample_account.id)
        with pytest.raises(ShippingServiceError) as exc_info:
            svc.bulk_create_shipments(uuid.uuid4(), {}, actor_id=sample_user.id)
        assert exc_info.value.code == "not_found"

    def test_bulk_create_no_pending_orders(self, db_session, sample_account, sample_user):
        show = Show(account_id=sample_account.id, title="Empty Show", status=ShowStatus.COMPLETED)
        db_session.add(show)
        db_session.flush()
        svc = ShippingService(db_session, sample_account.id)
        result = svc.bulk_create_shipments(show.id, {}, actor_id=sample_user.id)
        assert result["summary"]["created_count"] == 0
        assert result["summary"]["skipped_count"] == 0


class TestPackingList:
    """Tests for packing list generation."""

    def test_packing_list_success(self, db_session, sample_account, sample_show, sample_order, sample_shipment):
        svc = ShippingService(db_session, sample_account.id)
        result = svc.generate_packing_list(sample_show.id)
        assert result["show"]["id"] == str(sample_show.id)
        assert result["summary"]["total_buyers"] == 1
        assert result["summary"]["total_items"] == 1
        assert result["buyers"][0]["buyer_username"] == "buyer123"
        assert result["buyers"][0]["address"]["city"] == "Springfield"

    def test_packing_list_multiple_buyers(self, db_session, sample_account, sample_show, sample_order, sample_order2):
        svc = ShippingService(db_session, sample_account.id)
        result = svc.generate_packing_list(sample_show.id)
        assert result["summary"]["total_buyers"] == 2
        assert result["summary"]["total_items"] == 2

    def test_packing_list_empty_show(self, db_session, sample_account, sample_user):
        show = Show(account_id=sample_account.id, title="Empty Show", status=ShowStatus.COMPLETED)
        db_session.add(show)
        db_session.flush()
        svc = ShippingService(db_session, sample_account.id)
        result = svc.generate_packing_list(show.id)
        assert result["buyers"] == []
        assert result["summary"]["total_buyers"] == 0
        assert result["summary"]["total_items"] == 0

    def test_packing_list_show_not_found(self, db_session, sample_account):
        svc = ShippingService(db_session, sample_account.id)
        with pytest.raises(ShippingServiceError) as exc_info:
            svc.generate_packing_list(uuid.uuid4())
        assert exc_info.value.code == "not_found"


class TestOverdueShipments:
    """Tests for overdue shipment queries."""

    def test_list_overdue_empty(self, db_session, sample_account):
        svc = ShippingService(db_session, sample_account.id)
        result = svc.list_overdue_shipments()
        assert result == []

    def test_list_overdue_with_data(self, db_session, sample_account, sample_shipment):
        sample_shipment.ship_by_date = datetime.now(timezone.utc) - timedelta(days=1)
        db_session.flush()
        svc = ShippingService(db_session, sample_account.id)
        result = svc.list_overdue_shipments()
        assert len(result) == 1
        assert result[0]["id"] == str(sample_shipment.id)

    def test_list_overdue_excludes_shipped(self, db_session, sample_account, sample_shipment):
        sample_shipment.ship_by_date = datetime.now(timezone.utc) - timedelta(days=1)
        sample_shipment.status = ShipmentStatus.SHIPPED
        db_session.flush()
        svc = ShippingService(db_session, sample_account.id)
        result = svc.list_overdue_shipments()
        assert result == []

    def test_list_overdue_excludes_future(self, db_session, sample_account, sample_shipment):
        sample_shipment.ship_by_date = datetime.now(timezone.utc) + timedelta(days=5)
        db_session.flush()
        svc = ShippingService(db_session, sample_account.id)
        result = svc.list_overdue_shipments()
        assert result == []


class TestEventPublishing:
    """Tests for event publishing behavior."""

    def test_no_publisher_no_error(self, db_session, sample_account, sample_order, sample_user):
        svc = ShippingService(db_session, sample_account.id, event_publisher=None)
        result = svc.create_shipment({"order_id": sample_order.id}, actor_id=sample_user.id)
        assert result is not None

    def test_bulk_create_publishes_event(self, db_session, sample_account, sample_show, sample_order, sample_user, mock_event_publisher):
        svc = ShippingService(db_session, sample_account.id, event_publisher=mock_event_publisher)
        svc.bulk_create_shipments(sample_show.id, {}, actor_id=sample_user.id)
        mock_event_publisher.publish.assert_called_once()
        call_args = mock_event_publisher.publish.call_args
        assert call_args[0][0] == "shipment.bulk_created"
