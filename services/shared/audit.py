"""Audit trail model and helper for logging all mutations."""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, JSON
from sqlalchemy.orm import Mapped, Session, mapped_column

from services.shared.models import Base


class AuditLog(Base):
    """Immutable audit log entry for tracking mutations on resources."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("accounts.id"), index=True)
    actor_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    action: Mapped[str] = mapped_column(String(50))
    resource_type: Mapped[str] = mapped_column(String(100), index=True)
    resource_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    changes: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


def log_audit(
    db: Session,
    *,
    account_id: uuid.UUID,
    actor_id: uuid.UUID,
    action: str,
    resource_type: str,
    resource_id: uuid.UUID,
    changes: dict[str, Any] | None = None,
    description: str | None = None,
) -> AuditLog:
    """Create an audit log entry.

    Args:
        db: SQLAlchemy session.
        account_id: The account this action belongs to.
        actor_id: The user performing the action.
        action: Action type (create, update, delete, restore).
        resource_type: Type of resource (e.g., "inventory_item", "category").
        resource_id: ID of the affected resource.
        changes: JSON diff of old/new values for updates.
        description: Optional human-readable description.

    Returns:
        The created AuditLog entry.
    """
    entry = AuditLog(
        account_id=account_id,
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        changes=changes,
        description=description,
    )
    db.add(entry)
    return entry
