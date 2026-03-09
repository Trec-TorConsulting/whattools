"""Sales service layer — show and order management, profit calculation, audit logging."""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.inventory.models.models import InventoryItem, ItemStatus
from services.sales.models.models import (
    Order,
    OrderStatus,
    Show,
    ShowStatus,
    SHOW_TRANSITIONS,
)
from services.sales.repositories.sales_repository import OrderRepository, ShowRepository
from services.shared.audit import log_audit
from services.shared.events import EventPublisher
from services.shared.logging import get_logger

logger = get_logger("sales_service")


class SalesServiceError(Exception):
    """Base exception for sales service errors."""

    def __init__(self, message: str, code: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class SalesService:
    """Show and order management with profit calculation and audit logging."""

    def __init__(
        self,
        db: Session,
        account_id: uuid.UUID,
        *,
        event_publisher: EventPublisher | None = None,
    ) -> None:
        self.db = db
        self.account_id = account_id
        self.show_repo = ShowRepository(db, account_id)
        self.order_repo = OrderRepository(db, account_id)
        self.event_publisher = event_publisher

    # ── Show Management ─────────────────────────────────────────────

    def create_show(self, data: dict[str, Any], *, actor_id: uuid.UUID) -> dict[str, Any]:
        """Create a new show."""
        show = Show(
            account_id=self.account_id,
            title=data["title"],
            platform=data.get("platform", "whatnot"),
            scheduled_at=data.get("scheduled_at"),
            notes=data.get("notes", ""),
        )
        self.show_repo.create(show)

        log_audit(
            self.db,
            account_id=self.account_id,
            actor_id=actor_id,
            action="create",
            resource_type="shows",
            resource_id=show.id,
        )
        self.db.commit()

        self._publish_event("show.created", {
            "show_id": str(show.id),
            "account_id": str(self.account_id),
            "title": show.title,
        })

        return self._show_to_dict(show)

    def get_show(self, show_id: uuid.UUID) -> dict[str, Any]:
        """Get a single show by ID."""
        show = self.show_repo.get_by_id(show_id)
        if show is None:
            raise SalesServiceError("Show not found.", "not_found", 404)
        return self._show_to_dict(show)

    def list_shows(
        self,
        *,
        cursor: str | None = None,
        limit: int = 50,
        status: str | None = None,
    ) -> dict[str, Any]:
        """List shows with pagination and optional status filter."""
        result = self.show_repo.list_shows(cursor=cursor, limit=limit, status=status)
        return {
            "items": [self._show_to_dict(s) for s in result.items],
            "total_count": result.total_count,
            "next_cursor": result.next_cursor,
        }

    def update_show(self, show_id: uuid.UUID, updates: dict[str, Any], *, actor_id: uuid.UUID) -> dict[str, Any]:
        """Update a show's details."""
        show = self.show_repo.get_by_id(show_id)
        if show is None:
            raise SalesServiceError("Show not found.", "not_found", 404)

        changes: dict[str, Any] = {}
        for key, value in updates.items():
            old_val = getattr(show, key, None)
            if old_val != value:
                changes[key] = {"old": str(old_val) if old_val else old_val, "new": str(value) if value else value}
                setattr(show, key, value)

        if changes:
            show.updated_at = datetime.now(timezone.utc)
            self.show_repo.save()
            log_audit(
                self.db,
                account_id=self.account_id,
                actor_id=actor_id,
                action="update",
                resource_type="shows",
                resource_id=show.id,
                changes=changes,
            )
            self.db.commit()

        return self._show_to_dict(show)

    def delete_show(self, show_id: uuid.UUID, *, actor_id: uuid.UUID) -> None:
        """Soft-delete a show."""
        show = self.show_repo.get_by_id(show_id)
        if show is None:
            raise SalesServiceError("Show not found.", "not_found", 404)

        show.deleted_at = datetime.now(timezone.utc)
        self.show_repo.save()

        log_audit(
            self.db,
            account_id=self.account_id,
            actor_id=actor_id,
            action="delete",
            resource_type="shows",
            resource_id=show.id,
        )
        self.db.commit()

    def start_show(self, show_id: uuid.UUID, *, actor_id: uuid.UUID) -> dict[str, Any]:
        """Transition a show from planned → live."""
        return self._transition_show(show_id, ShowStatus.LIVE, actor_id=actor_id)

    def complete_show(self, show_id: uuid.UUID, *, actor_id: uuid.UUID) -> dict[str, Any]:
        """Transition a show from live → completed."""
        return self._transition_show(show_id, ShowStatus.COMPLETED, actor_id=actor_id)

    def cancel_show(self, show_id: uuid.UUID, *, actor_id: uuid.UUID) -> dict[str, Any]:
        """Cancel a show and all its pending orders."""
        show = self.show_repo.get_by_id(show_id)
        if show is None:
            raise SalesServiceError("Show not found.", "not_found", 404)

        allowed = SHOW_TRANSITIONS.get(show.status, [])
        if ShowStatus.CANCELLED not in allowed:
            raise SalesServiceError(
                f"Cannot cancel a show with status '{show.status}'. Allowed transitions: {allowed}",
                "conflict",
                409,
            )

        # Cancel all non-cancelled orders and restore inventory items
        orders = self.order_repo.list_by_show(show_id)
        for order in orders:
            if order.status != OrderStatus.CANCELLED:
                order.status = OrderStatus.CANCELLED
                order.updated_at = datetime.now(timezone.utc)
                self._restore_item_status(order.inventory_item_id)

        show.status = ShowStatus.CANCELLED
        show.updated_at = datetime.now(timezone.utc)
        self.show_repo.save()

        log_audit(
            self.db,
            account_id=self.account_id,
            actor_id=actor_id,
            action="cancel",
            resource_type="shows",
            resource_id=show.id,
            changes={"status": {"old": show.status, "new": ShowStatus.CANCELLED}},
        )
        self.db.commit()

        self._publish_event("show.cancelled", {
            "show_id": str(show.id),
            "account_id": str(self.account_id),
        })

        return self._show_to_dict(show)

    def _transition_show(self, show_id: uuid.UUID, target: str, *, actor_id: uuid.UUID) -> dict[str, Any]:
        """Transition a show to a new status."""
        show = self.show_repo.get_by_id(show_id)
        if show is None:
            raise SalesServiceError("Show not found.", "not_found", 404)

        allowed = SHOW_TRANSITIONS.get(show.status, [])
        if target not in allowed:
            raise SalesServiceError(
                f"Cannot transition from '{show.status}' to '{target}'. Allowed: {allowed}",
                "conflict",
                409,
            )

        old_status = show.status
        show.status = target
        show.updated_at = datetime.now(timezone.utc)

        if target == ShowStatus.LIVE:
            show.started_at = datetime.now(timezone.utc)
        elif target == ShowStatus.COMPLETED:
            show.ended_at = datetime.now(timezone.utc)

        self.show_repo.save()

        log_audit(
            self.db,
            account_id=self.account_id,
            actor_id=actor_id,
            action="status_change",
            resource_type="shows",
            resource_id=show.id,
            changes={"status": {"old": old_status, "new": target}},
        )
        self.db.commit()

        event_map = {
            ShowStatus.LIVE: "show.started",
            ShowStatus.COMPLETED: "show.completed",
        }
        event_type = event_map.get(target)
        if event_type:
            self._publish_event(event_type, {
                "show_id": str(show.id),
                "account_id": str(self.account_id),
            })

        return self._show_to_dict(show)

    # ── Order Management ────────────────────────────────────────────

    def create_order(self, data: dict[str, Any], *, actor_id: uuid.UUID) -> dict[str, Any]:
        """Create an order, linking a show to an inventory item."""
        # Validate show exists and belongs to this account
        show = self.show_repo.get_by_id(data["show_id"])
        if show is None:
            raise SalesServiceError("Show not found.", "not_found", 404)

        # Validate inventory item exists and belongs to this account
        item = self.db.execute(
            select(InventoryItem).where(
                InventoryItem.id == data["inventory_item_id"],
                InventoryItem.account_id == self.account_id,
                InventoryItem.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

        if item is None:
            raise SalesServiceError("Inventory item not found.", "not_found", 404)

        # Check item isn't already sold
        if item.status == ItemStatus.SOLD:
            raise SalesServiceError("Item is already sold.", "conflict", 409)

        # Existing active order for this item?
        existing = self.order_repo.get_by_item_id(data["inventory_item_id"])
        if existing is not None:
            raise SalesServiceError("An active order already exists for this item.", "conflict", 409)

        # Calculate profit
        cost_basis = float(item.cogs)
        sale_price = float(data["sale_price"])
        platform_fees = float(data.get("platform_fees", 0.0))
        shipping_cost = float(data.get("shipping_cost", 0.0))
        profit = sale_price - platform_fees - shipping_cost - cost_basis

        order = Order(
            account_id=self.account_id,
            show_id=data["show_id"],
            inventory_item_id=data["inventory_item_id"],
            sale_price=sale_price,
            platform_fees=platform_fees,
            shipping_cost=shipping_cost,
            cost_basis=cost_basis,
            profit=profit,
            buyer_username=data.get("buyer_username", ""),
            notes=data.get("notes", ""),
        )
        self.order_repo.create(order)

        # Mark item as sold
        item.status = ItemStatus.SOLD
        item.updated_at = datetime.now(timezone.utc)

        log_audit(
            self.db,
            account_id=self.account_id,
            actor_id=actor_id,
            action="create",
            resource_type="orders",
            resource_id=order.id,
        )
        self.db.commit()

        self._publish_event("order.created", {
            "order_id": str(order.id),
            "show_id": str(order.show_id),
            "item_id": str(order.inventory_item_id),
            "account_id": str(self.account_id),
            "profit": float(profit),
        })

        return self._order_to_dict(order)

    def get_order(self, order_id: uuid.UUID) -> dict[str, Any]:
        """Get a single order by ID."""
        order = self.order_repo.get_by_id(order_id)
        if order is None:
            raise SalesServiceError("Order not found.", "not_found", 404)
        return self._order_to_dict(order)

    def list_orders(
        self,
        *,
        cursor: str | None = None,
        limit: int = 50,
        show_id: uuid.UUID | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """List orders with pagination and optional filters."""
        result = self.order_repo.list_orders(cursor=cursor, limit=limit, show_id=show_id, status=status)
        return {
            "items": [self._order_to_dict(o) for o in result.items],
            "total_count": result.total_count,
            "next_cursor": result.next_cursor,
        }

    def list_show_orders(self, show_id: uuid.UUID) -> dict[str, Any]:
        """List all orders for a specific show with summary."""
        show = self.show_repo.get_by_id(show_id)
        if show is None:
            raise SalesServiceError("Show not found.", "not_found", 404)

        orders = self.order_repo.list_by_show(show_id)
        order_dicts = [self._order_to_dict(o) for o in orders]

        total_revenue = sum(float(o.sale_price) for o in orders)
        total_profit = sum(float(o.profit) for o in orders)

        return {
            "orders": order_dicts,
            "summary": {
                "order_count": len(orders),
                "total_revenue": round(total_revenue, 2),
                "total_profit": round(total_profit, 2),
            },
        }

    def update_order(self, order_id: uuid.UUID, updates: dict[str, Any], *, actor_id: uuid.UUID) -> dict[str, Any]:
        """Update an order."""
        order = self.order_repo.get_by_id(order_id)
        if order is None:
            raise SalesServiceError("Order not found.", "not_found", 404)

        if order.status == OrderStatus.CANCELLED:
            raise SalesServiceError("Cannot update a cancelled order.", "conflict", 409)

        changes: dict[str, Any] = {}
        recalc = False
        for key, value in updates.items():
            old_val = getattr(order, key, None)
            if old_val != value:
                changes[key] = {"old": old_val, "new": value}
                setattr(order, key, value)
                if key in ("sale_price", "platform_fees", "shipping_cost"):
                    recalc = True

        if recalc:
            order.profit = float(order.sale_price) - float(order.platform_fees) - float(order.shipping_cost) - float(order.cost_basis)

        if changes:
            order.updated_at = datetime.now(timezone.utc)
            self.order_repo.save()
            log_audit(
                self.db,
                account_id=self.account_id,
                actor_id=actor_id,
                action="update",
                resource_type="orders",
                resource_id=order.id,
                changes=changes,
            )
            self.db.commit()

            self._publish_event("order.updated", {
                "order_id": str(order.id),
                "account_id": str(self.account_id),
                "changes": list(changes.keys()),
            })

        return self._order_to_dict(order)

    def cancel_order(self, order_id: uuid.UUID, *, actor_id: uuid.UUID) -> dict[str, Any]:
        """Cancel an order and restore the inventory item to active."""
        order = self.order_repo.get_by_id(order_id)
        if order is None:
            raise SalesServiceError("Order not found.", "not_found", 404)

        if order.status == OrderStatus.CANCELLED:
            raise SalesServiceError("Order is already cancelled.", "conflict", 409)

        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.now(timezone.utc)
        self.order_repo.save()

        # Restore inventory item
        self._restore_item_status(order.inventory_item_id)

        log_audit(
            self.db,
            account_id=self.account_id,
            actor_id=actor_id,
            action="cancel",
            resource_type="orders",
            resource_id=order.id,
        )
        self.db.commit()

        self._publish_event("order.cancelled", {
            "order_id": str(order.id),
            "item_id": str(order.inventory_item_id),
            "account_id": str(self.account_id),
        })

        return self._order_to_dict(order)

    def delete_order(self, order_id: uuid.UUID, *, actor_id: uuid.UUID) -> None:
        """Soft-delete an order and restore inventory item."""
        order = self.order_repo.get_by_id(order_id)
        if order is None:
            raise SalesServiceError("Order not found.", "not_found", 404)

        # If order wasn't cancelled, restore the item
        if order.status != OrderStatus.CANCELLED:
            self._restore_item_status(order.inventory_item_id)

        order.deleted_at = datetime.now(timezone.utc)
        self.order_repo.save()

        log_audit(
            self.db,
            account_id=self.account_id,
            actor_id=actor_id,
            action="delete",
            resource_type="orders",
            resource_id=order.id,
        )
        self.db.commit()

    def list_deleted_orders(self) -> list[dict[str, Any]]:
        """List soft-deleted orders within 30-day retention."""
        orders = self.order_repo.list_deleted()
        return [self._order_to_dict(o) for o in orders]

    def restore_order(self, order_id: uuid.UUID, *, actor_id: uuid.UUID) -> dict[str, Any]:
        """Restore a soft-deleted order."""
        order = self.db.execute(
            select(Order).where(
                Order.id == order_id,
                Order.account_id == self.account_id,
                Order.deleted_at.is_not(None),
            )
        ).scalar_one_or_none()

        if order is None:
            raise SalesServiceError("Deleted order not found.", "not_found", 404)

        # If the order was not cancelled, re-mark the item as sold
        if order.status != OrderStatus.CANCELLED:
            item = self.db.execute(
                select(InventoryItem).where(
                    InventoryItem.id == order.inventory_item_id,
                    InventoryItem.account_id == self.account_id,
                    InventoryItem.deleted_at.is_(None),
                )
            ).scalar_one_or_none()

            if item is not None and item.status == ItemStatus.AVAILABLE:
                item.status = ItemStatus.SOLD
                item.updated_at = datetime.now(timezone.utc)

        order.deleted_at = None
        order.updated_at = datetime.now(timezone.utc)
        self.order_repo.save()

        log_audit(
            self.db,
            account_id=self.account_id,
            actor_id=actor_id,
            action="restore",
            resource_type="orders",
            resource_id=order.id,
        )
        self.db.commit()

        return self._order_to_dict(order)

    # ── Helpers ─────────────────────────────────────────────────────

    def _restore_item_status(self, item_id: uuid.UUID) -> None:
        """Restore an inventory item from sold to available."""
        item = self.db.execute(
            select(InventoryItem).where(
                InventoryItem.id == item_id,
                InventoryItem.account_id == self.account_id,
                InventoryItem.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

        if item is not None and item.status == ItemStatus.SOLD:
            item.status = ItemStatus.AVAILABLE
            item.updated_at = datetime.now(timezone.utc)

    def _show_to_dict(self, show: Show) -> dict[str, Any]:
        return {
            "id": str(show.id),
            "account_id": str(show.account_id),
            "title": show.title,
            "platform": show.platform,
            "scheduled_at": show.scheduled_at.isoformat() if show.scheduled_at else None,
            "started_at": show.started_at.isoformat() if show.started_at else None,
            "ended_at": show.ended_at.isoformat() if show.ended_at else None,
            "status": show.status,
            "notes": show.notes,
            "created_at": show.created_at.isoformat(),
            "updated_at": show.updated_at.isoformat(),
            "deleted_at": show.deleted_at.isoformat() if show.deleted_at else None,
        }

    def _order_to_dict(self, order: Order) -> dict[str, Any]:
        return {
            "id": str(order.id),
            "account_id": str(order.account_id),
            "show_id": str(order.show_id),
            "inventory_item_id": str(order.inventory_item_id),
            "sale_price": float(order.sale_price),
            "platform_fees": float(order.platform_fees),
            "shipping_cost": float(order.shipping_cost),
            "cost_basis": float(order.cost_basis),
            "profit": float(order.profit),
            "buyer_username": order.buyer_username,
            "status": order.status,
            "notes": order.notes,
            "created_at": order.created_at.isoformat(),
            "updated_at": order.updated_at.isoformat(),
            "deleted_at": order.deleted_at.isoformat() if order.deleted_at else None,
        }

    def _publish_event(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.event_publisher is not None:
            self.event_publisher.publish(event_type, payload, source_service="sales")
