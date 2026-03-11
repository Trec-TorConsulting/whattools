"""Admin audit log model — separate table for platform admin actions."""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, JSON
from sqlalchemy.orm import Mapped, Session, mapped_column

from services.shared.models import Base


class AdminAuditLog(Base):
    """Immutable audit log entry for platform admin actions."""

    __tablename__ = "admin_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    admin_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(100))
    target_type: Mapped[str] = mapped_column(String(100), index=True)
    target_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    changes: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


def log_admin_audit(
    db: Session,
    *,
    admin_id: uuid.UUID,
    action: str,
    target_type: str,
    target_id: uuid.UUID | None = None,
    changes: dict[str, Any] | None = None,
    description: str | None = None,
    ip_address: str | None = None,
) -> AdminAuditLog:
    """Create an admin audit log entry."""
    entry = AdminAuditLog(
        admin_id=admin_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        changes=changes,
        description=description,
        ip_address=ip_address,
    )
    db.add(entry)
    return entry
