"""Tests for Whatnot repositories."""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from services.whatnot.models import SyncLog, SyncStatus, SyncType, WebhookEvent, WebhookStatus
from services.whatnot.repositories.whatnot_repository import (
    SyncLogRepository,
    WebhookEventRepository,
    WhatnotCredentialRepository,
)


class TestWhatnotCredentialRepository:
    def test_get_credential(self, db_session, sample_account, sample_credential):
        repo = WhatnotCredentialRepository(db_session, sample_account.id)
        cred = repo.get_credential()
        assert cred is not None
        assert cred.whatnot_username == "testuser"

    def test_get_credential_not_found(self, db_session, test_account_id):
        repo = WhatnotCredentialRepository(db_session, test_account_id)
        cred = repo.get_credential()
        assert cred is None

    def test_get_active_credential(self, db_session, sample_account, sample_credential):
        repo = WhatnotCredentialRepository(db_session, sample_account.id)
        cred = repo.get_active_credential()
        assert cred is not None
        assert cred.is_active is True


class TestSyncLogRepository:
    def test_create_sync_log(self, db_session, sample_account):
        repo = SyncLogRepository(db_session, sample_account.id)
        log = repo.create(SyncType.PRODUCTS)
        assert log.id is not None
        assert log.sync_type == "products"
        assert log.status == "pending"

    def test_complete_sync_log(self, db_session, sample_account):
        repo = SyncLogRepository(db_session, sample_account.id)
        log = repo.create(SyncType.ORDERS)
        repo.complete(log, items_synced=10, items_created=5, items_updated=3, items_failed=2)
        assert log.status == "completed"
        assert log.items_synced == 10
        assert log.items_created == 5
        assert log.completed_at is not None

    def test_fail_sync_log(self, db_session, sample_account):
        repo = SyncLogRepository(db_session, sample_account.id)
        log = repo.create(SyncType.PRODUCTS)
        repo.fail(log, "Connection timeout")
        assert log.status == "failed"
        assert log.error_message == "Connection timeout"

    def test_get_latest(self, db_session, sample_account):
        repo = SyncLogRepository(db_session, sample_account.id)
        log = repo.create(SyncType.PRODUCTS)
        repo.complete(log, items_synced=5, items_created=5, items_updated=0, items_failed=0)

        latest = repo.get_latest(SyncType.PRODUCTS)
        assert isinstance(latest, list)
        assert len(latest) >= 1
        assert latest[0].sync_type == "products"


class TestWebhookEventRepository:
    def test_create_and_check_exists(self, db_session, sample_account):
        repo = WebhookEventRepository(db_session, sample_account.id)
        assert repo.exists("evt_123") is False

        repo.create("evt_123", "product/sold", {"item_id": "abc"})
        db_session.flush()
        assert repo.exists("evt_123") is True

    def test_mark_processed(self, db_session, sample_account):
        repo = WebhookEventRepository(db_session, sample_account.id)
        event = repo.create("evt_456", "product/sold", {})
        db_session.flush()

        repo.mark_processed(event)
        assert event.status == "processed"
        assert event.processed_at is not None

    def test_mark_failed(self, db_session, sample_account):
        repo = WebhookEventRepository(db_session, sample_account.id)
        event = repo.create("evt_789", "order/created", {})
        db_session.flush()

        repo.mark_failed(event, "Handler error")
        assert event.status == "failed"
        assert event.error_message == "Handler error"

    def test_mark_skipped(self, db_session, sample_account):
        repo = WebhookEventRepository(db_session, sample_account.id)
        event = repo.create("evt_skipped", "unknown/event", {})
        db_session.flush()

        repo.mark_skipped(event)
        assert event.status == "skipped"
