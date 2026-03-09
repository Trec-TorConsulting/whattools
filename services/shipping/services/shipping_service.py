"""Shipping service layer — shipment management, bulk operations, packing lists."""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.inventory.models.models import InventoryItem
from services.sales.models.models import Order, OrderStatus, Show
from services.shipping.models.models import Shipment, ShipmentStatus, SHIPMENT_TRANSITIONS
from services.shipping.providers.base import ShippingProvider
from services.shipping.providers.manual import ManualProvider
from services.shipping.repositories.shipping_repository import ShipmentRepository
from services.shared.audit import log_audit
from services.shared.events import EventPublisher
from services.shared.logging import get_logger

logger = get_logger("shipping_service")


class ShippingServiceError(Exception):
    """Base exception for shipping service errors."""

    def __init__(self, message: str, code: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class ShippingService:
    """Shipment management with bulk operations and packing list generation."""

    def __init__(
        self,
        db: Session,
        account_id: uuid.UUID,
        *,
        event_publisher: EventPublisher | None = None,
        shipping_provider: ShippingProvider | None = None,
    ) -> None:
        self.db = db
        self.account_id = account_id
        self.repo = ShipmentRepository(db, account_id)
        self.event_publisher = event_publisher
        self.provider = shipping_provider or ManualProvider()

    # ── Shipment CRUD ───────────────────────────────────────────────

    def create_shipment(self, data: dict[str, Any], *, actor_id: uuid.UUID) -> dict[str, Any]:
        """Create a shipment for an order."""
        order_id = data["order_id"]

        # Validate order exists and belongs to this account
        order = self.db.execute(
            select(Order).where(
                Order.id == order_id,
                Order.account_id == self.account_id,
                Order.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

        if order is None:
            raise ShippingServiceError("Order not found.", "not_found", 404)

        # Check no active shipment already exists for this order
        existing = self.repo.get_by_order_id(order_id)
        if existing is not None:
            raise ShippingServiceError(
                "An active shipment already exists for this order.", "conflict", 409
            )

        shipment = Shipment(
            account_id=self.account_id,
            order_id=order_id,
            carrier=data.get("carrier", ""),
            tracking_number=data.get("tracking_number", ""),
            label_url=data.get("label_url", ""),
            ship_by_date=data.get("ship_by_date"),
            weight_oz=data.get("weight_oz", 0.0),
            buyer_name=data.get("buyer_name", ""),
            address_line1=data.get("address_line1", ""),
            address_line2=data.get("address_line2", ""),
            city=data.get("city", ""),
            state=data.get("state", ""),
            zip_code=data.get("zip_code", ""),
            country=data.get("country", "US"),
            notes=data.get("notes", ""),
        )
        self.repo.create(shipment)

        log_audit(
            self.db,
            account_id=self.account_id,
            actor_id=actor_id,
            action="create",
            resource_type="shipments",
            resource_id=shipment.id,
        )
        self.db.commit()

        self._publish_event("shipment.created", {
            "shipment_id": str(shipment.id),
            "order_id": str(order_id),
            "account_id": str(self.account_id),
        })

        return self._shipment_to_dict(shipment)

    def get_shipment(self, shipment_id: uuid.UUID) -> dict[str, Any]:
        """Get a single shipment by ID."""
        shipment = self.repo.get_by_id(shipment_id)
        if shipment is None:
            raise ShippingServiceError("Shipment not found.", "not_found", 404)
        return self._shipment_to_dict(shipment)

    def list_shipments(
        self,
        *,
        cursor: str | None = None,
        limit: int = 50,
        status: str | None = None,
        order_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """List shipments with pagination and optional filters."""
        result = self.repo.list_shipments(cursor=cursor, limit=limit, status=status, order_id=order_id)
        return {
            "items": [self._shipment_to_dict(s) for s in result.items],
            "total_count": result.total_count,
            "next_cursor": result.next_cursor,
        }

    def update_shipment(
        self, shipment_id: uuid.UUID, updates: dict[str, Any], *, actor_id: uuid.UUID
    ) -> dict[str, Any]:
        """Update a shipment's details."""
        shipment = self.repo.get_by_id(shipment_id)
        if shipment is None:
            raise ShippingServiceError("Shipment not found.", "not_found", 404)

        if shipment.status == ShipmentStatus.CANCELLED:
            raise ShippingServiceError("Cannot update a cancelled shipment.", "conflict", 409)

        changes: dict[str, Any] = {}
        for key, value in updates.items():
            old_val = getattr(shipment, key, None)
            if old_val != value:
                changes[key] = {"old": str(old_val) if old_val else old_val, "new": str(value) if value else value}
                setattr(shipment, key, value)

        if changes:
            shipment.updated_at = datetime.now(timezone.utc)
            self.repo.save()
            log_audit(
                self.db,
                account_id=self.account_id,
                actor_id=actor_id,
                action="update",
                resource_type="shipments",
                resource_id=shipment.id,
                changes=changes,
            )
            self.db.commit()

            self._publish_event("shipment.updated", {
                "shipment_id": str(shipment.id),
                "account_id": str(self.account_id),
                "changes": list(changes.keys()),
            })

        return self._shipment_to_dict(shipment)

    def delete_shipment(self, shipment_id: uuid.UUID, *, actor_id: uuid.UUID) -> None:
        """Soft-delete a shipment."""
        shipment = self.repo.get_by_id(shipment_id)
        if shipment is None:
            raise ShippingServiceError("Shipment not found.", "not_found", 404)

        shipment.deleted_at = datetime.now(timezone.utc)
        self.repo.save()

        log_audit(
            self.db,
            account_id=self.account_id,
            actor_id=actor_id,
            action="delete",
            resource_type="shipments",
            resource_id=shipment.id,
        )
        self.db.commit()

    def list_deleted_shipments(self) -> list[dict[str, Any]]:
        """List soft-deleted shipments within 30-day retention."""
        shipments = self.repo.list_deleted()
        return [self._shipment_to_dict(s) for s in shipments]

    def restore_shipment(self, shipment_id: uuid.UUID, *, actor_id: uuid.UUID) -> dict[str, Any]:
        """Restore a soft-deleted shipment."""
        shipment = self.db.execute(
            select(Shipment).where(
                Shipment.id == shipment_id,
                Shipment.account_id == self.account_id,
                Shipment.deleted_at.is_not(None),
            )
        ).scalar_one_or_none()

        if shipment is None:
            raise ShippingServiceError("Deleted shipment not found.", "not_found", 404)

        shipment.deleted_at = None
        shipment.updated_at = datetime.now(timezone.utc)
        self.repo.save()

        log_audit(
            self.db,
            account_id=self.account_id,
            actor_id=actor_id,
            action="restore",
            resource_type="shipments",
            resource_id=shipment.id,
        )
        self.db.commit()

        return self._shipment_to_dict(shipment)

    # ── Status Transitions ──────────────────────────────────────────

    def transition_shipment(
        self, shipment_id: uuid.UUID, target_status: str, *, actor_id: uuid.UUID
    ) -> dict[str, Any]:
        """Transition a shipment to a new status."""
        shipment = self.repo.get_by_id(shipment_id)
        if shipment is None:
            raise ShippingServiceError("Shipment not found.", "not_found", 404)

        allowed = SHIPMENT_TRANSITIONS.get(shipment.status, [])
        if target_status not in allowed:
            raise ShippingServiceError(
                f"Cannot transition from '{shipment.status}' to '{target_status}'. Allowed: {allowed}",
                "conflict",
                409,
            )

        old_status = shipment.status
        shipment.status = target_status
        shipment.updated_at = datetime.now(timezone.utc)

        if target_status == ShipmentStatus.SHIPPED:
            shipment.shipped_at = datetime.now(timezone.utc)
            self._update_order_status(shipment.order_id, OrderStatus.SHIPPED)
        elif target_status == ShipmentStatus.DELIVERED:
            shipment.delivered_at = datetime.now(timezone.utc)
            self._update_order_status(shipment.order_id, OrderStatus.DELIVERED)

        self.repo.save()

        log_audit(
            self.db,
            account_id=self.account_id,
            actor_id=actor_id,
            action="status_change",
            resource_type="shipments",
            resource_id=shipment.id,
            changes={"status": {"old": old_status, "new": target_status}},
        )
        self.db.commit()

        event_map = {
            ShipmentStatus.LABEL_CREATED: "shipment.label_created",
            ShipmentStatus.SHIPPED: "shipment.shipped",
            ShipmentStatus.DELIVERED: "shipment.delivered",
            ShipmentStatus.CANCELLED: "shipment.cancelled",
        }
        event_type = event_map.get(target_status)
        if event_type:
            self._publish_event(event_type, {
                "shipment_id": str(shipment.id),
                "order_id": str(shipment.order_id),
                "account_id": str(self.account_id),
            })

        return self._shipment_to_dict(shipment)

    def create_label(self, shipment_id: uuid.UUID, *, actor_id: uuid.UUID) -> dict[str, Any]:
        """Create a shipping label via the provider and transition to LABEL_CREATED."""
        shipment = self.repo.get_by_id(shipment_id)
        if shipment is None:
            raise ShippingServiceError("Shipment not found.", "not_found", 404)

        if shipment.status != ShipmentStatus.PENDING:
            raise ShippingServiceError(
                f"Can only create labels for pending shipments. Current status: {shipment.status}",
                "conflict",
                409,
            )

        to_address = {
            "name": shipment.buyer_name,
            "street1": shipment.address_line1,
            "street2": shipment.address_line2,
            "city": shipment.city,
            "state": shipment.state,
            "zip": shipment.zip_code,
            "country": shipment.country,
        }

        result = self.provider.create_label(
            from_address={},
            to_address=to_address,
            weight_oz=float(shipment.weight_oz),
            carrier=shipment.carrier or None,
        )

        if not result.success:
            raise ShippingServiceError(
                f"Label creation failed: {result.error}", "provider_error", 502
            )

        if result.label_url:
            shipment.label_url = result.label_url
        if result.tracking_number:
            shipment.tracking_number = result.tracking_number

        shipment.status = ShipmentStatus.LABEL_CREATED
        shipment.updated_at = datetime.now(timezone.utc)
        self.repo.save()

        log_audit(
            self.db,
            account_id=self.account_id,
            actor_id=actor_id,
            action="create_label",
            resource_type="shipments",
            resource_id=shipment.id,
        )
        self.db.commit()

        self._publish_event("shipment.label_created", {
            "shipment_id": str(shipment.id),
            "account_id": str(self.account_id),
        })

        return self._shipment_to_dict(shipment)

    # ── Bulk Operations ─────────────────────────────────────────────

    def bulk_create_shipments(
        self, show_id: uuid.UUID, data: dict[str, Any], *, actor_id: uuid.UUID
    ) -> dict[str, Any]:
        """Create shipments for all pending orders in a show that don't already have one."""
        # Validate show exists and belongs to this account
        show = self.db.execute(
            select(Show).where(
                Show.id == show_id,
                Show.account_id == self.account_id,
                Show.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

        if show is None:
            raise ShippingServiceError("Show not found.", "not_found", 404)

        # Get all non-cancelled, non-deleted orders for this show
        orders = list(
            self.db.execute(
                select(Order).where(
                    Order.show_id == show_id,
                    Order.account_id == self.account_id,
                    Order.deleted_at.is_(None),
                    Order.status == OrderStatus.PENDING,
                )
            ).scalars().all()
        )

        created: list[dict[str, Any]] = []
        skipped: list[dict[str, str]] = []

        for order in orders:
            # Check if shipment already exists
            existing = self.repo.get_by_order_id(order.id)
            if existing is not None:
                skipped.append({
                    "order_id": str(order.id),
                    "reason": "Shipment already exists.",
                })
                continue

            shipment = Shipment(
                account_id=self.account_id,
                order_id=order.id,
                carrier=data.get("carrier", ""),
                ship_by_date=data.get("ship_by_date"),
                buyer_name=order.buyer_username,
            )
            self.repo.create(shipment)

            log_audit(
                self.db,
                account_id=self.account_id,
                actor_id=actor_id,
                action="create",
                resource_type="shipments",
                resource_id=shipment.id,
                description=f"Bulk created from show {show_id}",
            )

            created.append(self._shipment_to_dict(shipment))

        self.db.commit()

        if created:
            self._publish_event("shipment.bulk_created", {
                "show_id": str(show_id),
                "account_id": str(self.account_id),
                "count": len(created),
            })

        return {
            "created": created,
            "skipped": skipped,
            "summary": {
                "created_count": len(created),
                "skipped_count": len(skipped),
            },
        }

    # ── Packing Lists ───────────────────────────────────────────────

    def generate_packing_list(self, show_id: uuid.UUID) -> dict[str, Any]:
        """Generate a structured packing list for a show, grouped by buyer."""
        # Validate show exists and belongs to this account
        show = self.db.execute(
            select(Show).where(
                Show.id == show_id,
                Show.account_id == self.account_id,
                Show.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

        if show is None:
            raise ShippingServiceError("Show not found.", "not_found", 404)

        # Get all non-cancelled, non-deleted orders for this show
        orders = list(
            self.db.execute(
                select(Order).where(
                    Order.show_id == show_id,
                    Order.account_id == self.account_id,
                    Order.deleted_at.is_(None),
                    Order.status != OrderStatus.CANCELLED,
                )
            ).scalars().all()
        )

        # Collect item IDs for bulk fetch
        item_ids = [o.inventory_item_id for o in orders]
        items_map: dict[uuid.UUID, InventoryItem] = {}
        if item_ids:
            items = list(
                self.db.execute(
                    select(InventoryItem).where(InventoryItem.id.in_(item_ids))
                ).scalars().all()
            )
            items_map = {item.id: item for item in items}

        # Collect shipment info per order
        order_ids = [o.id for o in orders]
        shipments_map: dict[uuid.UUID, Shipment] = {}
        if order_ids:
            shipments = list(
                self.db.execute(
                    select(Shipment).where(
                        Shipment.order_id.in_(order_ids),
                        Shipment.account_id == self.account_id,
                        Shipment.deleted_at.is_(None),
                    )
                ).scalars().all()
            )
            shipments_map = {s.order_id: s for s in shipments}

        # Group by buyer
        buyers: dict[str, dict[str, Any]] = {}
        for order in orders:
            buyer = order.buyer_username or "Unknown Buyer"
            if buyer not in buyers:
                buyers[buyer] = {
                    "buyer_username": buyer,
                    "items": [],
                    "total_items": 0,
                    "total_revenue": 0.0,
                    "address": None,
                }

            item = items_map.get(order.inventory_item_id)
            item_name = item.name if item else "Unknown Item"

            shipment = shipments_map.get(order.id)
            if shipment and not buyers[buyer]["address"]:
                buyers[buyer]["address"] = {
                    "buyer_name": shipment.buyer_name,
                    "address_line1": shipment.address_line1,
                    "address_line2": shipment.address_line2,
                    "city": shipment.city,
                    "state": shipment.state,
                    "zip_code": shipment.zip_code,
                    "country": shipment.country,
                }

            buyers[buyer]["items"].append({
                "order_id": str(order.id),
                "item_name": item_name,
                "sale_price": float(order.sale_price),
                "status": order.status,
                "shipment_status": shipment.status if shipment else None,
                "tracking_number": shipment.tracking_number if shipment else None,
            })
            buyers[buyer]["total_items"] += 1
            buyers[buyer]["total_revenue"] += float(order.sale_price)

        # Round revenue
        for buyer_data in buyers.values():
            buyer_data["total_revenue"] = round(buyer_data["total_revenue"], 2)

        buyer_list = list(buyers.values())

        return {
            "show": {
                "id": str(show.id),
                "title": show.title,
                "status": show.status,
            },
            "buyers": buyer_list,
            "summary": {
                "total_buyers": len(buyer_list),
                "total_items": sum(b["total_items"] for b in buyer_list),
                "total_revenue": round(sum(b["total_revenue"] for b in buyer_list), 2),
            },
        }

    # ── Overdue Shipments ───────────────────────────────────────────

    def list_overdue_shipments(self) -> list[dict[str, Any]]:
        """List shipments past their ship-by date that haven't shipped."""
        shipments = self.repo.list_overdue()
        return [self._shipment_to_dict(s) for s in shipments]

    # ── Helpers ─────────────────────────────────────────────────────

    def _update_order_status(self, order_id: uuid.UUID, status: str) -> None:
        """Update the linked order's status."""
        order = self.db.execute(
            select(Order).where(
                Order.id == order_id,
                Order.account_id == self.account_id,
                Order.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

        if order is not None:
            order.status = status
            order.updated_at = datetime.now(timezone.utc)

    def _shipment_to_dict(self, shipment: Shipment) -> dict[str, Any]:
        return {
            "id": str(shipment.id),
            "account_id": str(shipment.account_id),
            "order_id": str(shipment.order_id),
            "carrier": shipment.carrier,
            "tracking_number": shipment.tracking_number,
            "label_url": shipment.label_url,
            "ship_by_date": shipment.ship_by_date.isoformat() if shipment.ship_by_date else None,
            "shipped_at": shipment.shipped_at.isoformat() if shipment.shipped_at else None,
            "delivered_at": shipment.delivered_at.isoformat() if shipment.delivered_at else None,
            "weight_oz": float(shipment.weight_oz),
            "buyer_name": shipment.buyer_name,
            "address_line1": shipment.address_line1,
            "address_line2": shipment.address_line2,
            "city": shipment.city,
            "state": shipment.state,
            "zip_code": shipment.zip_code,
            "country": shipment.country,
            "status": shipment.status,
            "notes": shipment.notes,
            "created_at": shipment.created_at.isoformat(),
            "updated_at": shipment.updated_at.isoformat(),
            "deleted_at": shipment.deleted_at.isoformat() if shipment.deleted_at else None,
        }

    def _publish_event(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.event_publisher is not None:
            self.event_publisher.publish(event_type, payload, source_service="shipping")
