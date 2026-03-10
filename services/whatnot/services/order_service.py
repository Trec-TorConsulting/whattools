"""Order sync service — pull orders from Whatnot, push tracking codes, cancel orders."""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.inventory.models.models import InventoryItem, ItemStatus
from services.sales.models.models import Order, OrderStatus, Show
from services.shared.logging import get_logger
from services.whatnot.graphql.client import WhatnotClient, WhatnotApiError, WhatnotUserError
from services.whatnot.graphql.queries import ORDERS_QUERY, ORDER_QUERY
from services.whatnot.graphql.mutations import ADD_TRACKING_CODE_MUTATION, ORDER_CANCEL_MUTATION
from services.whatnot.models import SyncType
from services.whatnot.repositories.whatnot_repository import SyncLogRepository

logger = get_logger("whatnot.order_service")


class OrderServiceError(Exception):
    """Error during order sync operations."""

    def __init__(self, message: str, code: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class OrderSyncService:
    """Syncs orders between Whatnot and WhatTools."""

    def __init__(self, db: Session, account_id: uuid.UUID, client: WhatnotClient) -> None:
        self.db = db
        self.account_id = account_id
        self.client = client
        self.sync_log_repo = SyncLogRepository(db, account_id)

    def pull_orders(self) -> dict[str, Any]:
        """Pull orders from Whatnot and upsert into local database.

        Returns:
            Dict with sync stats.
        """
        sync_log = self.sync_log_repo.create(SyncType.ORDERS)
        sync_log.status = "running"
        self.db.flush()

        created = 0
        updated = 0
        failed = 0
        cursor = None

        try:
            while True:
                variables: dict[str, Any] = {"first": 50}
                if cursor:
                    variables["after"] = cursor

                data = self.client.execute(ORDERS_QUERY, variables)
                orders_conn = data.get("orders", {})
                edges = orders_conn.get("edges", [])

                for edge in edges:
                    node = edge.get("node", {})
                    try:
                        was_created = self._upsert_order(node)
                        if was_created:
                            created += 1
                        else:
                            updated += 1
                    except Exception as exc:
                        logger.warning("order_pull_item_error", whatnot_id=node.get("id"), error=str(exc))
                        failed += 1

                page_info = orders_conn.get("pageInfo", {})
                if not page_info.get("hasNextPage"):
                    break
                cursor = page_info.get("endCursor")

            self.db.commit()
            self.sync_log_repo.complete(
                sync_log,
                items_synced=created + updated,
                items_created=created,
                items_updated=updated,
                items_failed=failed,
            )
            self.db.commit()

        except (WhatnotApiError, WhatnotUserError) as exc:
            self.db.rollback()
            self.sync_log_repo.fail(sync_log, str(exc))
            self.db.commit()
            raise OrderServiceError(str(exc), "sync_error", 502) from exc

        return {
            "synced": created + updated,
            "created": created,
            "updated": updated,
            "failed": failed,
        }

    def _upsert_order(self, whatnot_order: dict[str, Any]) -> bool:
        """Create or update a local order from Whatnot order data.

        Returns:
            True if created, False if updated.
        """
        whatnot_order_id = whatnot_order["id"]
        status = whatnot_order.get("status", "PENDING")

        # Map Whatnot status to local status
        status_map = {
            "PENDING": OrderStatus.PENDING,
            "CREATED": OrderStatus.PENDING,
            "PROCESSING": OrderStatus.PENDING,
            "COMPLETED": OrderStatus.DELIVERED,
            "CANCELLED": OrderStatus.CANCELLED,
            "FAILED": OrderStatus.CANCELLED,
        }
        local_status = status_map.get(status, OrderStatus.PENDING)

        # Extract pricing (amounts are in cents)
        total = whatnot_order.get("total", {})
        sale_price = (total.get("amount", 0) or 0) / 100.0
        shipping_price = (whatnot_order.get("shippingPrice", {}).get("amount", 0) or 0) / 100.0

        # Customer info
        customer = whatnot_order.get("customer", {}) or {}
        buyer_username = customer.get("username", "")

        # Sales channel
        sales_channel = whatnot_order.get("salesChannel", {}) or {}
        channel_type = sales_channel.get("type", "")
        is_giveaway = whatnot_order.get("isGiveaway", False)

        # Check for existing order
        query = (
            select(Order)
            .where(Order.account_id == self.account_id)
            .where(Order.whatnot_order_id == whatnot_order_id)
            .where(Order.deleted_at.is_(None))
        )
        existing = self.db.execute(query).scalar_one_or_none()

        if existing:
            existing.status = local_status
            existing.buyer_username = buyer_username
            existing.updated_at = datetime.now(timezone.utc)
            self.db.flush()
            return False

        # Find or create a default show for these orders
        show = self._get_or_create_default_show()

        # Find linked inventory item if possible
        items = _extract_edges(whatnot_order.get("items", {}))
        inventory_item_id = None
        if items:
            first_item = items[0]
            product = first_item.get("product", {}) or {}
            whatnot_product_id = product.get("id")
            if whatnot_product_id:
                inv_query = (
                    select(InventoryItem)
                    .where(InventoryItem.account_id == self.account_id)
                    .where(InventoryItem.whatnot_product_id == whatnot_product_id)
                    .where(InventoryItem.deleted_at.is_(None))
                )
                inv_item = self.db.execute(inv_query).scalar_one_or_none()
                if inv_item:
                    inventory_item_id = inv_item.id
                    # Mark as sold if order is not cancelled
                    if local_status != OrderStatus.CANCELLED:
                        inv_item.status = ItemStatus.SOLD
                        inv_item.updated_at = datetime.now(timezone.utc)

        # If no linked inventory item found, create a placeholder
        if not inventory_item_id:
            placeholder = InventoryItem(
                account_id=self.account_id,
                name=f"Whatnot Order Item ({whatnot_order_id[:8]})",
                status=ItemStatus.SOLD,
                cogs=0.0,
                quantity=1,
            )
            placeholder.whatnot_product_id = items[0].get("product", {}).get("id") if items else None
            self.db.add(placeholder)
            self.db.flush()
            inventory_item_id = placeholder.id

        order = Order(
            account_id=self.account_id,
            show_id=show.id,
            inventory_item_id=inventory_item_id,
            sale_price=sale_price,
            shipping_cost=shipping_price,
            buyer_username=buyer_username,
            status=local_status,
        )
        order.whatnot_order_id = whatnot_order_id
        order.whatnot_customer_id = customer.get("id", "")
        order.sales_channel = channel_type
        order.is_giveaway = is_giveaway
        self.db.add(order)
        self.db.flush()
        return True

    def _get_or_create_default_show(self) -> Show:
        """Get or create a default show for Whatnot-synced orders."""
        query = (
            select(Show)
            .where(Show.account_id == self.account_id)
            .where(Show.title == "Whatnot Orders (Auto)")
            .where(Show.deleted_at.is_(None))
        )
        show = self.db.execute(query).scalar_one_or_none()
        if show:
            return show

        show = Show(
            account_id=self.account_id,
            title="Whatnot Orders (Auto)",
            platform="whatnot",
        )
        self.db.add(show)
        self.db.flush()
        return show

    def push_tracking(
        self,
        order_id: uuid.UUID,
        tracking_company: str,
        tracking_number: str,
    ) -> dict[str, Any]:
        """Push a tracking code for an order to Whatnot.

        Args:
            order_id: Local order ID.
            tracking_company: Carrier name (USPS, UPS, FEDEX).
            tracking_number: The tracking number.

        Returns:
            Dict with updated order info.
        """
        valid_carriers = {"USPS", "UPS", "FEDEX"}
        if tracking_company.upper() not in valid_carriers:
            raise OrderServiceError(
                f"Invalid carrier. Must be one of: {', '.join(sorted(valid_carriers))}",
                "validation_error",
                422,
            )

        query = (
            select(Order)
            .where(Order.id == order_id)
            .where(Order.account_id == self.account_id)
            .where(Order.deleted_at.is_(None))
        )
        order = self.db.execute(query).scalar_one_or_none()
        if not order:
            raise OrderServiceError("Order not found", "not_found", 404)

        if not order.whatnot_order_id:
            raise OrderServiceError(
                "Order not linked to Whatnot", "not_linked", 400
            )

        try:
            result = self.client.execute_mutation(
                ADD_TRACKING_CODE_MUTATION,
                {
                    "input": {
                        "orderId": order.whatnot_order_id,
                        "trackingCompany": tracking_company.upper(),
                        "trackingNumber": tracking_number,
                    }
                },
                mutation_name="addTrackingCode",
            )
        except WhatnotUserError as exc:
            raise OrderServiceError(exc.message, "whatnot_error", 422) from exc
        except WhatnotApiError as exc:
            raise OrderServiceError(str(exc), "whatnot_error", 502) from exc

        order.status = OrderStatus.SHIPPED
        order.updated_at = datetime.now(timezone.utc)
        self.db.commit()

        return {
            "order_id": str(order.id),
            "whatnot_order_id": order.whatnot_order_id,
            "tracking_company": tracking_company.upper(),
            "tracking_number": tracking_number,
        }

    def cancel_order(self, order_id: uuid.UUID) -> dict[str, Any]:
        """Cancel an order on Whatnot.

        Args:
            order_id: Local order ID.

        Returns:
            Dict with cancelled order info.
        """
        query = (
            select(Order)
            .where(Order.id == order_id)
            .where(Order.account_id == self.account_id)
            .where(Order.deleted_at.is_(None))
        )
        order = self.db.execute(query).scalar_one_or_none()
        if not order:
            raise OrderServiceError("Order not found", "not_found", 404)

        if not order.whatnot_order_id:
            raise OrderServiceError(
                "Order not linked to Whatnot", "not_linked", 400
            )

        try:
            self.client.execute_mutation(
                ORDER_CANCEL_MUTATION,
                {"input": {"orderId": order.whatnot_order_id}},
                mutation_name="orderCancel",
            )
        except WhatnotUserError as exc:
            raise OrderServiceError(exc.message, "whatnot_error", 422) from exc
        except WhatnotApiError as exc:
            raise OrderServiceError(str(exc), "whatnot_error", 502) from exc

        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.now(timezone.utc)
        self.db.commit()

        return {
            "order_id": str(order.id),
            "whatnot_order_id": order.whatnot_order_id,
            "status": "cancelled",
        }


def _extract_edges(connection: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract node data from a GraphQL connection/edges structure."""
    edges = connection.get("edges", [])
    return [edge.get("node", {}) for edge in edges]
