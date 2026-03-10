"""Whatnot service database models: WhatnotCredential, SyncLog, WebhookEvent."""

import uuid
from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid, JSON
from sqlalchemy.orm import Mapped, mapped_column

from services.shared.models import BaseModel


class SyncType(StrEnum):
    """Types of data sync operations."""

    PRODUCTS = "products"
    ORDERS = "orders"
    LIVESTREAMS = "livestreams"
    LISTINGS = "listings"
    FULL = "full"


class SyncStatus(StrEnum):
    """Sync operation status values."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class WebhookStatus(StrEnum):
    """Webhook event processing status."""

    RECEIVED = "received"
    PROCESSED = "processed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WhatnotCredential(BaseModel):
    """Encrypted OAuth credentials linking a WhatTools account to Whatnot."""

    __tablename__ = "whatnot_credentials"

    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id"), unique=True, index=True
    )
    whatnot_user_id: Mapped[str] = mapped_column(String(255), default="")
    whatnot_username: Mapped[str] = mapped_column(String(255), default="")
    encrypted_access_token: Mapped[str] = mapped_column(Text, default="")
    encrypted_refresh_token: Mapped[str] = mapped_column(Text, default="")
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    scopes: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, init=False
    )
    webhook_secret: Mapped[str] = mapped_column(String(255), default="")


class SyncLog(BaseModel):
    """Tracks sync operation history for audit and debugging."""

    __tablename__ = "sync_logs"

    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id"), index=True
    )
    sync_type: Mapped[str] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(String(20), default=SyncStatus.PENDING, index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=lambda: datetime.now(timezone.utc),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, init=False
    )
    items_synced: Mapped[int] = mapped_column(Integer, default=0, init=False)
    items_created: Mapped[int] = mapped_column(Integer, default=0, init=False)
    items_updated: Mapped[int] = mapped_column(Integer, default=0, init=False)
    items_failed: Mapped[int] = mapped_column(Integer, default=0, init=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, default=None, init=False)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None, init=False)


class WebhookEvent(BaseModel):
    """Stores incoming Whatnot webhook events for idempotent processing."""

    __tablename__ = "webhook_events"

    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id"), index=True
    )
    event_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    topic: Mapped[str] = mapped_column(String(100), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(
        String(20), default=WebhookStatus.RECEIVED, index=True
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None, init=False
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, init=False
    )
