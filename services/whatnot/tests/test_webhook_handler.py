"""Tests for webhook handler."""

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from services.whatnot.services.webhook_handler import WebhookHandler, WebhookServiceError


class TestWebhookValidation:
    def test_validate_valid_signature(self, db_session, sample_account, sample_credential):
        handler = WebhookHandler(db_session)

        payload = b'{"event_id": "evt_1", "topic": "product/sold"}'
        secret = sample_credential.webhook_secret
        expected_sig = hmac.new(
            secret.encode(), payload, hashlib.sha256
        ).hexdigest()

        # seller_id is the whatnot_user_id on the credential
        account_id = handler.validate_signature(
            payload, expected_sig, sample_credential.whatnot_user_id
        )
        assert account_id == sample_account.id

    def test_validate_invalid_signature(self, db_session, sample_account, sample_credential):
        handler = WebhookHandler(db_session)

        payload = b'{"event_id": "evt_1"}'
        with pytest.raises(WebhookServiceError, match="Invalid webhook signature"):
            handler.validate_signature(
                payload, "invalid_sig", sample_credential.whatnot_user_id
            )

    def test_validate_no_credential(self, db_session, test_account_id):
        handler = WebhookHandler(db_session)
        with pytest.raises(WebhookServiceError, match="Unknown seller ID"):
            handler.validate_signature(b"{}", "any_sig", "nonexistent_seller")


class TestWebhookHandling:
    def test_handle_duplicate_event(self, db_session, sample_account, sample_credential):
        handler = WebhookHandler(db_session)

        # First call
        handler.handle_event(
            account_id=sample_account.id,
            event_id="evt_dup_1",
            topic="product/sold",
            payload={"product_id": "p1"},
        )
        db_session.flush()

        # Second call — should be idempotent (skipped)
        result = handler.handle_event(
            account_id=sample_account.id,
            event_id="evt_dup_1",
            topic="product/sold",
            payload={"product_id": "p1"},
        )
        assert result["status"] == "skipped"
        assert result["reason"] == "duplicate"

    def test_handle_unknown_topic(self, db_session, sample_account, sample_credential):
        handler = WebhookHandler(db_session)
        result = handler.handle_event(
            account_id=sample_account.id,
            event_id="evt_unknown_1",
            topic="unknown/event_type",
            payload={},
        )
        assert result["status"] == "processed"
        assert result["result"]["handled"] is False
        assert "Unknown topic" in result["result"]["reason"]

    def test_product_sold_no_product_id(self, db_session, sample_account):
        handler = WebhookHandler(db_session)
        result = handler.handle_event(
            account_id=sample_account.id,
            event_id="evt_no_pid",
            topic="product/sold",
            payload={},
        )
        assert result["status"] == "processed"
        assert result["result"]["handled"] is False

    def test_product_sold_not_found(self, db_session, sample_account):
        handler = WebhookHandler(db_session)
        result = handler.handle_event(
            account_id=sample_account.id,
            event_id="evt_notfound",
            topic="product/sold",
            payload={"product_id": "nonexistent"},
        )
        assert result["status"] == "processed"
        assert result["result"]["handled"] is False
        assert "not found" in result["result"]["reason"].lower()

    def test_product_sold_decrements_quantity(self, db_session, sample_account):
        from services.inventory.models.models import InventoryItem, ItemStatus

        inv = InventoryItem(
            account_id=sample_account.id, name="Card", status=ItemStatus.AVAILABLE,
            cogs=5.0, quantity=5,
        )
        inv.whatnot_product_id = "wn_sell_me"
        db_session.add(inv)
        db_session.flush()

        handler = WebhookHandler(db_session)
        result = handler.handle_event(
            account_id=sample_account.id,
            event_id="evt_sell_1",
            topic="product/sold",
            payload={"product_id": "wn_sell_me", "quantity": 2},
        )
        assert result["status"] == "processed"
        assert result["result"]["handled"] is True
        assert result["result"]["new_quantity"] == 3
        db_session.refresh(inv)
        assert inv.quantity == 3
        assert inv.status == ItemStatus.AVAILABLE

    def test_product_sold_marks_sold_at_zero(self, db_session, sample_account):
        from services.inventory.models.models import InventoryItem, ItemStatus

        inv = InventoryItem(
            account_id=sample_account.id, name="Last One", status=ItemStatus.AVAILABLE,
            cogs=5.0, quantity=1,
        )
        inv.whatnot_product_id = "wn_last"
        db_session.add(inv)
        db_session.flush()

        handler = WebhookHandler(db_session)
        result = handler.handle_event(
            account_id=sample_account.id,
            event_id="evt_sell_last",
            topic="product/sold",
            payload={"product_id": "wn_last", "quantity": 1},
        )
        assert result["result"]["new_quantity"] == 0
        db_session.refresh(inv)
        assert inv.status == ItemStatus.SOLD

    def test_listing_created_missing_fields(self, db_session, sample_account):
        handler = WebhookHandler(db_session)
        result = handler.handle_event(
            account_id=sample_account.id,
            event_id="evt_lc_no_fields",
            topic="listing/created",
            payload={"product_id": "p1"},  # missing listing_id
        )
        assert result["result"]["handled"] is False

    def test_listing_created_product_not_found(self, db_session, sample_account):
        handler = WebhookHandler(db_session)
        result = handler.handle_event(
            account_id=sample_account.id,
            event_id="evt_lc_nf",
            topic="listing/created",
            payload={"product_id": "missing", "listing_id": "lst_1"},
        )
        assert result["result"]["handled"] is False

    def test_listing_created_success(self, db_session, sample_account):
        from services.inventory.models.models import InventoryItem, ItemStatus

        inv = InventoryItem(
            account_id=sample_account.id, name="Item", status=ItemStatus.AVAILABLE,
            cogs=5.0, quantity=1,
        )
        inv.whatnot_product_id = "wn_lc_prod"
        db_session.add(inv)
        db_session.flush()

        handler = WebhookHandler(db_session)
        result = handler.handle_event(
            account_id=sample_account.id,
            event_id="evt_lc_ok",
            topic="listing/created",
            payload={"product_id": "wn_lc_prod", "listing_id": "lst_new"},
        )
        assert result["result"]["handled"] is True
        assert result["result"]["listing_id"] == "lst_new"
        db_session.refresh(inv)
        assert inv.whatnot_listing_id == "lst_new"

    def test_listing_updated_delegates(self, db_session, sample_account):
        from services.inventory.models.models import InventoryItem, ItemStatus

        inv = InventoryItem(
            account_id=sample_account.id, name="Item", status=ItemStatus.AVAILABLE,
            cogs=5.0, quantity=1,
        )
        inv.whatnot_product_id = "wn_lu_prod"
        db_session.add(inv)
        db_session.flush()

        handler = WebhookHandler(db_session)
        result = handler.handle_event(
            account_id=sample_account.id,
            event_id="evt_lu_ok",
            topic="listing/updated",
            payload={"product_id": "wn_lu_prod", "listing_id": "lst_updated"},
        )
        assert result["result"]["handled"] is True

    def test_bulk_operation_finished(self, db_session, sample_account):
        handler = WebhookHandler(db_session)
        result = handler.handle_event(
            account_id=sample_account.id,
            event_id="evt_bulk_1",
            topic="bulk_operation/finished",
            payload={"id": "bulk_123", "status": "completed"},
        )
        assert result["result"]["handled"] is True
        assert result["result"]["bulk_operation_id"] == "bulk_123"
