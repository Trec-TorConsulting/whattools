"""Tests for inventory service layer."""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from services.inventory.models.models import (
    Category,
    InventoryItem,
    ItemStatus,
)
from services.inventory.services.inventory_service import (
    InventoryService,
    InventoryServiceError,
)


class TestItemCRUD:
    def test_create_item(self, db_session: Session, sample_account, sample_user, mock_event_publisher) -> None:  # type: ignore[no-untyped-def]
        svc = InventoryService(db_session, sample_account.id, event_publisher=mock_event_publisher)
        result = svc.create_item(
            {"name": "Widget", "cogs": 10.0, "quantity": 5},
            actor_id=sample_user.id,
        )
        assert result["name"] == "Widget"
        assert result["cogs"] == 10.0
        assert result["quantity"] == 5
        assert result["status"] == "available"
        mock_event_publisher.publish.assert_called_once()

    def test_create_item_with_category(self, db_session: Session, sample_account, sample_user, sample_category) -> None:  # type: ignore[no-untyped-def]
        svc = InventoryService(db_session, sample_account.id)
        result = svc.create_item(
            {"name": "Categorized", "category_id": sample_category.id},
            actor_id=sample_user.id,
        )
        assert result["category_id"] == str(sample_category.id)

    def test_create_item_invalid_category(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = InventoryService(db_session, sample_account.id)
        with pytest.raises(InventoryServiceError) as exc:
            svc.create_item(
                {"name": "Bad Cat", "category_id": uuid.uuid4()},
                actor_id=sample_user.id,
            )
        assert exc.value.status_code == 404

    def test_create_item_exceeds_tier_limit(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = InventoryService(db_session, sample_account.id, item_limit=2)
        svc.create_item({"name": "Item 1"}, actor_id=sample_user.id)
        svc.create_item({"name": "Item 2"}, actor_id=sample_user.id)

        with pytest.raises(InventoryServiceError) as exc:
            svc.create_item({"name": "Item 3"}, actor_id=sample_user.id)
        assert exc.value.status_code == 403
        assert "limit" in exc.value.message.lower()

    def test_get_item(self, db_session: Session, sample_account, sample_item) -> None:  # type: ignore[no-untyped-def]
        svc = InventoryService(db_session, sample_account.id)
        result = svc.get_item(sample_item.id)
        assert result["name"] == "Test Widget"

    def test_get_item_not_found(self, db_session: Session, sample_account) -> None:  # type: ignore[no-untyped-def]
        svc = InventoryService(db_session, sample_account.id)
        with pytest.raises(InventoryServiceError) as exc:
            svc.get_item(uuid.uuid4())
        assert exc.value.status_code == 404

    def test_get_item_cross_account(self, db_session: Session, sample_account, other_account, sample_item) -> None:  # type: ignore[no-untyped-def]
        svc = InventoryService(db_session, other_account.id)
        with pytest.raises(InventoryServiceError) as exc:
            svc.get_item(sample_item.id)
        assert exc.value.status_code == 404

    def test_list_items(self, db_session: Session, sample_account, sample_item) -> None:  # type: ignore[no-untyped-def]
        svc = InventoryService(db_session, sample_account.id)
        result = svc.list_items()
        assert len(result["items"]) >= 1
        assert result["total_count"] >= 1

    def test_list_items_with_search(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = InventoryService(db_session, sample_account.id)
        svc.create_item({"name": "Red Ball"}, actor_id=sample_user.id)
        svc.create_item({"name": "Blue Ball"}, actor_id=sample_user.id)
        svc.create_item({"name": "Green Cube"}, actor_id=sample_user.id)

        result = svc.list_items(search="ball")
        assert len(result["items"]) == 2

    def test_update_item(self, db_session: Session, sample_account, sample_item, sample_user, mock_event_publisher) -> None:  # type: ignore[no-untyped-def]
        svc = InventoryService(db_session, sample_account.id, event_publisher=mock_event_publisher)
        result = svc.update_item(
            sample_item.id,
            {"name": "Updated Widget", "cogs": 20.0},
            actor_id=sample_user.id,
        )
        assert result["name"] == "Updated Widget"
        assert result["cogs"] == 20.0
        mock_event_publisher.publish.assert_called_once()

    def test_update_item_no_changes(self, db_session: Session, sample_account, sample_item, sample_user, mock_event_publisher) -> None:  # type: ignore[no-untyped-def]
        svc = InventoryService(db_session, sample_account.id, event_publisher=mock_event_publisher)
        result = svc.update_item(
            sample_item.id,
            {"name": "Test Widget"},  # Same name
            actor_id=sample_user.id,
        )
        assert result["name"] == "Test Widget"
        mock_event_publisher.publish.assert_not_called()

    def test_update_item_not_found(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = InventoryService(db_session, sample_account.id)
        with pytest.raises(InventoryServiceError) as exc:
            svc.update_item(uuid.uuid4(), {"name": "X"}, actor_id=sample_user.id)
        assert exc.value.status_code == 404

    def test_update_item_invalid_category(self, db_session: Session, sample_account, sample_item, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = InventoryService(db_session, sample_account.id)
        with pytest.raises(InventoryServiceError) as exc:
            svc.update_item(
                sample_item.id,
                {"category_id": uuid.uuid4()},
                actor_id=sample_user.id,
            )
        assert exc.value.status_code == 404

    def test_delete_item(self, db_session: Session, sample_account, sample_item, sample_user, mock_event_publisher) -> None:  # type: ignore[no-untyped-def]
        svc = InventoryService(db_session, sample_account.id, event_publisher=mock_event_publisher)
        svc.delete_item(sample_item.id, actor_id=sample_user.id)

        with pytest.raises(InventoryServiceError):
            svc.get_item(sample_item.id)

        mock_event_publisher.publish.assert_called_once()

    def test_delete_item_not_found(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = InventoryService(db_session, sample_account.id)
        with pytest.raises(InventoryServiceError) as exc:
            svc.delete_item(uuid.uuid4(), actor_id=sample_user.id)
        assert exc.value.status_code == 404


class TestSoftDeleteAndRestore:
    def test_list_deleted(self, db_session: Session, sample_account, sample_item, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = InventoryService(db_session, sample_account.id)
        svc.delete_item(sample_item.id, actor_id=sample_user.id)

        deleted = svc.list_deleted_items()
        assert len(deleted) == 1
        assert deleted[0]["name"] == "Test Widget"

    def test_restore_item(self, db_session: Session, sample_account, sample_item, sample_user, mock_event_publisher) -> None:  # type: ignore[no-untyped-def]
        svc = InventoryService(db_session, sample_account.id, event_publisher=mock_event_publisher)
        svc.delete_item(sample_item.id, actor_id=sample_user.id)
        mock_event_publisher.publish.reset_mock()

        result = svc.restore_item(sample_item.id, actor_id=sample_user.id)
        assert result["deleted_at"] is None
        assert result["name"] == "Test Widget"
        mock_event_publisher.publish.assert_called_once()

    def test_restore_not_found(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = InventoryService(db_session, sample_account.id)
        with pytest.raises(InventoryServiceError) as exc:
            svc.restore_item(uuid.uuid4(), actor_id=sample_user.id)
        assert exc.value.status_code == 404

    def test_restore_exceeds_tier_limit(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        # Create 2 items with no limit, then enforce limit=2 for restore test
        svc = InventoryService(db_session, sample_account.id, item_limit=0)
        r1 = svc.create_item({"name": "Keep"}, actor_id=sample_user.id)
        r2 = svc.create_item({"name": "Delete Me"}, actor_id=sample_user.id)

        # Delete item 2
        svc.delete_item(uuid.UUID(r2["id"]), actor_id=sample_user.id)

        # Now enforce a limit of 1 — we have 1 active item, restoring would exceed
        svc_limited = InventoryService(db_session, sample_account.id, item_limit=1)
        with pytest.raises(InventoryServiceError) as exc:
            svc_limited.restore_item(uuid.UUID(r2["id"]), actor_id=sample_user.id)
        assert exc.value.status_code == 403


class TestCategoryCRUD:
    def test_create_category(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = InventoryService(db_session, sample_account.id)
        result = svc.create_category(
            {"name": "Books", "description": "Book items"},
            actor_id=sample_user.id,
        )
        assert result["name"] == "Books"
        assert result["description"] == "Book items"

    def test_create_category_duplicate(self, db_session: Session, sample_account, sample_user, sample_category) -> None:  # type: ignore[no-untyped-def]
        svc = InventoryService(db_session, sample_account.id)
        with pytest.raises(InventoryServiceError) as exc:
            svc.create_category(
                {"name": "Electronics"},  # Same as sample_category
                actor_id=sample_user.id,
            )
        assert exc.value.status_code == 409

    def test_get_category(self, db_session: Session, sample_account, sample_category) -> None:  # type: ignore[no-untyped-def]
        svc = InventoryService(db_session, sample_account.id)
        result = svc.get_category(sample_category.id)
        assert result["name"] == "Electronics"

    def test_get_category_not_found(self, db_session: Session, sample_account) -> None:  # type: ignore[no-untyped-def]
        svc = InventoryService(db_session, sample_account.id)
        with pytest.raises(InventoryServiceError) as exc:
            svc.get_category(uuid.uuid4())
        assert exc.value.status_code == 404

    def test_list_categories(self, db_session: Session, sample_account, sample_category) -> None:  # type: ignore[no-untyped-def]
        svc = InventoryService(db_session, sample_account.id)
        result = svc.list_categories()
        assert len(result) >= 1

    def test_update_category(self, db_session: Session, sample_account, sample_category, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = InventoryService(db_session, sample_account.id)
        result = svc.update_category(
            sample_category.id,
            {"name": "Tech"},
            actor_id=sample_user.id,
        )
        assert result["name"] == "Tech"

    def test_update_category_duplicate_name(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = InventoryService(db_session, sample_account.id)
        svc.create_category({"name": "Cat A"}, actor_id=sample_user.id)
        r2 = svc.create_category({"name": "Cat B"}, actor_id=sample_user.id)

        with pytest.raises(InventoryServiceError) as exc:
            svc.update_category(
                uuid.UUID(r2["id"]),
                {"name": "Cat A"},
                actor_id=sample_user.id,
            )
        assert exc.value.status_code == 409

    def test_update_category_not_found(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = InventoryService(db_session, sample_account.id)
        with pytest.raises(InventoryServiceError) as exc:
            svc.update_category(uuid.uuid4(), {"name": "X"}, actor_id=sample_user.id)
        assert exc.value.status_code == 404

    def test_delete_category(self, db_session: Session, sample_account, sample_category, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = InventoryService(db_session, sample_account.id)
        svc.delete_category(sample_category.id, actor_id=sample_user.id)

        with pytest.raises(InventoryServiceError):
            svc.get_category(sample_category.id)

    def test_delete_category_not_found(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = InventoryService(db_session, sample_account.id)
        with pytest.raises(InventoryServiceError) as exc:
            svc.delete_category(uuid.uuid4(), actor_id=sample_user.id)
        assert exc.value.status_code == 404


class TestEventPublishing:
    def test_create_publishes_event(self, db_session: Session, sample_account, sample_user, mock_event_publisher) -> None:  # type: ignore[no-untyped-def]
        svc = InventoryService(db_session, sample_account.id, event_publisher=mock_event_publisher)
        svc.create_item({"name": "Evented"}, actor_id=sample_user.id)
        mock_event_publisher.publish.assert_called_once()
        call_args = mock_event_publisher.publish.call_args
        assert call_args[0][0] == "inventory.item.created"

    def test_no_publisher_no_error(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = InventoryService(db_session, sample_account.id, event_publisher=None)
        result = svc.create_item({"name": "No Events"}, actor_id=sample_user.id)
        assert result["name"] == "No Events"

    def test_delete_publishes_event(self, db_session: Session, sample_account, sample_item, sample_user, mock_event_publisher) -> None:  # type: ignore[no-untyped-def]
        svc = InventoryService(db_session, sample_account.id, event_publisher=mock_event_publisher)
        svc.delete_item(sample_item.id, actor_id=sample_user.id)
        call_args = mock_event_publisher.publish.call_args
        assert call_args[0][0] == "inventory.item.deleted"

    def test_restore_publishes_event(self, db_session: Session, sample_account, sample_item, sample_user, mock_event_publisher) -> None:  # type: ignore[no-untyped-def]
        svc = InventoryService(db_session, sample_account.id, event_publisher=mock_event_publisher)
        svc.delete_item(sample_item.id, actor_id=sample_user.id)
        mock_event_publisher.publish.reset_mock()
        svc.restore_item(sample_item.id, actor_id=sample_user.id)
        call_args = mock_event_publisher.publish.call_args
        assert call_args[0][0] == "inventory.item.restored"
