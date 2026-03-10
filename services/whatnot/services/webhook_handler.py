"""Webhook handler service — processes incoming Whatnot webhook events."""

import hashlib
import hmac
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.inventory.models.models import InventoryItem, ItemStatus
from services.shared.logging import get_logger
from services.whatnot.models import WhatnotCredential
from services.whatnot.repositories.whatnot_repository import WebhookEventRepository

logger = get_logger("whatnot.webhook_handler")


class WebhookServiceError(Exception):
    """Error during webhook processing."""

    def __init__(self, message: str, code: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class WebhookHandler:
    """Processes incoming Whatnot webhook events with HMAC validation and idempotency."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def validate_signature(
        self, payload_bytes: bytes, signature: str, seller_id: str
    ) -> uuid.UUID:
        """Validate the HMAC SHA256 signature of a webhook payload.

        Args:
            payload_bytes: Raw request body bytes.
            signature: Value of X-Whatnot-Webhook-Signature header.
            seller_id: Value of X-Whatnot-Seller-Id header.

        Returns:
            The account_id associated with the seller ID.

        Raises:
            WebhookServiceError: If signature validation fails.
        """
        # Look up credential by seller ID
        query = (
            select(WhatnotCredential)
            .where(WhatnotCredential.whatnot_user_id == seller_id)
            .where(WhatnotCredential.is_active.is_(True))
            .where(WhatnotCredential.deleted_at.is_(None))
        )
        credential = self.db.execute(query).scalar_one_or_none()
        if not credential:
            raise WebhookServiceError(
                "Unknown seller ID", "webhook_auth_failed", 401
            )

        # Compute expected signature
        expected = hmac.new(
            credential.webhook_secret.encode(),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected, signature):
            raise WebhookServiceError(
                "Invalid webhook signature", "webhook_auth_failed", 401
            )

        return credential.account_id

    def handle_event(
        self,
        account_id: uuid.UUID,
        event_id: str,
        topic: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Process a webhook event with idempotency check.

        Args:
            account_id: The WhatTools account this event belongs to.
            event_id: Unique event identifier for deduplication.
            topic: Webhook topic (e.g., 'product/sold').
            payload: Event payload data.

        Returns:
            Dict with processing result.
        """
        repo = WebhookEventRepository(self.db, account_id)

        # Idempotency check
        if repo.exists(event_id):
            logger.info("webhook_duplicate", event_id=event_id, topic=topic)
            return {"status": "skipped", "reason": "duplicate"}

        event = repo.create(event_id, topic, payload)

        try:
            result = self._dispatch_event(account_id, topic, payload)
            repo.mark_processed(event)
            self.db.commit()
            return {"status": "processed", "result": result}
        except Exception as exc:
            repo.mark_failed(event, str(exc)[:1000])
            self.db.commit()
            logger.error("webhook_processing_error", event_id=event_id, topic=topic, error=str(exc))
            return {"status": "failed", "error": str(exc)}

    def _dispatch_event(
        self,
        account_id: uuid.UUID,
        topic: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Route a webhook event to the appropriate handler.

        Args:
            account_id: The WhatTools account.
            topic: Webhook topic.
            payload: Event payload.

        Returns:
            Handler result dict.
        """
        handlers = {
            "product/sold": self._handle_product_sold,
            "bulk_operation/finished": self._handle_bulk_operation_finished,
            "listing/created": self._handle_listing_created,
            "listing/updated": self._handle_listing_updated,
        }

        handler = handlers.get(topic)
        if not handler:
            logger.warning("webhook_unknown_topic", topic=topic)
            return {"handled": False, "reason": f"Unknown topic: {topic}"}

        return handler(account_id, payload)

    def _handle_product_sold(
        self, account_id: uuid.UUID, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle product/sold webhook — decrement inventory quantity."""
        product_id = payload.get("product_id")
        quantity = payload.get("quantity", 1)

        if not product_id:
            return {"handled": False, "reason": "No product_id in payload"}

        query = (
            select(InventoryItem)
            .where(InventoryItem.account_id == account_id)
            .where(InventoryItem.whatnot_product_id == product_id)
            .where(InventoryItem.deleted_at.is_(None))
        )
        item = self.db.execute(query).scalar_one_or_none()
        if not item:
            logger.warning("webhook_product_not_found", product_id=product_id)
            return {"handled": False, "reason": "Product not found locally"}

        item.quantity = max(0, item.quantity - quantity)
        if item.quantity == 0:
            item.status = ItemStatus.SOLD
        item.updated_at = datetime.now(timezone.utc)
        self.db.flush()

        return {
            "handled": True,
            "item_id": str(item.id),
            "new_quantity": item.quantity,
        }

    def _handle_bulk_operation_finished(
        self, account_id: uuid.UUID, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle bulk_operation/finished webhook — log completion."""
        bulk_op_id = payload.get("id")
        status = payload.get("status")
        logger.info(
            "bulk_operation_finished",
            account_id=str(account_id),
            bulk_op_id=bulk_op_id,
            status=status,
        )
        return {"handled": True, "bulk_operation_id": bulk_op_id, "status": status}

    def _handle_listing_created(
        self, account_id: uuid.UUID, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle listing/created webhook — update local item listing ID."""
        product_id = payload.get("product_id")
        listing_id = payload.get("listing_id")

        if not product_id or not listing_id:
            return {"handled": False, "reason": "Missing product_id or listing_id"}

        query = (
            select(InventoryItem)
            .where(InventoryItem.account_id == account_id)
            .where(InventoryItem.whatnot_product_id == product_id)
            .where(InventoryItem.deleted_at.is_(None))
        )
        item = self.db.execute(query).scalar_one_or_none()
        if not item:
            return {"handled": False, "reason": "Product not found locally"}

        item.whatnot_listing_id = listing_id
        item.updated_at = datetime.now(timezone.utc)
        self.db.flush()

        return {"handled": True, "item_id": str(item.id), "listing_id": listing_id}

    def _handle_listing_updated(
        self, account_id: uuid.UUID, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle listing/updated webhook — same logic as listing/created."""
        return self._handle_listing_created(account_id, payload)
