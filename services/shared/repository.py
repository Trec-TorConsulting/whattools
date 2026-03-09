"""Base repository with account scoping, soft delete awareness, and cursor-based pagination."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from services.shared.audit import log_audit
from services.shared.models import BaseModel

T = TypeVar("T", bound=BaseModel)


@dataclass
class PaginatedResult(Generic[T]):
    """Result of a paginated query."""

    items: list[T]
    total_count: int
    next_cursor: str | None


class BaseRepository(Generic[T]):
    """Base repository with account scoping, soft deletes, and pagination.

    All queries are automatically scoped to the given account_id and exclude
    soft-deleted records unless explicitly requested.
    """

    model: type[T]

    def __init__(self, db: Session, account_id: uuid.UUID) -> None:
        self.db = db
        self.account_id = account_id

    def _base_query(self, *, include_deleted: bool = False) -> Select[tuple[T]]:
        """Build a base query scoped to account with optional soft-delete filter."""
        query = select(self.model).where(self.model.account_id == self.account_id)  # type: ignore[attr-defined]
        if not include_deleted:
            query = query.where(self.model.deleted_at.is_(None))
        return query

    def get_by_id(self, resource_id: uuid.UUID, *, include_deleted: bool = False) -> T | None:
        """Get a single record by ID, scoped to account."""
        query = self._base_query(include_deleted=include_deleted).where(self.model.id == resource_id)
        return self.db.execute(query).scalar_one_or_none()

    def list_all(
        self,
        *,
        cursor: str | None = None,
        limit: int = 50,
        include_deleted: bool = False,
        filters: list[Any] | None = None,
    ) -> PaginatedResult[T]:
        """List records with cursor-based pagination.

        Args:
            cursor: UUID string of the last item from previous page.
            limit: Maximum number of items to return (max 100).
            include_deleted: Whether to include soft-deleted records.
            filters: Additional SQLAlchemy filter conditions.

        Returns:
            PaginatedResult with items, total_count, and next_cursor.
        """
        limit = min(limit, 100)
        query = self._base_query(include_deleted=include_deleted)

        if filters:
            for f in filters:
                query = query.where(f)

        count_query = select(func.count()).select_from(query.subquery())
        total_count: int = self.db.execute(count_query).scalar_one()

        if cursor:
            query = query.where(self.model.id > uuid.UUID(cursor))

        query = query.order_by(self.model.id).limit(limit + 1)
        results = list(self.db.execute(query).scalars().all())

        next_cursor: str | None = None
        if len(results) > limit:
            results = results[:limit]
            next_cursor = str(results[-1].id)

        return PaginatedResult(items=results, total_count=total_count, next_cursor=next_cursor)

    def create(self, entity: T, *, actor_id: uuid.UUID | None = None) -> T:
        """Create a new record and log audit entry."""
        self.db.add(entity)
        self.db.flush()

        if actor_id is not None:
            log_audit(
                self.db,
                account_id=self.account_id,
                actor_id=actor_id,
                action="create",
                resource_type=self.model.__tablename__,
                resource_id=entity.id,
            )
        return entity

    def update(
        self,
        entity: T,
        updates: dict[str, Any],
        *,
        actor_id: uuid.UUID | None = None,
    ) -> T:
        """Update a record, track changes, and log audit entry."""
        old_values: dict[str, Any] = {}
        new_values: dict[str, Any] = {}

        for key, value in updates.items():
            if hasattr(entity, key):
                old_val = getattr(entity, key)
                if old_val != value:
                    old_values[key] = str(old_val) if old_val is not None else None
                    new_values[key] = str(value) if value is not None else None
                    setattr(entity, key, value)

        entity.updated_at = datetime.now(timezone.utc)
        self.db.flush()

        if actor_id is not None and old_values:
            log_audit(
                self.db,
                account_id=self.account_id,
                actor_id=actor_id,
                action="update",
                resource_type=self.model.__tablename__,
                resource_id=entity.id,
                changes={"old": old_values, "new": new_values},
            )
        return entity

    def soft_delete(self, entity: T, *, actor_id: uuid.UUID | None = None) -> T:
        """Soft-delete a record by setting deleted_at."""
        entity.deleted_at = datetime.now(timezone.utc)
        entity.updated_at = datetime.now(timezone.utc)
        self.db.flush()

        if actor_id is not None:
            log_audit(
                self.db,
                account_id=self.account_id,
                actor_id=actor_id,
                action="delete",
                resource_type=self.model.__tablename__,
                resource_id=entity.id,
            )
        return entity

    def restore(self, entity: T, *, actor_id: uuid.UUID | None = None) -> T:
        """Restore a soft-deleted record."""
        entity.deleted_at = None
        entity.updated_at = datetime.now(timezone.utc)
        self.db.flush()

        if actor_id is not None:
            log_audit(
                self.db,
                account_id=self.account_id,
                actor_id=actor_id,
                action="restore",
                resource_type=self.model.__tablename__,
                resource_id=entity.id,
            )
        return entity

    def list_deleted(self, *, cursor: str | None = None, limit: int = 50) -> PaginatedResult[T]:
        """List soft-deleted records within the 30-day retention window."""
        thirty_days_ago = datetime.now(timezone.utc).replace(day=datetime.now(timezone.utc).day)
        from datetime import timedelta

        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

        return self.list_all(
            cursor=cursor,
            limit=limit,
            include_deleted=True,
            filters=[
                self.model.deleted_at.isnot(None),
                self.model.deleted_at >= thirty_days_ago,
            ],
        )

    def purge_expired(self) -> int:
        """Permanently delete records soft-deleted more than 30 days ago."""
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        query = (
            select(self.model)
            .where(self.model.account_id == self.account_id)  # type: ignore[attr-defined]
            .where(self.model.deleted_at.isnot(None))
            .where(self.model.deleted_at < cutoff)
        )
        expired = list(self.db.execute(query).scalars().all())
        for record in expired:
            self.db.delete(record)
        self.db.flush()
        return len(expired)
