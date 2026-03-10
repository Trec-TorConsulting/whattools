"""Tests for Whatnot models."""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from services.whatnot.models import (
    SyncLog,
    SyncStatus,
    SyncType,
    WebhookEvent,
    WebhookStatus,
    WhatnotCredential,
)


class TestWhatnotCredential:
    def test_create_credential(self, db_session: Session, sample_account):
        cred = WhatnotCredential(
            account_id=sample_account.id,
            whatnot_user_id="user_abc",
            whatnot_username="seller1",
            encrypted_access_token="enc_token",
            encrypted_refresh_token="enc_refresh",
            scopes="full_access",
            is_active=True,
            webhook_secret="secret",
        )
        db_session.add(cred)
        db_session.flush()

        assert cred.id is not None
        assert cred.whatnot_username == "seller1"
        assert cred.is_active is True

    def test_credential_has_uuid_pk(self, sample_credential):
        assert isinstance(sample_credential.id, uuid.UUID)

    def test_credential_timestamps(self, sample_credential):
        assert sample_credential.created_at is not None
        assert sample_credential.updated_at is not None


class TestSyncLog:
    def test_create_sync_log(self, db_session: Session, sample_account):
        log = SyncLog(
            account_id=sample_account.id,
            sync_type=SyncType.PRODUCTS,
            status=SyncStatus.RUNNING,
        )
        db_session.add(log)
        db_session.flush()

        assert log.id is not None
        assert log.sync_type == "products"
        assert log.status == "running"
        assert log.items_synced == 0

    def test_sync_type_enum_values(self):
        assert SyncType.PRODUCTS == "products"
        assert SyncType.ORDERS == "orders"
        assert SyncType.LIVESTREAMS == "livestreams"
        assert SyncType.FULL == "full"


class TestWebhookEvent:
    def test_create_webhook_event(self, db_session: Session, sample_account):
        event = WebhookEvent(
            account_id=sample_account.id,
            event_id="evt_unique_123",
            topic="product/sold",
            payload={"item_id": "abc"},
            status=WebhookStatus.RECEIVED,
        )
        db_session.add(event)
        db_session.flush()

        assert event.id is not None
        assert event.event_id == "evt_unique_123"
        assert event.status == "received"

    def test_webhook_status_values(self):
        assert WebhookStatus.RECEIVED == "received"
        assert WebhookStatus.PROCESSED == "processed"
        assert WebhookStatus.FAILED == "failed"
        assert WebhookStatus.SKIPPED == "skipped"
