"""ExportJob model for tracking async report generation."""

import uuid
from datetime import datetime, timedelta, timezone
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from services.shared.models import BaseModel


class ExportStatus(StrEnum):
    """Export job lifecycle status values."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExportFormat(StrEnum):
    """Supported export file formats."""

    CSV = "csv"
    PDF = "pdf"


VALID_REPORT_TYPES = {"summary", "categories", "shows", "trends", "top_items", "full"}
VALID_FORMATS = {f.value for f in ExportFormat}


class ExportJob(BaseModel):
    """Tracks an async report export job."""

    __tablename__ = "export_jobs"

    account_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("accounts.id"), index=True)
    report_type: Mapped[str] = mapped_column(String(20))
    format: Mapped[str] = mapped_column(String(10))
    period: Mapped[str] = mapped_column(String(10), default="30d")
    status: Mapped[str] = mapped_column(String(20), default=ExportStatus.PENDING)
    file_path: Mapped[str] = mapped_column(String(1024), default="")
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str] = mapped_column(Text, default="")
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
