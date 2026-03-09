"""Tests for sales service layer — shows and orders."""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from services.auth.models.models import User
from services.inventory.models.models import InventoryItem, ItemStatus
from services.sales.models.models import Order, OrderStatus, Show, ShowStatus
from services.sales.services.sales_service import SalesService, SalesServiceError


# ── Show Tests ──────────────────────────────────────────────────────


class TestShowCRUD:
    def test_create_show(self, db_session: Session, sample_account, sample_user, mock_event_publisher) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id, event_publisher=mock_event_publisher)
        result = svc.create_show({"title": "Friday Night Cards"}, actor_id=sample_user.id)
        assert result["title"] == "Friday Night Cards"
        assert result["platform"] == "whatnot"
        assert result["status"] == "planned"
        mock_event_publisher.publish.assert_called_once()

    def test_create_show_with_all_fields(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        dt = datetime(2025, 1, 15, 20, 0, tzinfo=timezone.utc)
        result = svc.create_show(
            {"title": "Sports Cards Night", "platform": "whatnot", "scheduled_at": dt, "notes": "Big show"},
            actor_id=sample_user.id,
        )
        assert result["title"] == "Sports Cards Night"
        assert result["notes"] == "Big show"

    def test_get_show(self, db_session: Session, sample_account, sample_show) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        result = svc.get_show(sample_show.id)
        assert result["title"] == "Friday Night Cards"

    def test_get_show_not_found(self, db_session: Session, sample_account) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        with pytest.raises(SalesServiceError) as exc:
            svc.get_show(uuid.uuid4())
        assert exc.value.status_code == 404

    def test_get_show_cross_account(self, db_session: Session, other_account, sample_show) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, other_account.id)
        with pytest.raises(SalesServiceError) as exc:
            svc.get_show(sample_show.id)
        assert exc.value.status_code == 404

    def test_list_shows(self, db_session: Session, sample_account, sample_show) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        result = svc.list_shows()
        assert len(result["items"]) >= 1
        assert result["total_count"] >= 1

    def test_list_shows_filter_by_status(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        svc.create_show({"title": "Show 1"}, actor_id=sample_user.id)
        result = svc.list_shows(status="planned")
        for item in result["items"]:
            assert item["status"] == "planned"

    def test_update_show(self, db_session: Session, sample_account, sample_show, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        result = svc.update_show(sample_show.id, {"title": "Updated Show"}, actor_id=sample_user.id)
        assert result["title"] == "Updated Show"

    def test_update_show_not_found(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        with pytest.raises(SalesServiceError) as exc:
            svc.update_show(uuid.uuid4(), {"title": "X"}, actor_id=sample_user.id)
        assert exc.value.status_code == 404

    def test_update_show_no_changes(self, db_session: Session, sample_account, sample_show, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        result = svc.update_show(sample_show.id, {"title": "Friday Night Cards"}, actor_id=sample_user.id)
        assert result["title"] == "Friday Night Cards"

    def test_delete_show(self, db_session: Session, sample_account, sample_show, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        svc.delete_show(sample_show.id, actor_id=sample_user.id)
        with pytest.raises(SalesServiceError) as exc:
            svc.get_show(sample_show.id)
        assert exc.value.status_code == 404

    def test_delete_show_not_found(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        with pytest.raises(SalesServiceError) as exc:
            svc.delete_show(uuid.uuid4(), actor_id=sample_user.id)
        assert exc.value.status_code == 404


class TestShowStatusTransitions:
    def test_start_show(self, db_session: Session, sample_account, sample_show, sample_user, mock_event_publisher) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id, event_publisher=mock_event_publisher)
        result = svc.start_show(sample_show.id, actor_id=sample_user.id)
        assert result["status"] == "live"
        assert result["started_at"] is not None
        mock_event_publisher.publish.assert_called_once()

    def test_complete_show(self, db_session: Session, sample_account, sample_show, sample_user, mock_event_publisher) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id, event_publisher=mock_event_publisher)
        svc.start_show(sample_show.id, actor_id=sample_user.id)
        mock_event_publisher.reset_mock()
        result = svc.complete_show(sample_show.id, actor_id=sample_user.id)
        assert result["status"] == "completed"
        assert result["ended_at"] is not None
        mock_event_publisher.publish.assert_called_once()

    def test_cancel_planned_show(self, db_session: Session, sample_account, sample_show, sample_user, mock_event_publisher) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id, event_publisher=mock_event_publisher)
        result = svc.cancel_show(sample_show.id, actor_id=sample_user.id)
        assert result["status"] == "cancelled"

    def test_cancel_live_show(self, db_session: Session, sample_account, sample_show, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        svc.start_show(sample_show.id, actor_id=sample_user.id)
        result = svc.cancel_show(sample_show.id, actor_id=sample_user.id)
        assert result["status"] == "cancelled"

    def test_cannot_start_completed_show(self, db_session: Session, sample_account, sample_show, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        svc.start_show(sample_show.id, actor_id=sample_user.id)
        svc.complete_show(sample_show.id, actor_id=sample_user.id)
        with pytest.raises(SalesServiceError) as exc:
            svc.start_show(sample_show.id, actor_id=sample_user.id)
        assert exc.value.status_code == 409

    def test_cannot_complete_planned_show(self, db_session: Session, sample_account, sample_show, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        with pytest.raises(SalesServiceError) as exc:
            svc.complete_show(sample_show.id, actor_id=sample_user.id)
        assert exc.value.status_code == 409

    def test_cannot_cancel_completed_show(self, db_session: Session, sample_account, sample_show, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        svc.start_show(sample_show.id, actor_id=sample_user.id)
        svc.complete_show(sample_show.id, actor_id=sample_user.id)
        with pytest.raises(SalesServiceError) as exc:
            svc.cancel_show(sample_show.id, actor_id=sample_user.id)
        assert exc.value.status_code == 409

    def test_cannot_cancel_already_cancelled_show(self, db_session: Session, sample_account, sample_show, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        svc.cancel_show(sample_show.id, actor_id=sample_user.id)
        with pytest.raises(SalesServiceError) as exc:
            svc.cancel_show(sample_show.id, actor_id=sample_user.id)
        assert exc.value.status_code == 409

    def test_start_show_not_found(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        with pytest.raises(SalesServiceError) as exc:
            svc.start_show(uuid.uuid4(), actor_id=sample_user.id)
        assert exc.value.status_code == 404

    def test_cancel_show_cancels_orders_and_restores_items(
        self, db_session: Session, sample_account, sample_show, sample_item, sample_user
    ) -> None:
        svc = SalesService(db_session, sample_account.id)
        svc.create_order(
            {"show_id": sample_show.id, "inventory_item_id": sample_item.id, "sale_price": 20.0},
            actor_id=sample_user.id,
        )
        assert sample_item.status == ItemStatus.SOLD

        svc.cancel_show(sample_show.id, actor_id=sample_user.id)
        assert sample_item.status == ItemStatus.AVAILABLE


# ── Order Tests ─────────────────────────────────────────────────────


class TestOrderCRUD:
    def test_create_order(self, db_session: Session, sample_account, sample_show, sample_item, sample_user, mock_event_publisher) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id, event_publisher=mock_event_publisher)
        result = svc.create_order(
            {"show_id": sample_show.id, "inventory_item_id": sample_item.id, "sale_price": 25.0, "platform_fees": 2.50, "shipping_cost": 5.0},
            actor_id=sample_user.id,
        )
        assert result["sale_price"] == 25.0
        assert result["cost_basis"] == 10.5  # from sample_item.cogs
        assert result["profit"] == 7.0  # 25 - 2.5 - 5 - 10.5
        assert result["status"] == "pending"
        assert sample_item.status == ItemStatus.SOLD
        mock_event_publisher.publish.assert_called_once()

    def test_create_order_zero_cogs(self, db_session: Session, sample_account, sample_show, sample_item_no_cogs, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        result = svc.create_order(
            {"show_id": sample_show.id, "inventory_item_id": sample_item_no_cogs.id, "sale_price": 20.0, "platform_fees": 2.0},
            actor_id=sample_user.id,
        )
        assert result["cost_basis"] == 0.0
        assert result["profit"] == 18.0  # 20 - 2 - 0 - 0

    def test_create_order_show_not_found(self, db_session: Session, sample_account, sample_item, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        with pytest.raises(SalesServiceError) as exc:
            svc.create_order(
                {"show_id": uuid.uuid4(), "inventory_item_id": sample_item.id, "sale_price": 10.0},
                actor_id=sample_user.id,
            )
        assert exc.value.status_code == 404

    def test_create_order_item_not_found(self, db_session: Session, sample_account, sample_show, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        with pytest.raises(SalesServiceError) as exc:
            svc.create_order(
                {"show_id": sample_show.id, "inventory_item_id": uuid.uuid4(), "sale_price": 10.0},
                actor_id=sample_user.id,
            )
        assert exc.value.status_code == 404

    def test_create_order_item_already_sold(self, db_session: Session, sample_account, sample_show, sample_item, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        svc.create_order(
            {"show_id": sample_show.id, "inventory_item_id": sample_item.id, "sale_price": 20.0},
            actor_id=sample_user.id,
        )
        # Create another item that's already sold
        with pytest.raises(SalesServiceError) as exc:
            svc.create_order(
                {"show_id": sample_show.id, "inventory_item_id": sample_item.id, "sale_price": 30.0},
                actor_id=sample_user.id,
            )
        assert exc.value.status_code == 409

    def test_create_order_cross_account_item(self, db_session: Session, other_account, sample_show, sample_item, sample_user) -> None:  # type: ignore[no-untyped-def]
        # Other account tries to use sample_item that belongs to sample_account
        other_show = Show(account_id=other_account.id, title="Other Show")
        db_session.add(other_show)
        db_session.flush()
        other_user = User(
            account_id=other_account.id, email="other@test.com", password_hash="", name="Other", role="owner", is_verified=True, is_active=True,
        )
        other_user.set_password("StrongPass1")
        db_session.add(other_user)
        db_session.flush()

        svc = SalesService(db_session, other_account.id)
        with pytest.raises(SalesServiceError) as exc:
            svc.create_order(
                {"show_id": other_show.id, "inventory_item_id": sample_item.id, "sale_price": 10.0},
                actor_id=other_user.id,
            )
        assert exc.value.status_code == 404

    def test_get_order(self, db_session: Session, sample_account, sample_order) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        result = svc.get_order(sample_order.id)
        assert result["sale_price"] == 25.0

    def test_get_order_not_found(self, db_session: Session, sample_account) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        with pytest.raises(SalesServiceError) as exc:
            svc.get_order(uuid.uuid4())
        assert exc.value.status_code == 404

    def test_get_order_cross_account(self, db_session: Session, other_account, sample_order) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, other_account.id)
        with pytest.raises(SalesServiceError) as exc:
            svc.get_order(sample_order.id)
        assert exc.value.status_code == 404

    def test_list_orders(self, db_session: Session, sample_account, sample_order) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        result = svc.list_orders()
        assert len(result["items"]) >= 1

    def test_list_orders_filter_by_show(self, db_session: Session, sample_account, sample_show, sample_order) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        result = svc.list_orders(show_id=sample_show.id)
        assert len(result["items"]) >= 1
        for item in result["items"]:
            assert item["show_id"] == str(sample_show.id)

    def test_list_show_orders_with_summary(self, db_session: Session, sample_account, sample_show, sample_order) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        result = svc.list_show_orders(sample_show.id)
        assert len(result["orders"]) >= 1
        assert result["summary"]["order_count"] >= 1
        assert result["summary"]["total_revenue"] > 0

    def test_list_show_orders_not_found(self, db_session: Session, sample_account) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        with pytest.raises(SalesServiceError) as exc:
            svc.list_show_orders(uuid.uuid4())
        assert exc.value.status_code == 404

    def test_update_order(self, db_session: Session, sample_account, sample_order, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        result = svc.update_order(
            sample_order.id,
            {"sale_price": 30.0},
            actor_id=sample_user.id,
        )
        assert result["sale_price"] == 30.0
        # Profit recalculated: 30 - 2.5 - 5 - 10.5 = 12.0
        assert result["profit"] == 12.0

    def test_update_order_status(self, db_session: Session, sample_account, sample_order, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        result = svc.update_order(
            sample_order.id,
            {"status": "shipped"},
            actor_id=sample_user.id,
        )
        assert result["status"] == "shipped"

    def test_update_cancelled_order_fails(self, db_session: Session, sample_account, sample_order, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        svc.cancel_order(sample_order.id, actor_id=sample_user.id)
        with pytest.raises(SalesServiceError) as exc:
            svc.update_order(sample_order.id, {"sale_price": 50.0}, actor_id=sample_user.id)
        assert exc.value.status_code == 409

    def test_update_order_not_found(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        with pytest.raises(SalesServiceError) as exc:
            svc.update_order(uuid.uuid4(), {"sale_price": 50.0}, actor_id=sample_user.id)
        assert exc.value.status_code == 404

    def test_update_order_no_changes(self, db_session: Session, sample_account, sample_order, sample_user, mock_event_publisher) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id, event_publisher=mock_event_publisher)
        result = svc.update_order(sample_order.id, {"sale_price": 25.0}, actor_id=sample_user.id)
        assert result["sale_price"] == 25.0
        mock_event_publisher.publish.assert_not_called()


class TestOrderCancel:
    def test_cancel_order(self, db_session: Session, sample_account, sample_order, sample_item, sample_user, mock_event_publisher) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id, event_publisher=mock_event_publisher)
        assert sample_item.status == ItemStatus.SOLD
        result = svc.cancel_order(sample_order.id, actor_id=sample_user.id)
        assert result["status"] == "cancelled"
        assert sample_item.status == ItemStatus.AVAILABLE
        mock_event_publisher.publish.assert_called_once()

    def test_cancel_already_cancelled(self, db_session: Session, sample_account, sample_order, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        svc.cancel_order(sample_order.id, actor_id=sample_user.id)
        with pytest.raises(SalesServiceError) as exc:
            svc.cancel_order(sample_order.id, actor_id=sample_user.id)
        assert exc.value.status_code == 409

    def test_cancel_order_not_found(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        with pytest.raises(SalesServiceError) as exc:
            svc.cancel_order(uuid.uuid4(), actor_id=sample_user.id)
        assert exc.value.status_code == 404


class TestOrderSoftDelete:
    def test_delete_order(self, db_session: Session, sample_account, sample_order, sample_item, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        assert sample_item.status == ItemStatus.SOLD
        svc.delete_order(sample_order.id, actor_id=sample_user.id)
        # Item restored to available
        assert sample_item.status == ItemStatus.AVAILABLE
        with pytest.raises(SalesServiceError):
            svc.get_order(sample_order.id)

    def test_delete_cancelled_order_doesnt_restore(self, db_session: Session, sample_account, sample_order, sample_item, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        svc.cancel_order(sample_order.id, actor_id=sample_user.id)
        assert sample_item.status == ItemStatus.AVAILABLE
        # Deleting an already-cancelled order shouldn't change item status
        svc.delete_order(sample_order.id, actor_id=sample_user.id)
        assert sample_item.status == ItemStatus.AVAILABLE

    def test_delete_order_not_found(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        with pytest.raises(SalesServiceError) as exc:
            svc.delete_order(uuid.uuid4(), actor_id=sample_user.id)
        assert exc.value.status_code == 404

    def test_list_deleted_orders(self, db_session: Session, sample_account, sample_order, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        svc.delete_order(sample_order.id, actor_id=sample_user.id)
        deleted = svc.list_deleted_orders()
        assert len(deleted) >= 1

    def test_restore_order(self, db_session: Session, sample_account, sample_order, sample_item, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        svc.delete_order(sample_order.id, actor_id=sample_user.id)
        assert sample_item.status == ItemStatus.AVAILABLE

        result = svc.restore_order(sample_order.id, actor_id=sample_user.id)
        assert result["deleted_at"] is None
        assert sample_item.status == ItemStatus.SOLD

    def test_restore_order_not_found(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = SalesService(db_session, sample_account.id)
        with pytest.raises(SalesServiceError) as exc:
            svc.restore_order(uuid.uuid4(), actor_id=sample_user.id)
        assert exc.value.status_code == 404
