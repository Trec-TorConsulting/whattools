"""Shipping service database models: Shipment."""

import uuid
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from services.shared.models import BaseModel


class ShipmentStatus(StrEnum):
    """Shipment lifecycle status values."""

    PENDING = "pending"
    LABEL_CREATED = "label_created"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


# Valid shipment status transitions
SHIPMENT_TRANSITIONS: dict[str, list[str]] = {
    ShipmentStatus.PENDING: [ShipmentStatus.LABEL_CREATED, ShipmentStatus.CANCELLED],
    ShipmentStatus.LABEL_CREATED: [ShipmentStatus.SHIPPED, ShipmentStatus.CANCELLED],
    ShipmentStatus.SHIPPED: [ShipmentStatus.DELIVERED],
    ShipmentStatus.DELIVERED: [],
    ShipmentStatus.CANCELLED: [],
}


class Shipment(BaseModel):
    """A shipment linked to a single order."""

    __tablename__ = "shipments"

    account_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("accounts.id"), index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("orders.id"), unique=True, index=True)
    carrier: Mapped[str] = mapped_column(String(100), default="")
    tracking_number: Mapped[str] = mapped_column(String(255), default="")
    label_url: Mapped[str] = mapped_column(String(1024), default="")
    ship_by_date: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    shipped_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    delivered_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    weight_oz: Mapped[float] = mapped_column(Numeric(8, 2), default=0.0)
    buyer_name: Mapped[str] = mapped_column(String(255), default="")
    address_line1: Mapped[str] = mapped_column(String(255), default="")
    address_line2: Mapped[str] = mapped_column(String(255), default="")
    city: Mapped[str] = mapped_column(String(100), default="")
    state: Mapped[str] = mapped_column(String(50), default="")
    zip_code: Mapped[str] = mapped_column(String(20), default="")
    country: Mapped[str] = mapped_column(String(50), default="US")
    status: Mapped[str] = mapped_column(String(20), default=ShipmentStatus.PENDING, index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
