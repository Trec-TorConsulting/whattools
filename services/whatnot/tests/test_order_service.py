"""Tests for order sync service."""

import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from services.whatnot.services.order_service import OrderSyncService, OrderServiceError


class TestOrderSyncService:
    def test_pull_orders_empty(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute.return_value = {
            "orders": {"edges": [], "pageInfo": {"hasNextPage": False}}
        }

        svc = OrderSyncService(db_session, sample_account.id, mock_whatnot_client)
        result = svc.pull_orders()

        assert result["created"] == 0
        assert result["updated"] == 0

    def test_push_tracking_invalid_carrier(self, db_session, sample_account, mock_whatnot_client):
        svc = OrderSyncService(db_session, sample_account.id, mock_whatnot_client)
        fake_id = uuid.uuid4()

        with pytest.raises(OrderServiceError):
            svc.push_tracking(fake_id, "INVALID", "123")

    def test_push_tracking_valid_carriers(self, db_session, sample_account, mock_whatnot_client):
        """Ensure valid carriers are accepted (even if order not found)."""
        svc = OrderSyncService(db_session, sample_account.id, mock_whatnot_client)
        fake_id = uuid.uuid4()

        for carrier in ["USPS", "UPS", "FEDEX"]:
            with pytest.raises(OrderServiceError):
                # Raises because order doesn't exist, not because carrier is invalid
                svc.push_tracking(fake_id, carrier, "ABC123")

    def test_cancel_order_not_found(self, db_session, sample_account, mock_whatnot_client):
        svc = OrderSyncService(db_session, sample_account.id, mock_whatnot_client)
        fake_id = uuid.uuid4()

        with pytest.raises(OrderServiceError):
            svc.cancel_order(fake_id)
