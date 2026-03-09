"""Tests for inventory repositories."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from services.inventory.models.models import (
    Category,
    CSVImportJob,
    ImportJobStatus,
    InventoryItem,
    ItemStatus,
)
from services.inventory.repositories.inventory_repository import (
    CategoryRepository,
    CSVImportJobRepository,
    ItemRepository,
)


class TestItemRepository:
    def test_create_and_get(self, db_session: Session, sample_account) -> None:  # type: ignore[no-untyped-def]
        repo = ItemRepository(db_session, sample_account.id)
        item = InventoryItem(
            account_id=sample_account.id,
            name="New Item",
            cogs=5.0,
            quantity=3,
        )
        repo.create(item)
        db_session.flush()

        fetched = repo.get_by_id(item.id)
        assert fetched is not None
        assert fetched.name == "New Item"

    def test_get_nonexistent(self, db_session: Session, sample_account) -> None:  # type: ignore[no-untyped-def]
        repo = ItemRepository(db_session, sample_account.id)
        assert repo.get_by_id(uuid.uuid4()) is None

    def test_get_excludes_deleted(self, db_session: Session, sample_account) -> None:  # type: ignore[no-untyped-def]
        repo = ItemRepository(db_session, sample_account.id)
        item = InventoryItem(account_id=sample_account.id, name="Soon Deleted")
        repo.create(item)
        item.deleted_at = datetime.now(timezone.utc)
        db_session.flush()

        assert repo.get_by_id(item.id) is None

    def test_cross_account_isolation(self, db_session: Session, sample_account, other_account) -> None:  # type: ignore[no-untyped-def]
        repo_a = ItemRepository(db_session, sample_account.id)
        repo_b = ItemRepository(db_session, other_account.id)

        item = InventoryItem(account_id=sample_account.id, name="Account A Item")
        repo_a.create(item)
        db_session.flush()

        assert repo_a.get_by_id(item.id) is not None
        assert repo_b.get_by_id(item.id) is None

    def test_list_items_basic(self, db_session: Session, sample_account) -> None:  # type: ignore[no-untyped-def]
        repo = ItemRepository(db_session, sample_account.id)
        for i in range(3):
            repo.create(InventoryItem(account_id=sample_account.id, name=f"Item {i}"))
        db_session.flush()

        result = repo.list_items()
        assert len(result.items) == 3
        assert result.total_count == 3
        assert result.next_cursor is None

    def test_list_items_pagination(self, db_session: Session, sample_account) -> None:  # type: ignore[no-untyped-def]
        repo = ItemRepository(db_session, sample_account.id)
        for i in range(5):
            repo.create(InventoryItem(account_id=sample_account.id, name=f"Item {i}"))
        db_session.flush()

        result = repo.list_items(limit=2)
        assert len(result.items) == 2
        assert result.next_cursor is not None
        assert result.total_count == 5

        # Next page
        result2 = repo.list_items(cursor=result.next_cursor, limit=2)
        assert len(result2.items) == 2

    def test_list_items_search(self, db_session: Session, sample_account) -> None:  # type: ignore[no-untyped-def]
        repo = ItemRepository(db_session, sample_account.id)
        repo.create(InventoryItem(account_id=sample_account.id, name="Red Widget"))
        repo.create(InventoryItem(account_id=sample_account.id, name="Blue Gadget"))
        repo.create(InventoryItem(account_id=sample_account.id, name="Green Widget"))
        db_session.flush()

        result = repo.list_items(search="widget")
        assert len(result.items) == 2

    def test_list_items_filter_status(self, db_session: Session, sample_account) -> None:  # type: ignore[no-untyped-def]
        repo = ItemRepository(db_session, sample_account.id)
        repo.create(InventoryItem(account_id=sample_account.id, name="A", status=ItemStatus.AVAILABLE))
        repo.create(InventoryItem(account_id=sample_account.id, name="B", status=ItemStatus.SOLD))
        db_session.flush()

        result = repo.list_items(status="sold")
        assert len(result.items) == 1
        assert result.items[0].name == "B"

    def test_list_items_filter_category(self, db_session: Session, sample_account, sample_category) -> None:  # type: ignore[no-untyped-def]
        repo = ItemRepository(db_session, sample_account.id)
        repo.create(InventoryItem(account_id=sample_account.id, name="Categorized", category_id=sample_category.id))
        repo.create(InventoryItem(account_id=sample_account.id, name="Uncategorized"))
        db_session.flush()

        result = repo.list_items(category_id=sample_category.id)
        assert len(result.items) == 1
        assert result.items[0].name == "Categorized"

    def test_list_items_filter_cogs_range(self, db_session: Session, sample_account) -> None:  # type: ignore[no-untyped-def]
        repo = ItemRepository(db_session, sample_account.id)
        repo.create(InventoryItem(account_id=sample_account.id, name="Cheap", cogs=5.0))
        repo.create(InventoryItem(account_id=sample_account.id, name="Mid", cogs=50.0))
        repo.create(InventoryItem(account_id=sample_account.id, name="Expensive", cogs=200.0))
        db_session.flush()

        result = repo.list_items(min_cogs=10.0, max_cogs=100.0)
        assert len(result.items) == 1
        assert result.items[0].name == "Mid"

    def test_list_deleted(self, db_session: Session, sample_account) -> None:  # type: ignore[no-untyped-def]
        repo = ItemRepository(db_session, sample_account.id)
        item = InventoryItem(account_id=sample_account.id, name="Deleted")
        repo.create(item)
        item.deleted_at = datetime.now(timezone.utc)
        db_session.flush()

        deleted = repo.list_deleted()
        assert len(deleted) == 1
        assert deleted[0].name == "Deleted"

    def test_list_deleted_excludes_expired(self, db_session: Session, sample_account) -> None:  # type: ignore[no-untyped-def]
        repo = ItemRepository(db_session, sample_account.id)
        item = InventoryItem(account_id=sample_account.id, name="Old Deleted")
        repo.create(item)
        item.deleted_at = datetime.now(timezone.utc) - timedelta(days=31)
        db_session.flush()

        deleted = repo.list_deleted()
        assert len(deleted) == 0

    def test_count_active(self, db_session: Session, sample_account) -> None:  # type: ignore[no-untyped-def]
        repo = ItemRepository(db_session, sample_account.id)
        repo.create(InventoryItem(account_id=sample_account.id, name="Active 1"))
        repo.create(InventoryItem(account_id=sample_account.id, name="Active 2"))
        deleted = InventoryItem(account_id=sample_account.id, name="Deleted")
        repo.create(deleted)
        deleted.deleted_at = datetime.now(timezone.utc)
        db_session.flush()

        assert repo.count_active() == 2

    def test_purge_expired(self, db_session: Session, sample_account) -> None:  # type: ignore[no-untyped-def]
        repo = ItemRepository(db_session, sample_account.id)
        recent = InventoryItem(account_id=sample_account.id, name="Recent")
        repo.create(recent)
        recent.deleted_at = datetime.now(timezone.utc) - timedelta(days=15)

        old = InventoryItem(account_id=sample_account.id, name="Old")
        repo.create(old)
        old.deleted_at = datetime.now(timezone.utc) - timedelta(days=31)
        db_session.flush()

        purged = ItemRepository.purge_expired(db_session)
        assert purged == 1


class TestCategoryRepository:
    def test_create_and_get(self, db_session: Session, sample_account) -> None:  # type: ignore[no-untyped-def]
        repo = CategoryRepository(db_session, sample_account.id)
        cat = Category(account_id=sample_account.id, name="Books")
        repo.create(cat)
        db_session.flush()

        fetched = repo.get_by_id(cat.id)
        assert fetched is not None
        assert fetched.name == "Books"

    def test_get_by_name(self, db_session: Session, sample_account) -> None:  # type: ignore[no-untyped-def]
        repo = CategoryRepository(db_session, sample_account.id)
        cat = Category(account_id=sample_account.id, name="Unique")
        repo.create(cat)
        db_session.flush()

        found = repo.get_by_name("Unique")
        assert found is not None
        assert found.id == cat.id

        not_found = repo.get_by_name("NonExistent")
        assert not_found is None

    def test_list_all(self, db_session: Session, sample_account) -> None:  # type: ignore[no-untyped-def]
        repo = CategoryRepository(db_session, sample_account.id)
        repo.create(Category(account_id=sample_account.id, name="B Cat"))
        repo.create(Category(account_id=sample_account.id, name="A Cat"))
        db_session.flush()

        cats = repo.list_all()
        assert len(cats) == 2
        assert cats[0].name == "A Cat"  # sorted by name

    def test_cross_account_isolation(self, db_session: Session, sample_account, other_account) -> None:  # type: ignore[no-untyped-def]
        repo_a = CategoryRepository(db_session, sample_account.id)
        repo_b = CategoryRepository(db_session, other_account.id)

        cat = Category(account_id=sample_account.id, name="A Only")
        repo_a.create(cat)
        db_session.flush()

        assert repo_a.get_by_id(cat.id) is not None
        assert repo_b.get_by_id(cat.id) is None

    def test_purge_expired(self, db_session: Session, sample_account) -> None:  # type: ignore[no-untyped-def]
        repo = CategoryRepository(db_session, sample_account.id)
        cat = Category(account_id=sample_account.id, name="OldCat")
        repo.create(cat)
        cat.deleted_at = datetime.now(timezone.utc) - timedelta(days=31)
        db_session.flush()

        purged = CategoryRepository.purge_expired(db_session)
        assert purged == 1


class TestCSVImportJobRepository:
    def test_create_and_get(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        repo = CSVImportJobRepository(db_session)
        job = CSVImportJob(
            account_id=sample_account.id,
            user_id=sample_user.id,
            filename="test.csv",
        )
        repo.create(job)
        db_session.flush()

        fetched = repo.get_by_id(job.id, sample_account.id)
        assert fetched is not None
        assert fetched.filename == "test.csv"

    def test_get_cross_account(self, db_session: Session, sample_account, sample_user, other_account) -> None:  # type: ignore[no-untyped-def]
        repo = CSVImportJobRepository(db_session)
        job = CSVImportJob(
            account_id=sample_account.id,
            user_id=sample_user.id,
            filename="test.csv",
        )
        repo.create(job)
        db_session.flush()

        # Should not be visible to other account
        assert repo.get_by_id(job.id, other_account.id) is None
