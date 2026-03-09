"""Tests for inventory models."""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from services.inventory.models.models import (
    Category,
    CSVImportJob,
    ImportJobStatus,
    InventoryItem,
    ItemStatus,
)


class TestItemStatus:
    def test_values(self) -> None:
        assert ItemStatus.AVAILABLE == "available"
        assert ItemStatus.SOLD == "sold"
        assert ItemStatus.RESERVED == "reserved"
        assert ItemStatus.LISTED == "listed"


class TestImportJobStatus:
    def test_values(self) -> None:
        assert ImportJobStatus.PENDING_MAPPING == "pending_mapping"
        assert ImportJobStatus.PROCESSING == "processing"
        assert ImportJobStatus.COMPLETED == "completed"
        assert ImportJobStatus.COMPLETED_WITH_ERRORS == "completed_with_errors"
        assert ImportJobStatus.FAILED == "failed"


class TestCategory:
    def test_create_category(self, db_session: Session, sample_account) -> None:  # type: ignore[no-untyped-def]
        cat = Category(
            account_id=sample_account.id,
            name="Books",
            description="Book items",
        )
        db_session.add(cat)
        db_session.flush()

        assert cat.id is not None
        assert cat.name == "Books"
        assert cat.description == "Book items"
        assert cat.account_id == sample_account.id
        assert cat.deleted_at is None

    def test_category_default_description(self, db_session: Session, sample_account) -> None:  # type: ignore[no-untyped-def]
        cat = Category(account_id=sample_account.id, name="Empty")
        db_session.add(cat)
        db_session.flush()
        assert cat.description == ""


class TestInventoryItem:
    def test_create_item(self, db_session: Session, sample_account, sample_category) -> None:  # type: ignore[no-untyped-def]
        item = InventoryItem(
            account_id=sample_account.id,
            name="Widget",
            description="A widget",
            category_id=sample_category.id,
            cogs=25.99,
            quantity=10,
            status=ItemStatus.AVAILABLE,
        )
        db_session.add(item)
        db_session.flush()

        assert item.id is not None
        assert item.name == "Widget"
        assert float(item.cogs) == 25.99
        assert item.quantity == 10
        assert item.status == ItemStatus.AVAILABLE
        assert item.deleted_at is None

    def test_item_defaults(self, db_session: Session, sample_account) -> None:  # type: ignore[no-untyped-def]
        item = InventoryItem(
            account_id=sample_account.id,
            name="Default Item",
        )
        db_session.add(item)
        db_session.flush()

        assert item.description == ""
        assert item.category_id is None
        assert float(item.cogs) == 0.0
        assert item.quantity == 1
        assert item.status == ItemStatus.AVAILABLE

    def test_item_nullable_category(self, db_session: Session, sample_account) -> None:  # type: ignore[no-untyped-def]
        item = InventoryItem(
            account_id=sample_account.id,
            name="No Category",
        )
        db_session.add(item)
        db_session.flush()
        assert item.category_id is None


class TestCSVImportJob:
    def test_create_job(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        job = CSVImportJob(
            account_id=sample_account.id,
            user_id=sample_user.id,
            filename="test.csv",
            status=ImportJobStatus.PENDING_MAPPING,
        )
        db_session.add(job)
        db_session.flush()

        assert job.id is not None
        assert job.filename == "test.csv"
        assert job.status == ImportJobStatus.PENDING_MAPPING
        assert job.headers is None
        assert job.preview_rows is None
        assert job.column_mapping is None
        assert job.total_rows == 0
        assert job.success_count == 0
        assert job.error_count == 0
        assert job.skipped_count == 0
        assert job.row_errors is None

    def test_job_json_fields(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        job = CSVImportJob(
            account_id=sample_account.id,
            user_id=sample_user.id,
            filename="data.csv",
        )
        job.headers = ["Name", "Price", "Qty"]
        job.preview_rows = [["Widget", "10.00", "5"]]
        job.column_mapping = {"Name": "name", "Price": "cogs"}
        db_session.add(job)
        db_session.flush()

        fetched = db_session.get(CSVImportJob, job.id)
        assert fetched is not None
        assert fetched.headers == ["Name", "Price", "Qty"]
        assert fetched.preview_rows == [["Widget", "10.00", "5"]]
        assert fetched.column_mapping == {"Name": "name", "Price": "cogs"}
