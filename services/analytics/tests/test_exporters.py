"""Tests for export infrastructure — CSV, PDF, charts, models, repository, schemas."""

import csv
import io
import os
import tempfile
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from sqlalchemy.orm import Session

from services.analytics.exporters.csv_exporter import CsvExporter
from services.analytics.exporters.charts import (
    generate_category_chart,
    generate_top_items_chart,
    generate_trend_chart,
)
from services.analytics.models.models import (
    ExportFormat,
    ExportJob,
    ExportStatus,
    VALID_FORMATS,
    VALID_REPORT_TYPES,
)
from services.analytics.repositories.export_repository import ExportRepository
from services.analytics.schemas.schemas import ExportCreateSchema, ExportResponseSchema
from services.auth.models.models import Account


# ── ExportJob Model ──────────────────────────────────────────────


class TestExportJobModel:
    """Tests for the ExportJob model."""

    def test_create_export_job(
        self, db_session: Session, sample_account: Account
    ) -> None:
        now = datetime.now(timezone.utc)
        job = ExportJob(
            account_id=sample_account.id,
            report_type="summary",
            format="csv",
            period="30d",
            status=ExportStatus.PENDING,
            expires_at=now + timedelta(days=7),
        )
        db_session.add(job)
        db_session.flush()

        assert job.id is not None
        assert job.account_id == sample_account.id
        assert job.report_type == "summary"
        assert job.format == "csv"
        assert job.status == ExportStatus.PENDING
        assert job.file_path == ""
        assert job.file_size == 0
        assert job.error_message == ""

    def test_status_transitions(
        self, db_session: Session, sample_account: Account
    ) -> None:
        job = ExportJob(
            account_id=sample_account.id,
            report_type="full",
            format="pdf",
            period="7d",
            status=ExportStatus.PENDING,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db_session.add(job)
        db_session.flush()

        job.status = ExportStatus.PROCESSING
        db_session.flush()
        assert job.status == ExportStatus.PROCESSING

        job.status = ExportStatus.COMPLETED
        job.file_path = "/data/exports/test.pdf"
        job.file_size = 1024
        db_session.flush()
        assert job.status == ExportStatus.COMPLETED
        assert job.file_size == 1024

    def test_failed_status(
        self, db_session: Session, sample_account: Account
    ) -> None:
        job = ExportJob(
            account_id=sample_account.id,
            report_type="trends",
            format="csv",
            period="90d",
            status=ExportStatus.FAILED,
            error_message="Connection timeout",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db_session.add(job)
        db_session.flush()

        assert job.status == ExportStatus.FAILED
        assert job.error_message == "Connection timeout"


class TestExportStatusEnum:
    """Tests for ExportStatus and ExportFormat enums."""

    def test_status_values(self) -> None:
        assert ExportStatus.PENDING == "pending"
        assert ExportStatus.PROCESSING == "processing"
        assert ExportStatus.COMPLETED == "completed"
        assert ExportStatus.FAILED == "failed"

    def test_format_values(self) -> None:
        assert ExportFormat.CSV == "csv"
        assert ExportFormat.PDF == "pdf"

    def test_valid_report_types(self) -> None:
        expected = {"summary", "categories", "shows", "trends", "top_items", "full"}
        assert VALID_REPORT_TYPES == expected

    def test_valid_formats(self) -> None:
        assert VALID_FORMATS == {"csv", "pdf"}


# ── ExportRepository ────────────────────────────────────────────


class TestExportRepository:
    """Tests for ExportRepository."""

    def _make_job(
        self, account_id: uuid.UUID, status: str = ExportStatus.PENDING
    ) -> ExportJob:
        return ExportJob(
            account_id=account_id,
            report_type="summary",
            format="csv",
            period="30d",
            status=status,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )

    def test_create(self, db_session: Session, sample_account: Account) -> None:
        repo = ExportRepository(db_session)
        job = self._make_job(sample_account.id)
        created = repo.create(job)

        assert created.id is not None
        assert created.account_id == sample_account.id

    def test_get_by_id(self, db_session: Session, sample_account: Account) -> None:
        repo = ExportRepository(db_session)
        job = self._make_job(sample_account.id)
        repo.create(job)

        found = repo.get_by_id(job.id, sample_account.id)
        assert found is not None
        assert found.id == job.id

    def test_get_by_id_wrong_account(
        self,
        db_session: Session,
        sample_account: Account,
        other_account: Account,
    ) -> None:
        repo = ExportRepository(db_session)
        job = self._make_job(sample_account.id)
        repo.create(job)

        found = repo.get_by_id(job.id, other_account.id)
        assert found is None

    def test_get_by_id_deleted(
        self, db_session: Session, sample_account: Account
    ) -> None:
        repo = ExportRepository(db_session)
        job = self._make_job(sample_account.id)
        job.deleted_at = datetime.now(timezone.utc)
        repo.create(job)

        found = repo.get_by_id(job.id, sample_account.id)
        assert found is None

    def test_list_by_account(
        self, db_session: Session, sample_account: Account
    ) -> None:
        repo = ExportRepository(db_session)
        for _ in range(3):
            repo.create(self._make_job(sample_account.id))

        jobs = repo.list_by_account(sample_account.id)
        assert len(jobs) == 3

    def test_list_by_account_excludes_deleted(
        self, db_session: Session, sample_account: Account
    ) -> None:
        repo = ExportRepository(db_session)
        j1 = self._make_job(sample_account.id)
        repo.create(j1)
        j2 = self._make_job(sample_account.id)
        j2.deleted_at = datetime.now(timezone.utc)
        repo.create(j2)

        jobs = repo.list_by_account(sample_account.id)
        assert len(jobs) == 1

    def test_list_by_account_isolation(
        self,
        db_session: Session,
        sample_account: Account,
        other_account: Account,
    ) -> None:
        repo = ExportRepository(db_session)
        repo.create(self._make_job(sample_account.id))

        jobs = repo.list_by_account(other_account.id)
        assert len(jobs) == 0

    def test_save(self, db_session: Session, sample_account: Account) -> None:
        repo = ExportRepository(db_session)
        job = self._make_job(sample_account.id)
        repo.create(job)

        job.status = ExportStatus.COMPLETED
        updated = repo.save(job)
        assert updated.status == ExportStatus.COMPLETED

    def test_get_expired(self, db_session: Session, sample_account: Account) -> None:
        repo = ExportRepository(db_session)

        # Expired
        j1 = ExportJob(
            account_id=sample_account.id,
            report_type="summary",
            format="csv",
            period="30d",
            status=ExportStatus.COMPLETED,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        repo.create(j1)

        # Not expired
        j2 = ExportJob(
            account_id=sample_account.id,
            report_type="summary",
            format="csv",
            period="30d",
            status=ExportStatus.COMPLETED,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        repo.create(j2)

        # Pending (not completed, so not returned)
        j3 = ExportJob(
            account_id=sample_account.id,
            report_type="summary",
            format="csv",
            period="30d",
            status=ExportStatus.PENDING,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        repo.create(j3)

        expired = repo.get_expired()
        assert len(expired) == 1
        assert expired[0].id == j1.id


# ── ExportCreateSchema ──────────────────────────────────────────


class TestExportCreateSchema:
    """Tests for ExportCreateSchema."""

    def test_valid_input(self) -> None:
        schema = ExportCreateSchema()
        result = schema.load({"report_type": "summary", "format": "csv"})
        assert result["report_type"] == "summary"
        assert result["format"] == "csv"
        assert result["period"] == "30d"

    def test_valid_with_period(self) -> None:
        schema = ExportCreateSchema()
        result = schema.load({"report_type": "full", "format": "pdf", "period": "90d"})
        assert result["period"] == "90d"

    def test_invalid_report_type(self) -> None:
        schema = ExportCreateSchema()
        errors = schema.validate({"report_type": "invalid", "format": "csv"})
        assert "report_type" in errors

    def test_invalid_format(self) -> None:
        schema = ExportCreateSchema()
        errors = schema.validate({"report_type": "summary", "format": "xlsx"})
        assert "format" in errors

    def test_invalid_period(self) -> None:
        schema = ExportCreateSchema()
        errors = schema.validate({"report_type": "summary", "format": "csv", "period": "2d"})
        assert "period" in errors

    def test_missing_required_fields(self) -> None:
        schema = ExportCreateSchema()
        errors = schema.validate({})
        assert "report_type" in errors
        assert "format" in errors


class TestExportResponseSchema:
    """Tests for ExportResponseSchema."""

    def test_dump(self, db_session: Session, sample_account: Account) -> None:
        now = datetime.now(timezone.utc)
        job = ExportJob(
            account_id=sample_account.id,
            report_type="summary",
            format="csv",
            period="30d",
            status=ExportStatus.COMPLETED,
            file_size=2048,
            expires_at=now + timedelta(days=7),
        )
        db_session.add(job)
        db_session.flush()

        schema = ExportResponseSchema()
        data = schema.dump(job)
        assert data["report_type"] == "summary"
        assert data["status"] == "completed"
        assert data["file_size"] == 2048
        assert "id" in data
        assert "account_id" in data


# ── CsvExporter ─────────────────────────────────────────────────


class TestCsvExporter:
    """Tests for CsvExporter."""

    def test_export_summary_dict(self) -> None:
        exporter = CsvExporter()
        data = {"summary": {"total_revenue": 1000, "order_count": 10, "net_profit": 500}}

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="r") as f:
            tmp_path = f.name

        try:
            exporter.export(data, "summary", "30d", tmp_path)
            with open(tmp_path) as f:
                content = f.read()

            assert "Metric" in content
            assert "Value" in content
            assert "total_revenue" in content
            assert "1000" in content
        finally:
            os.unlink(tmp_path)

    def test_export_list_data(self) -> None:
        exporter = CsvExporter()
        data = {"categories": [
            {"category_name": "Electronics", "revenue": 500, "profit": 200},
            {"category_name": "Cards", "revenue": 300, "profit": 150},
        ]}

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="r") as f:
            tmp_path = f.name

        try:
            exporter.export(data, "categories", "30d", tmp_path)
            with open(tmp_path) as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            assert len(rows) == 2
            assert rows[0]["category_name"] == "Electronics"
        finally:
            os.unlink(tmp_path)

    def test_export_empty_list(self) -> None:
        exporter = CsvExporter()
        data = {"trends": []}

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="r") as f:
            tmp_path = f.name

        try:
            exporter.export(data, "trends", "30d", tmp_path)
            with open(tmp_path) as f:
                content = f.read()
            assert "No data available" in content
        finally:
            os.unlink(tmp_path)

    def test_export_full_zip(self) -> None:
        exporter = CsvExporter()
        data = {
            "summary": {"total_revenue": 1000, "order_count": 5},
            "categories": [{"name": "A", "revenue": 500}],
            "shows": [{"title": "Friday Show", "revenue": 300}],
            "trends": [{"date": "2024-01-01", "revenue": 100}],
            "top_items": [{"item_name": "Widget", "revenue": 200}],
        }

        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
            tmp_path = f.name

        try:
            exporter.export(data, "full", "30d", tmp_path)
            assert zipfile.is_zipfile(tmp_path)
            with zipfile.ZipFile(tmp_path) as zf:
                names = zf.namelist()
                assert "summary.csv" in names
                assert "categories.csv" in names
                assert "shows.csv" in names
                assert "trends.csv" in names
                assert "top_items.csv" in names
        finally:
            os.unlink(tmp_path)


# ── Chart Generation ────────────────────────────────────────────


class TestChartGeneration:
    """Tests for chart generation functions."""

    def test_trend_chart(self) -> None:
        trends = [
            {"date": "2024-01-01", "revenue": 100, "profit": 50},
            {"date": "2024-01-02", "revenue": 150, "profit": 75},
            {"date": "2024-01-03", "revenue": 120, "profit": 60},
        ]
        result = generate_trend_chart(trends)

        assert isinstance(result, bytes)
        assert len(result) > 0
        # PNG magic number
        assert result[:4] == b"\x89PNG"

    def test_trend_chart_empty(self) -> None:
        result = generate_trend_chart([])
        assert isinstance(result, bytes)
        assert result[:4] == b"\x89PNG"

    def test_trend_chart_many_points(self) -> None:
        trends = [
            {"date": f"2024-01-{i+1:02d}", "revenue": 100 + i * 10, "profit": 50 + i * 5}
            for i in range(30)
        ]
        result = generate_trend_chart(trends)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_category_chart(self) -> None:
        categories = [
            {"category_name": "Electronics", "revenue": 500, "profit": 200},
            {"category_name": "Cards", "revenue": 300, "profit": 150},
        ]
        result = generate_category_chart(categories)

        assert isinstance(result, bytes)
        assert result[:4] == b"\x89PNG"

    def test_category_chart_empty(self) -> None:
        result = generate_category_chart([])
        assert isinstance(result, bytes)
        assert result[:4] == b"\x89PNG"

    def test_top_items_chart(self) -> None:
        items = [
            {"item_name": "Widget A", "revenue": 500},
            {"item_name": "Widget B", "revenue": 300},
            {"item_name": "Very Long Item Name That Might Be Truncated", "revenue": 200},
        ]
        result = generate_top_items_chart(items)

        assert isinstance(result, bytes)
        assert result[:4] == b"\x89PNG"

    def test_top_items_chart_empty(self) -> None:
        result = generate_top_items_chart([])
        assert isinstance(result, bytes)
        assert result[:4] == b"\x89PNG"

    def test_category_chart_many_categories(self) -> None:
        # More than 10 — should only show top 10
        categories = [
            {"category_name": f"Cat {i}", "revenue": 100 - i, "profit": 50 - i}
            for i in range(15)
        ]
        result = generate_category_chart(categories)
        assert isinstance(result, bytes)
        assert len(result) > 0


# ── PDF Exporter ─────────────────────────────────────────────────


class TestPdfExporter:
    """Tests for PdfExporter."""

    def test_export_summary_pdf(self) -> None:
        from services.analytics.exporters.pdf_exporter import PdfExporter

        exporter = PdfExporter()
        data = {
            "summary": {
                "order_count": 10,
                "total_revenue": 1000.0,
                "total_cogs": 400.0,
                "total_fees": 100.0,
                "total_shipping": 50.0,
                "gross_profit": 600.0,
                "net_profit": 450.0,
                "margin_percent": 45.0,
                "average_order_value": 100.0,
                "sell_through_rate": 80.0,
            }
        }

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            tmp_path = f.name

        try:
            exporter.export(data, "summary", "30d", tmp_path)
            assert os.path.exists(tmp_path)
            assert os.path.getsize(tmp_path) > 0
            # PDF magic number
            with open(tmp_path, "rb") as f:
                assert f.read(4) == b"%PDF"
        finally:
            os.unlink(tmp_path)

    def test_export_full_pdf(self) -> None:
        from services.analytics.exporters.pdf_exporter import PdfExporter

        exporter = PdfExporter()
        data = {
            "summary": {
                "order_count": 5,
                "total_revenue": 500.0,
                "total_cogs": 200.0,
                "total_fees": 50.0,
                "total_shipping": 25.0,
                "gross_profit": 300.0,
                "net_profit": 225.0,
                "margin_percent": 45.0,
                "average_order_value": 100.0,
                "sell_through_rate": 60.0,
            },
            "categories": [
                {
                    "category_name": "Electronics",
                    "revenue": 300.0,
                    "profit": 150.0,
                    "item_count": 3,
                    "sell_through_rate": 75.0,
                },
            ],
            "shows": [
                {
                    "show_title": "Friday Night Cards",
                    "date": "2024-01-15T19:00:00",
                    "order_count": 5,
                    "revenue": 500.0,
                    "profit": 225.0,
                    "duration_minutes": 120,
                },
            ],
            "trends": [
                {"date": "2024-01-01", "revenue": 100, "profit": 50},
                {"date": "2024-01-02", "revenue": 150, "profit": 75},
            ],
            "top_items": [
                {
                    "item_name": "Widget A",
                    "category": "Electronics",
                    "quantity_sold": 3,
                    "revenue": 300.0,
                    "profit": 150.0,
                    "margin_percent": 50.0,
                },
            ],
        }

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            tmp_path = f.name

        try:
            exporter.export(data, "full", "30d", tmp_path)
            assert os.path.exists(tmp_path)
            size = os.path.getsize(tmp_path)
            assert size > 1000  # Full report should be substantial
        finally:
            os.unlink(tmp_path)

    def test_export_empty_sections(self) -> None:
        from services.analytics.exporters.pdf_exporter import PdfExporter

        exporter = PdfExporter()
        data = {
            "summary": {
                "order_count": 0,
                "total_revenue": 0,
                "total_cogs": 0,
                "total_fees": 0,
                "total_shipping": 0,
                "gross_profit": 0,
                "net_profit": 0,
                "margin_percent": 0,
                "average_order_value": 0,
                "sell_through_rate": 0,
            },
            "categories": [],
            "shows": [],
            "trends": [],
            "top_items": [],
        }

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            tmp_path = f.name

        try:
            exporter.export(data, "full", "30d", tmp_path)
            assert os.path.exists(tmp_path)
        finally:
            os.unlink(tmp_path)

    def test_export_categories_only(self) -> None:
        from services.analytics.exporters.pdf_exporter import PdfExporter

        exporter = PdfExporter()
        data = {
            "categories": [
                {
                    "category_name": "Cards",
                    "revenue": 1000.0,
                    "profit": 600.0,
                    "item_count": 10,
                    "sell_through_rate": 90.0,
                },
                {
                    "category_name": "Coins",
                    "revenue": 500.0,
                    "profit": 250.0,
                    "item_count": 5,
                    "sell_through_rate": 70.0,
                },
            ],
        }

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            tmp_path = f.name

        try:
            exporter.export(data, "categories", "7d", tmp_path)
            assert os.path.exists(tmp_path)
            assert os.path.getsize(tmp_path) > 0
        finally:
            os.unlink(tmp_path)
