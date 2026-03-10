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
        # Should handle gracefully (skip or log)
        assert result is not None
