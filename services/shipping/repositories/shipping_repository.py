"""Shipping repository — Shipment CRUD, account-scoped, soft-delete-aware."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from services.shipping.models.models import Shipment


@dataclass
class PaginatedResult:
    """Result of a paginated query."""

    items: list[Any]
    total_count: int
    next_cursor: str | None


class ShipmentRepository:
    """Data access for Shipment records, account-scoped with soft-delete awareness."""

    def __init__(self, db: Session, account_id: uuid.UUID) -> None:
        self.db = db
        self.account_id = account_id

    def _base_query(self) -> Select[tuple[Shipment]]:
        return select(Shipment).where(
            Shipment.account_id == self.account_id,
            Shipment.deleted_at.is_(None),
        )

    def get_by_id(self, shipment_id: uuid.UUID) -> Shipment | None:
        return self.db.execute(
            self._base_query().where(Shipment.id == shipment_id)
        ).scalar_one_or_none()

    def get_by_order_id(self, order_id: uuid.UUID) -> Shipment | None:
        """Find an active (non-deleted, non-cancelled) shipment for an order."""
        return self.db.execute(
            self._base_query().where(
                Shipment.order_id == order_id,
                Shipment.status != "cancelled",
            )
        ).scalar_one_or_none()

    def list_shipments(
        self,
        *,
        cursor: str | None = None,
        limit: int = 50,
        status: str | None = None,
        order_id: uuid.UUID | None = None,
    ) -> PaginatedResult:
        """List shipments with cursor-based pagination and optional filters."""
        limit = min(limit, 100)
        query = self._base_query()

        if status:
            query = query.where(Shipment.status == status)
        if order_id:
            query = query.where(Shipment.order_id == order_id)

        count_query = select(func.count()).select_from(query.subquery())
        total_count: int = self.db.execute(count_query).scalar_one()

        if cursor:
            query = query.where(Shipment.id > uuid.UUID(cursor))

        query = query.order_by(Shipment.id).limit(limit + 1)
        results = list(self.db.execute(query).scalars().all())

        next_cursor: str | None = None
        if len(results) > limit:
            results = results[:limit]
            next_cursor = str(results[-1].id)

        return PaginatedResult(items=results, total_count=total_count, next_cursor=next_cursor)

    def list_overdue(self) -> list[Shipment]:
        """List shipments past their ship-by date that haven't shipped/delivered/cancelled."""
        now = datetime.now(timezone.utc)
        query = (
            self._base_query()
            .where(
                Shipment.ship_by_date.is_not(None),
                Shipment.ship_by_date < now,
                Shipment.status.in_(["pending", "label_created"]),
            )
            .order_by(Shipment.ship_by_date)
        )
        return list(self.db.execute(query).scalars().all())

    def list_deleted(self) -> list[Shipment]:
        """List soft-deleted shipments within 30-day retention."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        query = (
            select(Shipment)
            .where(
                Shipment.account_id == self.account_id,
                Shipment.deleted_at.is_not(None),
                Shipment.deleted_at > cutoff,
            )
            .order_by(Shipment.deleted_at.desc())
        )
        return list(self.db.execute(query).scalars().all())

    def create(self, shipment: Shipment) -> Shipment:
        self.db.add(shipment)
        self.db.flush()
        return shipment

    def save(self) -> None:
        self.db.flush()

    @staticmethod
    def purge_expired(db: Session) -> int:
        """Permanently delete shipments soft-deleted more than 30 days ago."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        result = db.execute(
            select(Shipment).where(
                Shipment.deleted_at.is_not(None),
                Shipment.deleted_at < cutoff,
            )
        )
        shipments = list(result.scalars().all())
        count = len(shipments)
        for shipment in shipments:
            db.delete(shipment)
        db.flush()
        return count
