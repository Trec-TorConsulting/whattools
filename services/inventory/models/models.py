"""Inventory service database models: InventoryItem, Category, CSVImportJob."""

import uuid
from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, Uuid, JSON
from sqlalchemy.orm import Mapped, mapped_column

from services.shared.models import BaseModel


class ItemStatus(StrEnum):
    """Inventory item status values."""

    AVAILABLE = "available"
    SOLD = "sold"
    RESERVED = "reserved"
    LISTED = "listed"


class ImportJobStatus(StrEnum):
    """CSV import job status values."""

    PENDING_MAPPING = "pending_mapping"
    PROCESSING = "processing"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"


class Category(BaseModel):
    """Item category, scoped to an account."""

    __tablename__ = "categories"

    account_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("accounts.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")


class InventoryItem(BaseModel):
    """Inventory item belonging to an account, optionally categorized."""

    __tablename__ = "inventory_items"

    account_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("accounts.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("categories.id"), nullable=True, default=None, index=True
    )
    cogs: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default=ItemStatus.AVAILABLE, index=True)

    # Whatnot integration
    whatnot_product_id: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None, index=True, init=False)
    whatnot_variant_id: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None, init=False)
    whatnot_listing_id: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None, init=False)
    image_urls: Mapped[list | None] = mapped_column(JSON, nullable=True, default=None, init=False)


class CSVImportJob(BaseModel):
    """Tracks a CSV file import job from upload through processing."""

    __tablename__ = "csv_import_jobs"

    account_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("accounts.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    filename: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(30), default=ImportJobStatus.PENDING_MAPPING)

    # Detected headers and preview rows from the upload
    headers: Mapped[list | None] = mapped_column(JSON, nullable=True, default=None, init=False)
    preview_rows: Mapped[list | None] = mapped_column(JSON, nullable=True, default=None, init=False)

    # User-submitted column mapping: {"source_col": "whattools_field"}
    column_mapping: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None, init=False)

    # Results
    total_rows: Mapped[int] = mapped_column(Integer, default=0, init=False)
    success_count: Mapped[int] = mapped_column(Integer, default=0, init=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, init=False)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0, init=False)
    row_errors: Mapped[list | None] = mapped_column(JSON, nullable=True, default=None, init=False)
