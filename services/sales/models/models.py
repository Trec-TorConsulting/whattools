"""Sales service database models: Show, Order."""

import uuid
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from services.shared.models import BaseModel


class RecurrenceFrequency(StrEnum):
    """Recurrence frequency for repeating shows."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ShowStatus(StrEnum):
    """Show lifecycle status values."""

    PLANNED = "planned"
    LIVE = "live"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class OrderStatus(StrEnum):
    """Order lifecycle status values."""

    PENDING = "pending"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


# Valid show status transitions
SHOW_TRANSITIONS: dict[str, list[str]] = {
    ShowStatus.PLANNED: [ShowStatus.LIVE, ShowStatus.CANCELLED],
    ShowStatus.LIVE: [ShowStatus.COMPLETED, ShowStatus.CANCELLED],
    ShowStatus.COMPLETED: [],
    ShowStatus.CANCELLED: [],
}


class Show(BaseModel):
    """A live selling session on Whatnot or other platform."""

    __tablename__ = "shows"

    account_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("accounts.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    platform: Mapped[str] = mapped_column(String(50), default="whatnot")
    scheduled_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    scheduled_end_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    started_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    ended_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    status: Mapped[str] = mapped_column(String(20), default=ShowStatus.PLANNED, index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    recurrence_rule: Mapped[str | None] = mapped_column(String(20), nullable=True, default=None)
    recurrence_days: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)
    recurrence_weeks: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    recurrence_group_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, default=None, index=True)


class Order(BaseModel):
    """A single item sale within a show."""

    __tablename__ = "orders"

    account_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("accounts.id"), index=True)
    show_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("shows.id"), index=True)
    inventory_item_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("inventory_items.id"), index=True)
    sale_price: Mapped[float] = mapped_column(Numeric(12, 2))
    platform_fees: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    shipping_cost: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    cost_basis: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    profit: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    buyer_username: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(20), default=OrderStatus.PENDING, index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
