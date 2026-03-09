"""Tests for CSV import service."""

import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from services.inventory.models.models import ImportJobStatus
from services.inventory.services.csv_import_service import (
    CSVImportService,
    InventoryServiceError,
    MAX_FILE_SIZE,
)


def _make_csv(headers: list[str], rows: list[list[str]]) -> bytes:
    """Helper to create a CSV file as bytes."""
    lines = [",".join(headers)]
    for row in rows:
        lines.append(",".join(row))
    return "\n".join(lines).encode("utf-8")


class TestCSVUpload:
    def test_upload_success(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = CSVImportService(db_session, sample_account.id)
        csv_content = _make_csv(
            ["Name", "Price", "Qty"],
            [["Widget", "10.00", "5"], ["Gadget", "20.00", "3"]],
        )
        result = svc.upload_csv(csv_content, "test.csv", actor_id=sample_user.id)
        assert result["headers"] == ["Name", "Price", "Qty"]
        assert len(result["preview_rows"]) == 2
        assert result["total_rows"] == 2
        assert result["status"] == ImportJobStatus.PENDING_MAPPING

    def test_upload_with_preview_limit(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = CSVImportService(db_session, sample_account.id)
        rows = [[f"Item {i}", "10.00", "1"] for i in range(10)]
        csv_content = _make_csv(["Name", "Price", "Qty"], rows)

        result = svc.upload_csv(csv_content, "many.csv", actor_id=sample_user.id)
        assert len(result["preview_rows"]) == 5  # Max preview
        assert result["total_rows"] == 10

    def test_upload_too_large(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = CSVImportService(db_session, sample_account.id)
        content = b"x" * (MAX_FILE_SIZE + 1)

        with pytest.raises(InventoryServiceError) as exc:
            svc.upload_csv(content, "big.csv", actor_id=sample_user.id)
        assert exc.value.status_code == 413

    def test_upload_too_many_rows(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = CSVImportService(db_session, sample_account.id)
        rows = [[f"Item {i}", "1.00", "1"] for i in range(10_001)]
        csv_content = _make_csv(["Name", "Price", "Qty"], rows)

        with pytest.raises(InventoryServiceError) as exc:
            svc.upload_csv(csv_content, "huge.csv", actor_id=sample_user.id)
        assert exc.value.status_code == 413

    def test_upload_no_data_rows(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = CSVImportService(db_session, sample_account.id)
        content = b"Name,Price,Qty\n"  # header only, no data

        with pytest.raises(InventoryServiceError) as exc:
            svc.upload_csv(content, "empty.csv", actor_id=sample_user.id)
        assert exc.value.status_code == 400

    def test_upload_invalid_encoding(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = CSVImportService(db_session, sample_account.id)
        content = b"\xff\xfe" + b"\x00" * 100  # Invalid UTF-8

        with pytest.raises(InventoryServiceError) as exc:
            svc.upload_csv(content, "bad.csv", actor_id=sample_user.id)
        assert exc.value.status_code == 400


class TestCSVMapping:
    def test_submit_mapping_success(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = CSVImportService(db_session, sample_account.id, item_limit=0)  # No limit
        csv_content = _make_csv(
            ["Product", "Cost", "Amount"],
            [["Widget", "10.00", "5"], ["Gadget", "20.00", "3"]],
        )
        upload_result = svc.upload_csv(csv_content, "test.csv", actor_id=sample_user.id)

        mapping = {"Product": "name", "Cost": "cogs", "Amount": "quantity"}
        result = svc.submit_mapping(
            uuid.UUID(upload_result["job_id"]),
            mapping,
            actor_id=sample_user.id,
        )
        assert result["status"] in (ImportJobStatus.COMPLETED, ImportJobStatus.COMPLETED_WITH_ERRORS)
        assert result["success_count"] == 2

    def test_mapping_missing_required_field(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = CSVImportService(db_session, sample_account.id)
        csv_content = _make_csv(["Cost"], [["10.00"]])
        upload_result = svc.upload_csv(csv_content, "test.csv", actor_id=sample_user.id)

        with pytest.raises(InventoryServiceError) as exc:
            svc.submit_mapping(
                uuid.UUID(upload_result["job_id"]),
                {"Cost": "cogs"},  # No "name" mapping
                actor_id=sample_user.id,
            )
        assert exc.value.status_code == 400
        assert "name" in exc.value.message.lower()

    def test_mapping_invalid_target_field(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = CSVImportService(db_session, sample_account.id)
        csv_content = _make_csv(["Name"], [["Widget"]])
        upload_result = svc.upload_csv(csv_content, "test.csv", actor_id=sample_user.id)

        with pytest.raises(InventoryServiceError) as exc:
            svc.submit_mapping(
                uuid.UUID(upload_result["job_id"]),
                {"Name": "nonexistent_field"},
                actor_id=sample_user.id,
            )
        assert exc.value.status_code == 400

    def test_mapping_invalid_source_column(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = CSVImportService(db_session, sample_account.id)
        csv_content = _make_csv(["Name"], [["Widget"]])
        upload_result = svc.upload_csv(csv_content, "test.csv", actor_id=sample_user.id)

        with pytest.raises(InventoryServiceError) as exc:
            svc.submit_mapping(
                uuid.UUID(upload_result["job_id"]),
                {"NonExistent": "name"},
                actor_id=sample_user.id,
            )
        assert exc.value.status_code == 400

    def test_mapping_already_processed(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = CSVImportService(db_session, sample_account.id, item_limit=0)
        csv_content = _make_csv(["Name"], [["Widget"]])
        upload_result = svc.upload_csv(csv_content, "test.csv", actor_id=sample_user.id)
        job_id = uuid.UUID(upload_result["job_id"])

        svc.submit_mapping(job_id, {"Name": "name"}, actor_id=sample_user.id)

        with pytest.raises(InventoryServiceError) as exc:
            svc.submit_mapping(job_id, {"Name": "name"}, actor_id=sample_user.id)
        assert exc.value.status_code == 409

    def test_mapping_job_not_found(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = CSVImportService(db_session, sample_account.id)
        with pytest.raises(InventoryServiceError) as exc:
            svc.submit_mapping(uuid.uuid4(), {"Name": "name"}, actor_id=sample_user.id)
        assert exc.value.status_code == 404


class TestCSVImportProcessing:
    def test_import_with_errors(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = CSVImportService(db_session, sample_account.id, item_limit=0)
        csv_content = _make_csv(
            ["Name", "Cost"],
            [["Widget", "10.00"], ["", "bad"]],  # Second row has empty name
        )
        upload_result = svc.upload_csv(csv_content, "test.csv", actor_id=sample_user.id)
        result = svc.submit_mapping(
            uuid.UUID(upload_result["job_id"]),
            {"Name": "name", "Cost": "cogs"},
            actor_id=sample_user.id,
        )
        assert result["status"] == ImportJobStatus.COMPLETED_WITH_ERRORS
        assert result["success_count"] == 1
        assert result["error_count"] == 1

    def test_import_all_errors(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = CSVImportService(db_session, sample_account.id, item_limit=0)
        csv_content = _make_csv(
            ["Name", "Extra"],
            [["", "x"], ["", "y"]],
        )
        upload_result = svc.upload_csv(csv_content, "test.csv", actor_id=sample_user.id)
        result = svc.submit_mapping(
            uuid.UUID(upload_result["job_id"]),
            {"Name": "name"},
            actor_id=sample_user.id,
        )
        assert result["status"] == ImportJobStatus.FAILED
        assert result["success_count"] == 0
        assert result["error_count"] == 2

    def test_import_tier_limit_enforcement(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = CSVImportService(db_session, sample_account.id, item_limit=2)
        csv_content = _make_csv(
            ["Name"],
            [["A"], ["B"], ["C"], ["D"]],
        )
        upload_result = svc.upload_csv(csv_content, "test.csv", actor_id=sample_user.id)
        result = svc.submit_mapping(
            uuid.UUID(upload_result["job_id"]),
            {"Name": "name"},
            actor_id=sample_user.id,
        )
        assert result["success_count"] == 2
        assert result["skipped_count"] == 2

    def test_import_with_all_fields(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = CSVImportService(db_session, sample_account.id, item_limit=0)
        csv_content = _make_csv(
            ["Name", "Desc", "Price", "Qty", "Status"],
            [["Widget", "A cool widget", "$15.99", "10", "available"]],
        )
        upload_result = svc.upload_csv(csv_content, "test.csv", actor_id=sample_user.id)
        result = svc.submit_mapping(
            uuid.UUID(upload_result["job_id"]),
            {"Name": "name", "Desc": "description", "Price": "cogs", "Qty": "quantity", "Status": "status"},
            actor_id=sample_user.id,
        )
        assert result["success_count"] == 1
        assert result["status"] == ImportJobStatus.COMPLETED

    def test_import_invalid_cogs(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = CSVImportService(db_session, sample_account.id, item_limit=0)
        csv_content = _make_csv(
            ["Name", "Price"],
            [["Widget", "not_a_number"]],
        )
        upload_result = svc.upload_csv(csv_content, "test.csv", actor_id=sample_user.id)
        result = svc.submit_mapping(
            uuid.UUID(upload_result["job_id"]),
            {"Name": "name", "Price": "cogs"},
            actor_id=sample_user.id,
        )
        assert result["error_count"] == 1

    def test_import_invalid_quantity(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = CSVImportService(db_session, sample_account.id, item_limit=0)
        csv_content = _make_csv(
            ["Name", "Qty"],
            [["Widget", "abc"]],
        )
        upload_result = svc.upload_csv(csv_content, "test.csv", actor_id=sample_user.id)
        result = svc.submit_mapping(
            uuid.UUID(upload_result["job_id"]),
            {"Name": "name", "Qty": "quantity"},
            actor_id=sample_user.id,
        )
        assert result["error_count"] == 1

    def test_import_invalid_status(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = CSVImportService(db_session, sample_account.id, item_limit=0)
        csv_content = _make_csv(
            ["Name", "Status"],
            [["Widget", "invalid_status"]],
        )
        upload_result = svc.upload_csv(csv_content, "test.csv", actor_id=sample_user.id)
        result = svc.submit_mapping(
            uuid.UUID(upload_result["job_id"]),
            {"Name": "name", "Status": "status"},
            actor_id=sample_user.id,
        )
        assert result["error_count"] == 1

    def test_import_negative_quantity(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = CSVImportService(db_session, sample_account.id, item_limit=0)
        csv_content = _make_csv(
            ["Name", "Qty"],
            [["Widget", "-5"]],
        )
        upload_result = svc.upload_csv(csv_content, "test.csv", actor_id=sample_user.id)
        result = svc.submit_mapping(
            uuid.UUID(upload_result["job_id"]),
            {"Name": "name", "Qty": "quantity"},
            actor_id=sample_user.id,
        )
        assert result["error_count"] == 1

    def test_import_publishes_event(self, db_session: Session, sample_account, sample_user, mock_event_publisher) -> None:  # type: ignore[no-untyped-def]
        svc = CSVImportService(db_session, sample_account.id, item_limit=0, event_publisher=mock_event_publisher)
        csv_content = _make_csv(["Name"], [["Widget"]])
        upload_result = svc.upload_csv(csv_content, "test.csv", actor_id=sample_user.id)
        svc.submit_mapping(
            uuid.UUID(upload_result["job_id"]),
            {"Name": "name"},
            actor_id=sample_user.id,
        )
        mock_event_publisher.publish.assert_called_once()
        call_args = mock_event_publisher.publish.call_args
        assert call_args[0][0] == "inventory.import.completed"


class TestGetJobStatus:
    def test_get_status(self, db_session: Session, sample_account, sample_user) -> None:  # type: ignore[no-untyped-def]
        svc = CSVImportService(db_session, sample_account.id)
        csv_content = _make_csv(["Name"], [["Widget"]])
        upload_result = svc.upload_csv(csv_content, "test.csv", actor_id=sample_user.id)

        result = svc.get_job_status(uuid.UUID(upload_result["job_id"]))
        assert result["status"] == ImportJobStatus.PENDING_MAPPING
        assert result["filename"] == "test.csv"

    def test_get_status_not_found(self, db_session: Session, sample_account) -> None:  # type: ignore[no-untyped-def]
        svc = CSVImportService(db_session, sample_account.id)
        with pytest.raises(InventoryServiceError) as exc:
            svc.get_job_status(uuid.uuid4())
        assert exc.value.status_code == 404
