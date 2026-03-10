"""Tests for order sync service."""

import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from services.inventory.models.models import InventoryItem, ItemStatus
from services.sales.models.models import Order, OrderStatus, Show
from services.whatnot.graphql.client import WhatnotApiError, WhatnotUserError
from services.whatnot.services.order_service import OrderSyncService, OrderServiceError, _extract_edges


class TestExtractEdges:
    def test_normal_edges(self):
        data = {"edges": [{"node": {"id": "1"}}, {"node": {"id": "2"}}]}
        result = _extract_edges(data)
        assert len(result) == 2
        assert result[0]["id"] == "1"

    def test_empty(self):
        assert _extract_edges({}) == []

    def test_no_edges_key(self):
        assert _extract_edges({"other": "data"}) == []


class TestOrderSyncService:
    def test_pull_orders_empty(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute.return_value = {
            "orders": {"edges": [], "pageInfo": {"hasNextPage": False}}
        }

        svc = OrderSyncService(db_session, sample_account.id, mock_whatnot_client)
        result = svc.pull_orders()

        assert result["created"] == 0
        assert result["updated"] == 0

    def test_pull_orders_creates_order(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute.return_value = {
            "orders": {
                "edges": [
                    {
                        "node": {
                            "id": "wn_order_1",
                            "status": "COMPLETED",
                            "total": {"amount": 2500, "currencyCode": "USD"},
                            "shippingPrice": {"amount": 500},
                            "customer": {"id": "cust_1", "username": "buyer1"},
                            "salesChannel": {"type": "LIVESTREAM"},
                            "isGiveaway": False,
                            "items": {"edges": []},
                        },
                    }
                ],
                "pageInfo": {"hasNextPage": False},
            }
        }

        svc = OrderSyncService(db_session, sample_account.id, mock_whatnot_client)
        result = svc.pull_orders()

        assert result["created"] == 1
        assert result["updated"] == 0

    def test_pull_orders_updates_existing(self, db_session, sample_account, mock_whatnot_client):
        # Create a show and order first
        show = Show(account_id=sample_account.id, title="Test Show", platform="whatnot")
        db_session.add(show)
        db_session.flush()

        placeholder = InventoryItem(
            account_id=sample_account.id, name="Placeholder", status=ItemStatus.AVAILABLE, cogs=0, quantity=1
        )
        db_session.add(placeholder)
        db_session.flush()

        order = Order(
            account_id=sample_account.id,
            show_id=show.id,
            inventory_item_id=placeholder.id,
            sale_price=10.0,
            buyer_username="old_buyer",
            status=OrderStatus.PENDING,
        )
        order.whatnot_order_id = "wn_order_exist"
        db_session.add(order)
        db_session.flush()

        mock_whatnot_client.execute.return_value = {
            "orders": {
                "edges": [
                    {
                        "node": {
                            "id": "wn_order_exist",
                            "status": "COMPLETED",
                            "total": {"amount": 1500},
                            "customer": {"username": "new_buyer"},
                            "items": {"edges": []},
                        },
                    }
                ],
                "pageInfo": {"hasNextPage": False},
            }
        }

        svc = OrderSyncService(db_session, sample_account.id, mock_whatnot_client)
        result = svc.pull_orders()

        assert result["updated"] == 1
        assert result["created"] == 0

    def test_pull_orders_pagination(self, db_session, sample_account, mock_whatnot_client):
        page1 = {
            "orders": {
                "edges": [{"node": {"id": "o1", "status": "PENDING", "total": {"amount": 100}, "customer": {}, "items": {"edges": []}}}],
                "pageInfo": {"hasNextPage": True, "endCursor": "cursor_1"},
            }
        }
        page2 = {
            "orders": {
                "edges": [{"node": {"id": "o2", "status": "PENDING", "total": {"amount": 200}, "customer": {}, "items": {"edges": []}}}],
                "pageInfo": {"hasNextPage": False},
            }
        }
        mock_whatnot_client.execute.side_effect = [page1, page2]

        svc = OrderSyncService(db_session, sample_account.id, mock_whatnot_client)
        result = svc.pull_orders()

        assert result["created"] == 2
        assert mock_whatnot_client.execute.call_count == 2

    def test_pull_orders_api_error(self, db_session, sample_account, mock_whatnot_client):
        mock_whatnot_client.execute.side_effect = WhatnotApiError("API failure")

        svc = OrderSyncService(db_session, sample_account.id, mock_whatnot_client)
        with pytest.raises(OrderServiceError) as exc_info:
            svc.pull_orders()
        assert exc_info.value.status_code == 502

    def test_pull_orders_item_failure_continues(self, db_session, sample_account, mock_whatnot_client):
        """Single item failure doesn't abort the sync."""
        mock_whatnot_client.execute.return_value = {
            "orders": {
                "edges": [
                    {"node": {"id": "o_good", "status": "PENDING", "total": {"amount": 100}, "customer": {}, "items": {"edges": []}}},
                    {"node": {}},  # Missing 'id' — will cause KeyError in _upsert_order
                ],
                "pageInfo": {"hasNextPage": False},
            }
        }

        svc = OrderSyncService(db_session, sample_account.id, mock_whatnot_client)
        result = svc.pull_orders()

        assert result["created"] == 1
        assert result["failed"] == 1

    def test_pull_orders_with_inventory_item(self, db_session, sample_account, mock_whatnot_client):
        """Order with a linked inventory item marks it as SOLD."""
        inv_item = InventoryItem(
            account_id=sample_account.id, name="Card", status=ItemStatus.AVAILABLE,
            cogs=5.0, quantity=1,
        )
        inv_item.whatnot_product_id = "wn_prod_linked"
        db_session.add(inv_item)
        db_session.flush()

        mock_whatnot_client.execute.return_value = {
            "orders": {
                "edges": [{
                    "node": {
                        "id": "o_linked",
                        "status": "COMPLETED",
                        "total": {"amount": 1500},
                        "customer": {"id": "c1", "username": "buyer"},
                        "items": {"edges": [{"node": {"product": {"id": "wn_prod_linked"}}}]},
                    }
                }],
                "pageInfo": {"hasNextPage": False},
            }
        }

        svc = OrderSyncService(db_session, sample_account.id, mock_whatnot_client)
        result = svc.pull_orders()

        assert result["created"] == 1
        db_session.refresh(inv_item)
        assert inv_item.status == ItemStatus.SOLD

    def test_push_tracking_invalid_carrier(self, db_session, sample_account, mock_whatnot_client):
        svc = OrderSyncService(db_session, sample_account.id, mock_whatnot_client)
        fake_id = uuid.uuid4()

        with pytest.raises(OrderServiceError):
            svc.push_tracking(fake_id, "INVALID", "123")

    def test_push_tracking_valid_carriers(self, db_session, sample_account, mock_whatnot_client):
        svc = OrderSyncService(db_session, sample_account.id, mock_whatnot_client)
        fake_id = uuid.uuid4()

        for carrier in ["USPS", "UPS", "FEDEX"]:
            with pytest.raises(OrderServiceError):
                svc.push_tracking(fake_id, carrier, "ABC123")

    def test_push_tracking_not_linked(self, db_session, sample_account, mock_whatnot_client):
        show = Show(account_id=sample_account.id, title="S", platform="whatnot")
        db_session.add(show)
        db_session.flush()
        inv = InventoryItem(account_id=sample_account.id, name="I", status=ItemStatus.AVAILABLE, cogs=0, quantity=1)
        db_session.add(inv)
        db_session.flush()
        order = Order(
            account_id=sample_account.id, show_id=show.id, inventory_item_id=inv.id,
            sale_price=10, buyer_username="b", status=OrderStatus.PENDING,
        )
        db_session.add(order)
        db_session.flush()

        svc = OrderSyncService(db_session, sample_account.id, mock_whatnot_client)
        with pytest.raises(OrderServiceError, match="not linked"):
            svc.push_tracking(order.id, "USPS", "123")

    def test_push_tracking_success(self, db_session, sample_account, mock_whatnot_client):
        show = Show(account_id=sample_account.id, title="S", platform="whatnot")
        db_session.add(show)
        db_session.flush()
        inv = InventoryItem(account_id=sample_account.id, name="I", status=ItemStatus.AVAILABLE, cogs=0, quantity=1)
        db_session.add(inv)
        db_session.flush()
        order = Order(
            account_id=sample_account.id, show_id=show.id, inventory_item_id=inv.id,
            sale_price=10, buyer_username="b", status=OrderStatus.PENDING,
        )
        order.whatnot_order_id = "wn_123"
        db_session.add(order)
        db_session.flush()

        mock_whatnot_client.execute_mutation.return_value = {"trackingCode": {"id": "tc_1"}}

        svc = OrderSyncService(db_session, sample_account.id, mock_whatnot_client)
        result = svc.push_tracking(order.id, "USPS", "9400111")

        assert result["tracking_company"] == "USPS"
        assert result["tracking_number"] == "9400111"
        db_session.refresh(order)
        assert order.status == OrderStatus.SHIPPED

    def test_push_tracking_whatnot_user_error(self, db_session, sample_account, mock_whatnot_client):
        show = Show(account_id=sample_account.id, title="S", platform="whatnot")
        db_session.add(show)
        db_session.flush()
        inv = InventoryItem(account_id=sample_account.id, name="I", status=ItemStatus.AVAILABLE, cogs=0, quantity=1)
        db_session.add(inv)
        db_session.flush()
        order = Order(
            account_id=sample_account.id, show_id=show.id, inventory_item_id=inv.id,
            sale_price=10, buyer_username="b", status=OrderStatus.PENDING,
        )
        order.whatnot_order_id = "wn_123"
        db_session.add(order)
        db_session.flush()

        mock_whatnot_client.execute_mutation.side_effect = WhatnotUserError("Invalid tracking")
        svc = OrderSyncService(db_session, sample_account.id, mock_whatnot_client)
        with pytest.raises(OrderServiceError) as exc_info:
            svc.push_tracking(order.id, "USPS", "bad")
        assert exc_info.value.status_code == 422

    def test_push_tracking_whatnot_api_error(self, db_session, sample_account, mock_whatnot_client):
        show = Show(account_id=sample_account.id, title="S", platform="whatnot")
        db_session.add(show)
        db_session.flush()
        inv = InventoryItem(account_id=sample_account.id, name="I", status=ItemStatus.AVAILABLE, cogs=0, quantity=1)
        db_session.add(inv)
        db_session.flush()
        order = Order(
            account_id=sample_account.id, show_id=show.id, inventory_item_id=inv.id,
            sale_price=10, buyer_username="b", status=OrderStatus.PENDING,
        )
        order.whatnot_order_id = "wn_123"
        db_session.add(order)
        db_session.flush()

        mock_whatnot_client.execute_mutation.side_effect = WhatnotApiError("server down")
        svc = OrderSyncService(db_session, sample_account.id, mock_whatnot_client)
        with pytest.raises(OrderServiceError) as exc_info:
            svc.push_tracking(order.id, "USPS", "123")
        assert exc_info.value.status_code == 502

    def test_cancel_order_not_found(self, db_session, sample_account, mock_whatnot_client):
        svc = OrderSyncService(db_session, sample_account.id, mock_whatnot_client)
        fake_id = uuid.uuid4()

        with pytest.raises(OrderServiceError):
            svc.cancel_order(fake_id)

    def test_cancel_order_not_linked(self, db_session, sample_account, mock_whatnot_client):
        show = Show(account_id=sample_account.id, title="S", platform="whatnot")
        db_session.add(show)
        db_session.flush()
        inv = InventoryItem(account_id=sample_account.id, name="I", status=ItemStatus.AVAILABLE, cogs=0, quantity=1)
        db_session.add(inv)
        db_session.flush()
        order = Order(
            account_id=sample_account.id, show_id=show.id, inventory_item_id=inv.id,
            sale_price=10, buyer_username="b", status=OrderStatus.PENDING,
        )
        db_session.add(order)
        db_session.flush()

        svc = OrderSyncService(db_session, sample_account.id, mock_whatnot_client)
        with pytest.raises(OrderServiceError, match="not linked"):
            svc.cancel_order(order.id)

    def test_cancel_order_success(self, db_session, sample_account, mock_whatnot_client):
        show = Show(account_id=sample_account.id, title="S", platform="whatnot")
        db_session.add(show)
        db_session.flush()
        inv = InventoryItem(account_id=sample_account.id, name="I", status=ItemStatus.AVAILABLE, cogs=0, quantity=1)
        db_session.add(inv)
        db_session.flush()
        order = Order(
            account_id=sample_account.id, show_id=show.id, inventory_item_id=inv.id,
            sale_price=10, buyer_username="b", status=OrderStatus.PENDING,
        )
        order.whatnot_order_id = "wn_cancel_1"
        db_session.add(order)
        db_session.flush()

        mock_whatnot_client.execute_mutation.return_value = {"order": {"id": "wn_cancel_1", "status": "CANCELLED"}}

        svc = OrderSyncService(db_session, sample_account.id, mock_whatnot_client)
        result = svc.cancel_order(order.id)

        assert result["status"] == "cancelled"
        db_session.refresh(order)
        assert order.status == OrderStatus.CANCELLED

    def test_cancel_order_user_error(self, db_session, sample_account, mock_whatnot_client):
        show = Show(account_id=sample_account.id, title="S", platform="whatnot")
        db_session.add(show)
        db_session.flush()
        inv = InventoryItem(account_id=sample_account.id, name="I", status=ItemStatus.AVAILABLE, cogs=0, quantity=1)
        db_session.add(inv)
        db_session.flush()
        order = Order(
            account_id=sample_account.id, show_id=show.id, inventory_item_id=inv.id,
            sale_price=10, buyer_username="b", status=OrderStatus.PENDING,
        )
        order.whatnot_order_id = "wn_c"
        db_session.add(order)
        db_session.flush()

        mock_whatnot_client.execute_mutation.side_effect = WhatnotUserError("Cannot cancel")
        svc = OrderSyncService(db_session, sample_account.id, mock_whatnot_client)
        with pytest.raises(OrderServiceError) as exc_info:
            svc.cancel_order(order.id)
        assert exc_info.value.status_code == 422

    def test_cancel_order_api_error(self, db_session, sample_account, mock_whatnot_client):
        show = Show(account_id=sample_account.id, title="S", platform="whatnot")
        db_session.add(show)
        db_session.flush()
        inv = InventoryItem(account_id=sample_account.id, name="I", status=ItemStatus.AVAILABLE, cogs=0, quantity=1)
        db_session.add(inv)
        db_session.flush()
        order = Order(
            account_id=sample_account.id, show_id=show.id, inventory_item_id=inv.id,
            sale_price=10, buyer_username="b", status=OrderStatus.PENDING,
        )
        order.whatnot_order_id = "wn_c"
        db_session.add(order)
        db_session.flush()

        mock_whatnot_client.execute_mutation.side_effect = WhatnotApiError("down")
        svc = OrderSyncService(db_session, sample_account.id, mock_whatnot_client)
        with pytest.raises(OrderServiceError) as exc_info:
            svc.cancel_order(order.id)
        assert exc_info.value.status_code == 502
