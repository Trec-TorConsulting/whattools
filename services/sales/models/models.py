"""Sales service database models: Show, Order."""

import uuid
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from services.shared.models import BaseModel


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
    started_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    ended_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    status: Mapped[str] = mapped_column(String(20), default=ShowStatus.PLANNED, index=True)
    notes: Mapped[str] = mapped_column(Text, default="")


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
