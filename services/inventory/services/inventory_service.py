"""Inventory service layer — item/category management, search, tier enforcement."""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from services.inventory.models.models import Category, InventoryItem, ItemStatus
from services.inventory.repositories.inventory_repository import (
    CategoryRepository,
    ItemRepository,
    PaginatedResult,
)
from services.shared.audit import log_audit
from services.shared.events import EventPublisher
from services.shared.logging import get_logger

logger = get_logger("inventory_service")

# Free tier limit
FREE_TIER_ITEM_LIMIT = 50


class InventoryServiceError(Exception):
    """Base exception for inventory service errors."""

    def __init__(self, message: str, code: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class InventoryService:
    """Item and category management with tier enforcement and audit logging."""

    def __init__(
        self,
        db: Session,
        account_id: uuid.UUID,
        *,
        event_publisher: EventPublisher | None = None,
        item_limit: int = FREE_TIER_ITEM_LIMIT,
    ) -> None:
        self.db = db
        self.account_id = account_id
        self.item_repo = ItemRepository(db, account_id)
        self.category_repo = CategoryRepository(db, account_id)
        self.event_publisher = event_publisher
        self.item_limit = item_limit

    # ── Item CRUD ───────────────────────────────────────────────────

    def create_item(self, data: dict[str, Any], *, actor_id: uuid.UUID) -> dict[str, Any]:
        """Create a new inventory item.

        Raises:
            InventoryServiceError: If the tier limit is exceeded.
        """
        if self.item_limit > 0:
            count = self.item_repo.count_active()
            if count >= self.item_limit:
                raise InventoryServiceError(
                    f"Item limit of {self.item_limit} reached for your plan.",
                    "forbidden",
                    403,
                )

        # Validate category exists if provided
        if data.get("category_id"):
            cat = self.category_repo.get_by_id(data["category_id"])
            if cat is None:
                raise InventoryServiceError("Category not found.", "not_found", 404)

        item = InventoryItem(
            account_id=self.account_id,
            name=data["name"],
            description=data.get("description", ""),
            category_id=data.get("category_id"),
            cogs=data.get("cogs", 0.0),
            quantity=data.get("quantity", 1),
            status=data.get("status", ItemStatus.AVAILABLE),
        )
        self.item_repo.create(item)

        log_audit(
            self.db,
            account_id=self.account_id,
            actor_id=actor_id,
            action="create",
            resource_type="inventory_items",
            resource_id=item.id,
        )
        self.db.commit()

        self._publish_event("inventory.item.created", {
            "item_id": str(item.id),
            "account_id": str(self.account_id),
            "name": item.name,
        })

        return self._item_to_dict(item)

    def get_item(self, item_id: uuid.UUID) -> dict[str, Any]:
        """Get a single item by ID.

        Raises:
            InventoryServiceError: If not found or belongs to another account.
        """
        item = self.item_repo.get_by_id(item_id)
        if item is None:
            raise InventoryServiceError("Item not found.", "not_found", 404)
        return self._item_to_dict(item)

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
    ) -> dict[str, Any]:
        """List items with pagination and filters."""
        result = self.item_repo.list_items(
            cursor=cursor,
            limit=limit,
            search=search,
            category_id=category_id,
            status=status,
            min_cogs=min_cogs,
            max_cogs=max_cogs,
        )
        return {
            "items": [self._item_to_dict(i) for i in result.items],
            "total_count": result.total_count,
            "next_cursor": result.next_cursor,
        }

    def update_item(self, item_id: uuid.UUID, updates: dict[str, Any], *, actor_id: uuid.UUID) -> dict[str, Any]:
        """Update an item.

        Raises:
            InventoryServiceError: If not found.
        """
        item = self.item_repo.get_by_id(item_id)
        if item is None:
            raise InventoryServiceError("Item not found.", "not_found", 404)

        # Validate category if being changed
        if "category_id" in updates and updates["category_id"] is not None:
            cat = self.category_repo.get_by_id(updates["category_id"])
            if cat is None:
                raise InventoryServiceError("Category not found.", "not_found", 404)

        changes: dict[str, Any] = {}
        for key, value in updates.items():
            old_val = getattr(item, key, None)
            if old_val != value:
                changes[key] = {"old": old_val, "new": value}
                setattr(item, key, value)

        if changes:
            item.updated_at = datetime.now(timezone.utc)
            self.item_repo.save()
            log_audit(
                self.db,
                account_id=self.account_id,
                actor_id=actor_id,
                action="update",
                resource_type="inventory_items",
                resource_id=item.id,
                changes=changes,
            )
            self.db.commit()

            self._publish_event("inventory.item.updated", {
                "item_id": str(item.id),
                "account_id": str(self.account_id),
                "changes": list(changes.keys()),
            })

        return self._item_to_dict(item)

    def delete_item(self, item_id: uuid.UUID, *, actor_id: uuid.UUID) -> None:
        """Soft-delete an item.

        Raises:
            InventoryServiceError: If not found.
        """
        item = self.item_repo.get_by_id(item_id)
        if item is None:
            raise InventoryServiceError("Item not found.", "not_found", 404)

        item.deleted_at = datetime.now(timezone.utc)
        self.item_repo.save()

        log_audit(
            self.db,
            account_id=self.account_id,
            actor_id=actor_id,
            action="delete",
            resource_type="inventory_items",
            resource_id=item.id,
        )
        self.db.commit()

        self._publish_event("inventory.item.deleted", {
            "item_id": str(item.id),
            "account_id": str(self.account_id),
        })

    def list_deleted_items(self) -> list[dict[str, Any]]:
        """List soft-deleted items within 30-day retention."""
        items = self.item_repo.list_deleted()
        return [self._item_to_dict(i) for i in items]

    def restore_item(self, item_id: uuid.UUID, *, actor_id: uuid.UUID) -> dict[str, Any]:
        """Restore a soft-deleted item.

        Raises:
            InventoryServiceError: If not found/not deleted or tier limit exceeded.
        """
        # Find the item including deleted
        from sqlalchemy import select
        item = self.db.execute(
            select(InventoryItem).where(
                InventoryItem.id == item_id,
                InventoryItem.account_id == self.account_id,
                InventoryItem.deleted_at.is_not(None),
            )
        ).scalar_one_or_none()

        if item is None:
            raise InventoryServiceError("Deleted item not found.", "not_found", 404)

        # Check tier limit
        if self.item_limit > 0:
            count = self.item_repo.count_active()
            if count >= self.item_limit:
                raise InventoryServiceError(
                    f"Item limit of {self.item_limit} reached for your plan.",
                    "forbidden",
                    403,
                )

        item.deleted_at = None
        item.updated_at = datetime.now(timezone.utc)
        self.item_repo.save()

        log_audit(
            self.db,
            account_id=self.account_id,
            actor_id=actor_id,
            action="restore",
            resource_type="inventory_items",
            resource_id=item.id,
        )
        self.db.commit()

        self._publish_event("inventory.item.restored", {
            "item_id": str(item.id),
            "account_id": str(self.account_id),
        })

        return self._item_to_dict(item)

    # ── Category CRUD ───────────────────────────────────────────────

    def create_category(self, data: dict[str, Any], *, actor_id: uuid.UUID) -> dict[str, Any]:
        """Create a new category.

        Raises:
            InventoryServiceError: If duplicate name.
        """
        existing = self.category_repo.get_by_name(data["name"])
        if existing is not None:
            raise InventoryServiceError("A category with this name already exists.", "conflict", 409)

        category = Category(
            account_id=self.account_id,
            name=data["name"],
            description=data.get("description", ""),
        )
        self.category_repo.create(category)

        log_audit(
            self.db,
            account_id=self.account_id,
            actor_id=actor_id,
            action="create",
            resource_type="categories",
            resource_id=category.id,
        )
        self.db.commit()

        return self._category_to_dict(category)

    def get_category(self, category_id: uuid.UUID) -> dict[str, Any]:
        cat = self.category_repo.get_by_id(category_id)
        if cat is None:
            raise InventoryServiceError("Category not found.", "not_found", 404)
        return self._category_to_dict(cat)

    def list_categories(self) -> list[dict[str, Any]]:
        cats = self.category_repo.list_all()
        return [self._category_to_dict(c) for c in cats]

    def update_category(self, category_id: uuid.UUID, updates: dict[str, Any], *, actor_id: uuid.UUID) -> dict[str, Any]:
        cat = self.category_repo.get_by_id(category_id)
        if cat is None:
            raise InventoryServiceError("Category not found.", "not_found", 404)

        # Check for duplicate name if changing
        if "name" in updates and updates["name"] != cat.name:
            existing = self.category_repo.get_by_name(updates["name"])
            if existing is not None:
                raise InventoryServiceError("A category with this name already exists.", "conflict", 409)

        changes: dict[str, Any] = {}
        for key, value in updates.items():
            old_val = getattr(cat, key, None)
            if old_val != value:
                changes[key] = {"old": old_val, "new": value}
                setattr(cat, key, value)

        if changes:
            cat.updated_at = datetime.now(timezone.utc)
            self.category_repo.save()
            log_audit(
                self.db,
                account_id=self.account_id,
                actor_id=actor_id,
                action="update",
                resource_type="categories",
                resource_id=cat.id,
                changes=changes,
            )
            self.db.commit()

        return self._category_to_dict(cat)

    def delete_category(self, category_id: uuid.UUID, *, actor_id: uuid.UUID) -> None:
        cat = self.category_repo.get_by_id(category_id)
        if cat is None:
            raise InventoryServiceError("Category not found.", "not_found", 404)

        cat.deleted_at = datetime.now(timezone.utc)
        self.category_repo.save()

        log_audit(
            self.db,
            account_id=self.account_id,
            actor_id=actor_id,
            action="delete",
            resource_type="categories",
            resource_id=cat.id,
        )
        self.db.commit()

    # ── Helpers ─────────────────────────────────────────────────────

    def _item_to_dict(self, item: InventoryItem) -> dict[str, Any]:
        return {
            "id": str(item.id),
            "account_id": str(item.account_id),
            "name": item.name,
            "description": item.description,
            "category_id": str(item.category_id) if item.category_id else None,
            "cogs": float(item.cogs),
            "quantity": item.quantity,
            "status": item.status,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
            "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None,
        }

    def _category_to_dict(self, cat: Category) -> dict[str, Any]:
        return {
            "id": str(cat.id),
            "account_id": str(cat.account_id),
            "name": cat.name,
            "description": cat.description,
            "created_at": cat.created_at.isoformat(),
            "updated_at": cat.updated_at.isoformat(),
        }

    def _publish_event(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.event_publisher is not None:
            self.event_publisher.publish(event_type, payload, source_service="inventory")
