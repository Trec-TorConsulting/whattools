"""Inventory repository — item CRUD, category CRUD, search/filter, account-scoped."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, func, select, or_
from sqlalchemy.orm import Session

from services.inventory.models.models import Category, CSVImportJob, InventoryItem
from services.shared.audit import log_audit
from services.shared.models import BaseModel


@dataclass
class PaginatedResult:
    """Result of a paginated query."""

    items: list[Any]
    total_count: int
    next_cursor: str | None


class ItemRepository:
    """Data access for InventoryItem records, account-scoped with soft-delete awareness."""

    def __init__(self, db: Session, account_id: uuid.UUID) -> None:
        self.db = db
        self.account_id = account_id

    def _base_query(self) -> Select[tuple[InventoryItem]]:
        return select(InventoryItem).where(
            InventoryItem.account_id == self.account_id,
            InventoryItem.deleted_at.is_(None),
        )

    def get_by_id(self, item_id: uuid.UUID) -> InventoryItem | None:
        return self.db.execute(
            self._base_query().where(InventoryItem.id == item_id)
        ).scalar_one_or_none()

    def list_items(
        self,
        *,
        cursor: str | None = None,
        limit: int = 50,
        search: str | None = None,
        category_id: uuid.UUID | None = None,
        status: str | None = None,
        min_cogs: float | None = None,
        max_cogs: float | None = None,
    ) -> PaginatedResult:
        """List items with cursor-based pagination and optional filters."""
        limit = min(limit, 100)
        query = self._base_query()

        # Apply filters
        if search:
            query = query.where(InventoryItem.name.ilike(f"%{search}%"))
        if category_id:
            query = query.where(InventoryItem.category_id == category_id)
        if status:
            query = query.where(InventoryItem.status == status)
        if min_cogs is not None:
            query = query.where(InventoryItem.cogs >= min_cogs)
        if max_cogs is not None:
            query = query.where(InventoryItem.cogs <= max_cogs)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total_count: int = self.db.execute(count_query).scalar_one()

        # Cursor
        if cursor:
            query = query.where(InventoryItem.id > uuid.UUID(cursor))

        query = query.order_by(InventoryItem.id).limit(limit + 1)
        results = list(self.db.execute(query).scalars().all())

        next_cursor: str | None = None
        if len(results) > limit:
            results = results[:limit]
            next_cursor = str(results[-1].id)

        return PaginatedResult(items=results, total_count=total_count, next_cursor=next_cursor)

    def list_deleted(self) -> list[InventoryItem]:
        """List soft-deleted items within the 30-day retention window."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        query = (
            select(InventoryItem)
            .where(
                InventoryItem.account_id == self.account_id,
                InventoryItem.deleted_at.is_not(None),
                InventoryItem.deleted_at > cutoff,
            )
            .order_by(InventoryItem.deleted_at.desc())
        )
        return list(self.db.execute(query).scalars().all())

    def count_active(self) -> int:
        """Count active (non-deleted) items for this account."""
        return self.db.execute(
            select(func.count())
            .select_from(InventoryItem)
            .where(
                InventoryItem.account_id == self.account_id,
                InventoryItem.deleted_at.is_(None),
            )
        ).scalar_one()

    def create(self, item: InventoryItem) -> InventoryItem:
        self.db.add(item)
        self.db.flush()
        return item

    def save(self) -> None:
        self.db.flush()

    @staticmethod
    def purge_expired(db: Session) -> int:
        """Permanently delete items soft-deleted more than 30 days ago. Returns count."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        result = db.execute(
            select(InventoryItem).where(
                InventoryItem.deleted_at.is_not(None),
                InventoryItem.deleted_at < cutoff,
            )
        )
        items = list(result.scalars().all())
        count = len(items)
        for item in items:
            db.delete(item)
        db.flush()
        return count


class CategoryRepository:
    """Data access for Category records, account-scoped."""

    def __init__(self, db: Session, account_id: uuid.UUID) -> None:
        self.db = db
        self.account_id = account_id

    def _base_query(self) -> Select[tuple[Category]]:
        return select(Category).where(
            Category.account_id == self.account_id,
            Category.deleted_at.is_(None),
        )

    def get_by_id(self, category_id: uuid.UUID) -> Category | None:
        return self.db.execute(
            self._base_query().where(Category.id == category_id)
        ).scalar_one_or_none()

    def get_by_name(self, name: str) -> Category | None:
        return self.db.execute(
            self._base_query().where(Category.name == name)
        ).scalar_one_or_none()

    def list_all(self) -> list[Category]:
        return list(
            self.db.execute(self._base_query().order_by(Category.name)).scalars().all()
        )

    def create(self, category: Category) -> Category:
        self.db.add(category)
        self.db.flush()
        return category

    def save(self) -> None:
        self.db.flush()

    @staticmethod
    def purge_expired(db: Session) -> int:
        """Permanently delete categories soft-deleted more than 30 days ago."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        result = db.execute(
            select(Category).where(
                Category.deleted_at.is_not(None),
                Category.deleted_at < cutoff,
            )
        )
        cats = list(result.scalars().all())
        count = len(cats)
        for cat in cats:
            db.delete(cat)
        db.flush()
        return count


class CSVImportJobRepository:
    """Data access for CSVImportJob records."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, job_id: uuid.UUID, account_id: uuid.UUID) -> CSVImportJob | None:
        return self.db.execute(
            select(CSVImportJob).where(
                CSVImportJob.id == job_id,
                CSVImportJob.account_id == account_id,
                CSVImportJob.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

    def create(self, job: CSVImportJob) -> CSVImportJob:
        self.db.add(job)
        self.db.flush()
        return job

    def save(self) -> None:
        self.db.flush()
