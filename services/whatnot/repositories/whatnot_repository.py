"""Repositories for Whatnot service models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.whatnot.models import SyncLog, SyncStatus, WebhookEvent, WebhookStatus, WhatnotCredential


class WhatnotCredentialRepository:
    """Repository for WhatnotCredential model."""

    def __init__(self, db: Session, account_id: uuid.UUID) -> None:
        self.db = db
        self.account_id = account_id

    def get_credential(self) -> WhatnotCredential | None:
        """Get the Whatnot credential for this account."""
        query = (
            select(WhatnotCredential)
            .where(WhatnotCredential.account_id == self.account_id)
            .where(WhatnotCredential.deleted_at.is_(None))
        )
        return self.db.execute(query).scalar_one_or_none()

    def get_active_credential(self) -> WhatnotCredential | None:
        """Get the active Whatnot credential for this account."""
        query = (
            select(WhatnotCredential)
            .where(WhatnotCredential.account_id == self.account_id)
            .where(WhatnotCredential.is_active.is_(True))
            .where(WhatnotCredential.deleted_at.is_(None))
        )
        return self.db.execute(query).scalar_one_or_none()


class SyncLogRepository:
    """Repository for SyncLog model."""

    def __init__(self, db: Session, account_id: uuid.UUID) -> None:
        self.db = db
        self.account_id = account_id

    def create(self, sync_type: str) -> SyncLog:
        """Create a new sync log entry."""
        log = SyncLog(
            account_id=self.account_id,
            sync_type=sync_type,
            status=SyncStatus.PENDING,
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(log)
        self.db.flush()
        return log

    def complete(
        self,
        log: SyncLog,
        *,
        items_synced: int = 0,
        items_created: int = 0,
        items_updated: int = 0,
        items_failed: int = 0,
        details: dict | None = None,
    ) -> SyncLog:
        """Mark a sync log as completed."""
        log.status = SyncStatus.COMPLETED
        log.completed_at = datetime.now(timezone.utc)
        log.items_synced = items_synced
        log.items_created = items_created
        log.items_updated = items_updated
        log.items_failed = items_failed
        log.details = details
        self.db.flush()
        return log

    def fail(self, log: SyncLog, error_message: str) -> SyncLog:
        """Mark a sync log as failed."""
        log.status = SyncStatus.FAILED
        log.completed_at = datetime.now(timezone.utc)
        log.error_message = error_message
        self.db.flush()
        return log

    def get_latest(self, sync_type: str | None = None, *, limit: int = 20) -> list[SyncLog]:
        """Get recent sync logs, optionally filtered by type."""
        query = (
            select(SyncLog)
            .where(SyncLog.account_id == self.account_id)
            .where(SyncLog.deleted_at.is_(None))
        )
        if sync_type:
            query = query.where(SyncLog.sync_type == sync_type)
        query = query.order_by(SyncLog.started_at.desc()).limit(limit)
        return list(self.db.execute(query).scalars().all())

    def get_last_successful(self, sync_type: str) -> SyncLog | None:
        """Get the most recent successful sync log for a given type."""
        query = (
            select(SyncLog)
            .where(SyncLog.account_id == self.account_id)
            .where(SyncLog.sync_type == sync_type)
            .where(SyncLog.status == SyncStatus.COMPLETED)
            .where(SyncLog.deleted_at.is_(None))
            .order_by(SyncLog.started_at.desc())
            .limit(1)
        )
        return self.db.execute(query).scalar_one_or_none()


class WebhookEventRepository:
    """Repository for WebhookEvent model."""

    def __init__(self, db: Session, account_id: uuid.UUID) -> None:
        self.db = db
        self.account_id = account_id

    def exists(self, event_id: str) -> bool:
        """Check if a webhook event has already been received (for idempotency)."""
        query = select(WebhookEvent).where(WebhookEvent.event_id == event_id)
        return self.db.execute(query).scalar_one_or_none() is not None

    def create(self, event_id: str, topic: str, payload: dict) -> WebhookEvent:
        """Store a new webhook event."""
        event = WebhookEvent(
            account_id=self.account_id,
            event_id=event_id,
            topic=topic,
            payload=payload,
        )
        self.db.add(event)
        self.db.flush()
        return event

    def mark_processed(self, event: WebhookEvent) -> WebhookEvent:
        """Mark a webhook event as successfully processed."""
        event.status = WebhookStatus.PROCESSED
        event.processed_at = datetime.now(timezone.utc)
        self.db.flush()
        return event

    def mark_failed(self, event: WebhookEvent, error_message: str) -> WebhookEvent:
        """Mark a webhook event as failed."""
        event.status = WebhookStatus.FAILED
        event.error_message = error_message
        event.processed_at = datetime.now(timezone.utc)
        self.db.flush()
        return event

    def mark_skipped(self, event: WebhookEvent) -> WebhookEvent:
        """Mark a webhook event as skipped (duplicate)."""
        event.status = WebhookStatus.SKIPPED
        event.processed_at = datetime.now(timezone.utc)
        self.db.flush()
        return event
