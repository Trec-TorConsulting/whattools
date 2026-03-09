"""Sales repositories — Show and Order CRUD, account-scoped, soft-delete-aware."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from services.sales.models.models import Order, Show


@dataclass
class PaginatedResult:
    """Result of a paginated query."""

    items: list[Any]
    total_count: int
    next_cursor: str | None


class ShowRepository:
    """Data access for Show records, account-scoped with soft-delete awareness."""

    def __init__(self, db: Session, account_id: uuid.UUID) -> None:
        self.db = db
        self.account_id = account_id

    def _base_query(self) -> Select[tuple[Show]]:
        return select(Show).where(
            Show.account_id == self.account_id,
            Show.deleted_at.is_(None),
        )

    def get_by_id(self, show_id: uuid.UUID) -> Show | None:
        return self.db.execute(
            self._base_query().where(Show.id == show_id)
        ).scalar_one_or_none()

    def list_shows(
        self,
        *,
        cursor: str | None = None,
        limit: int = 50,
        status: str | None = None,
    ) -> PaginatedResult:
        """List shows with cursor-based pagination and optional status filter."""
        limit = min(limit, 100)
        query = self._base_query()

        if status:
            query = query.where(Show.status == status)

        count_query = select(func.count()).select_from(query.subquery())
        total_count: int = self.db.execute(count_query).scalar_one()

        if cursor:
            query = query.where(Show.id > uuid.UUID(cursor))

        query = query.order_by(Show.id).limit(limit + 1)
        results = list(self.db.execute(query).scalars().all())

        next_cursor: str | None = None
        if len(results) > limit:
            results = results[:limit]
            next_cursor = str(results[-1].id)

        return PaginatedResult(items=results, total_count=total_count, next_cursor=next_cursor)

    def create(self, show: Show) -> Show:
        self.db.add(show)
        self.db.flush()
        return show

    def save(self) -> None:
        self.db.flush()

    @staticmethod
    def purge_expired(db: Session) -> int:
        """Permanently delete shows soft-deleted more than 30 days ago."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        result = db.execute(
            select(Show).where(
                Show.deleted_at.is_not(None),
                Show.deleted_at < cutoff,
            )
        )
        shows = list(result.scalars().all())
        count = len(shows)
        for show in shows:
            db.delete(show)
        db.flush()
        return count


class OrderRepository:
    """Data access for Order records, account-scoped with soft-delete awareness."""

    def __init__(self, db: Session, account_id: uuid.UUID) -> None:
        self.db = db
        self.account_id = account_id

    def _base_query(self) -> Select[tuple[Order]]:
        return select(Order).where(
            Order.account_id == self.account_id,
            Order.deleted_at.is_(None),
        )

    def get_by_id(self, order_id: uuid.UUID) -> Order | None:
        return self.db.execute(
            self._base_query().where(Order.id == order_id)
        ).scalar_one_or_none()

    def list_orders(
        self,
        *,
        cursor: str | None = None,
        limit: int = 50,
        show_id: uuid.UUID | None = None,
        status: str | None = None,
    ) -> PaginatedResult:
        """List orders with cursor-based pagination and optional filters."""
        limit = min(limit, 100)
        query = self._base_query()

        if show_id:
            query = query.where(Order.show_id == show_id)
        if status:
            query = query.where(Order.status == status)

        count_query = select(func.count()).select_from(query.subquery())
        total_count: int = self.db.execute(count_query).scalar_one()

        if cursor:
            query = query.where(Order.id > uuid.UUID(cursor))

        query = query.order_by(Order.id).limit(limit + 1)
        results = list(self.db.execute(query).scalars().all())

        next_cursor: str | None = None
        if len(results) > limit:
            results = results[:limit]
            next_cursor = str(results[-1].id)

        return PaginatedResult(items=results, total_count=total_count, next_cursor=next_cursor)

    def list_by_show(self, show_id: uuid.UUID) -> list[Order]:
        """List all non-deleted orders for a specific show."""
        query = self._base_query().where(Order.show_id == show_id).order_by(Order.created_at)
        return list(self.db.execute(query).scalars().all())

    def get_by_item_id(self, item_id: uuid.UUID) -> Order | None:
        """Find an active (non-cancelled, non-deleted) order for an inventory item."""
        return self.db.execute(
            self._base_query().where(
                Order.inventory_item_id == item_id,
                Order.status != "cancelled",
            )
        ).scalar_one_or_none()

    def list_deleted(self) -> list[Order]:
        """List soft-deleted orders within 30-day retention."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        query = (
            select(Order)
            .where(
                Order.account_id == self.account_id,
                Order.deleted_at.is_not(None),
                Order.deleted_at > cutoff,
            )
            .order_by(Order.deleted_at.desc())
        )
        return list(self.db.execute(query).scalars().all())

    def create(self, order: Order) -> Order:
        self.db.add(order)
        self.db.flush()
        return order

    def save(self) -> None:
        self.db.flush()

    @staticmethod
    def purge_expired(db: Session) -> int:
        """Permanently delete orders soft-deleted more than 30 days ago."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        result = db.execute(
            select(Order).where(
                Order.deleted_at.is_not(None),
                Order.deleted_at < cutoff,
            )
        )
        orders = list(result.scalars().all())
        count = len(orders)
        for order in orders:
            db.delete(order)
        db.flush()
        return count
