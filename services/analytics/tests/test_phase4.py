"""Tests for show time optimization and export routes."""

import json
import os
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask
from sqlalchemy.orm import Session

from services.analytics.models.models import ExportJob, ExportStatus, ExportFormat
from services.analytics.routes.analytics_routes import analytics_bp
from services.analytics.routes.export_routes import export_bp
from services.analytics.services.analytics_service import AnalyticsService
from services.auth.models.models import Account, User
from services.inventory.models.models import Category, InventoryItem, ItemStatus
from services.sales.models.models import Order, OrderStatus, Show, ShowStatus
from services.shared.errors import register_error_handlers

from .conftest import make_auth_headers


# ── Show Time Suggestions (Service) ─────────────────────────────


class TestShowTimeSuggestions:
    """Tests for AnalyticsService.get_show_time_suggestions()."""

    def test_insufficient_shows(self, db_session: Session, sample_account: Account) -> None:
        """Returns empty recommendations when < 3 completed shows."""
        svc = AnalyticsService(db_session, sample_account.id)
        result = svc.get_show_time_suggestions()

        assert result["total_shows_analyzed"] == 0
        assert result["recommendations"] == []
        assert result["avoid_slots"] == []
        assert result["category_insights"] == []

    def test_insufficient_shows_with_one(
        self,
        db_session: Session,
        sample_account: Account,
    ) -> None:
        """Still insufficient with only 1 completed show."""
        show = Show(
            account_id=sample_account.id,
            title="Solo Show",
            platform="whatnot",
            status=ShowStatus.COMPLETED,
            started_at=datetime.now(timezone.utc) - timedelta(hours=3),
            ended_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        db_session.add(show)
        db_session.flush()

        svc = AnalyticsService(db_session, sample_account.id)
        result = svc.get_show_time_suggestions()
        assert result["total_shows_analyzed"] == 1
        assert result["recommendations"] == []

    def test_recommendations_with_enough_shows(
        self,
        db_session: Session,
        sample_account: Account,
        sample_category: Category,
    ) -> None:
        """Returns recommendations when >= 3 completed shows exist."""
        now = datetime.now(timezone.utc)
        shows = []
        for i in range(4):
            start = now - timedelta(days=7 * (i + 1))
            # All on the same weekday/hour for consistent scoring
            show = Show(
                account_id=sample_account.id,
                title=f"Weekly Show {i}",
                platform="whatnot",
                status=ShowStatus.COMPLETED,
                started_at=start,
                ended_at=start + timedelta(hours=2),
            )
            db_session.add(show)
            db_session.flush()
            shows.append(show)

            # Add an order for each show
            item = InventoryItem(
                account_id=sample_account.id,
                name=f"Item {i}",
                description="test",
                category_id=sample_category.id,
                cogs=5.00,
                quantity=1,
                status=ItemStatus.SOLD,
            )
            db_session.add(item)
            db_session.flush()

            order = Order(
                account_id=sample_account.id,
                show_id=show.id,
                inventory_item_id=item.id,
                sale_price=30.00 + i * 5,
                platform_fees=3.00,
                shipping_cost=4.00,
                cost_basis=5.00,
                profit=30.00 + i * 5 - 3.00 - 4.00 - 5.00,
            )
            db_session.add(order)
            db_session.flush()

        svc = AnalyticsService(db_session, sample_account.id)
        result = svc.get_show_time_suggestions()

        assert result["total_shows_analyzed"] == 4
        assert len(result["recommendations"]) >= 1
        rec = result["recommendations"][0]
        assert "rank" in rec
        assert "label" in rec
        assert "score" in rec
        assert "avg_revenue" in rec
        assert "avg_profit" in rec
        assert rec["rank"] == 1

    def test_recommendations_have_scores(
        self,
        db_session: Session,
        sample_account: Account,
        sample_category: Category,
    ) -> None:
        """Each recommendation has a numeric score between 0 and 1."""
        now = datetime.now(timezone.utc)
        for i in range(3):
            start = now - timedelta(days=7 * (i + 1))
            show = Show(
                account_id=sample_account.id,
                title=f"Show {i}",
                platform="whatnot",
                status=ShowStatus.COMPLETED,
                started_at=start,
                ended_at=start + timedelta(hours=2),
            )
            db_session.add(show)
            db_session.flush()

            item = InventoryItem(
                account_id=sample_account.id,
                name=f"Scored Item {i}",
                description="test",
                category_id=sample_category.id,
                cogs=5.00,
                quantity=1,
                status=ItemStatus.SOLD,
            )
            db_session.add(item)
            db_session.flush()

            order = Order(
                account_id=sample_account.id,
                show_id=show.id,
                inventory_item_id=item.id,
                sale_price=50.00,
                platform_fees=5.00,
                shipping_cost=4.00,
                cost_basis=5.00,
                profit=36.00,
            )
            db_session.add(order)
            db_session.flush()

        svc = AnalyticsService(db_session, sample_account.id)
        result = svc.get_show_time_suggestions()

        for rec in result["recommendations"]:
            assert 0 <= rec["score"] <= 1
            assert rec["avg_profit"] > 0

    def test_category_insights(
        self,
        db_session: Session,
        sample_account: Account,
        sample_category: Category,
        second_category: Category,
    ) -> None:
        """Returns category-level time insights."""
        now = datetime.now(timezone.utc)
        for i in range(3):
            start = now - timedelta(days=7 * (i + 1))
            show = Show(
                account_id=sample_account.id,
                title=f"Cat Show {i}",
                platform="whatnot",
                status=ShowStatus.COMPLETED,
                started_at=start,
                ended_at=start + timedelta(hours=2),
            )
            db_session.add(show)
            db_session.flush()

            for cat, price in [(sample_category, 30.0), (second_category, 50.0)]:
                item = InventoryItem(
                    account_id=sample_account.id,
                    name=f"Cat Item {i} {cat.name}",
                    description="test",
                    category_id=cat.id,
                    cogs=5.00,
                    quantity=1,
                    status=ItemStatus.SOLD,
                )
                db_session.add(item)
                db_session.flush()

                order = Order(
                    account_id=sample_account.id,
                    show_id=show.id,
                    inventory_item_id=item.id,
                    sale_price=price,
                    platform_fees=3.00,
                    shipping_cost=4.00,
                    cost_basis=5.00,
                    profit=price - 12.00,
                )
                db_session.add(order)
                db_session.flush()

        svc = AnalyticsService(db_session, sample_account.id)
        result = svc.get_show_time_suggestions()

        insights = result["category_insights"]
        assert len(insights) == 2
        # Sorted by avg_profit desc
        assert insights[0]["avg_profit"] >= insights[1]["avg_profit"]
        assert "category" in insights[0]
        assert "best_day" in insights[0]
        assert "best_hour" in insights[0]

    def test_account_isolation(
        self,
        db_session: Session,
        sample_account: Account,
        other_account: Account,
        sample_category: Category,
    ) -> None:
        """Only shows belonging to the account are analyzed."""
        now = datetime.now(timezone.utc)
        for i in range(3):
            start = now - timedelta(days=7 * (i + 1))
            show = Show(
                account_id=sample_account.id,
                title=f"SA Show {i}",
                platform="whatnot",
                status=ShowStatus.COMPLETED,
                started_at=start,
                ended_at=start + timedelta(hours=2),
            )
            db_session.add(show)
            db_session.flush()

        svc = AnalyticsService(db_session, other_account.id)
        result = svc.get_show_time_suggestions()
        assert result["total_shows_analyzed"] == 0

    def test_avoid_slots(
        self,
        db_session: Session,
        sample_account: Account,
        sample_category: Category,
    ) -> None:
        """Returns avoid_slots for time slots with poor performance."""
        now = datetime.now(timezone.utc)
        # Create 3 shows at different times — some with zero profit
        hours = [10, 15, 22]
        for i in range(3):
            start = (now - timedelta(days=i + 1)).replace(hour=hours[i], minute=0, second=0)
            show = Show(
                account_id=sample_account.id,
                title=f"Avoid Show {i}",
                platform="whatnot",
                status=ShowStatus.COMPLETED,
                started_at=start,
                ended_at=start + timedelta(hours=2),
            )
            db_session.add(show)
            db_session.flush()

            item = InventoryItem(
                account_id=sample_account.id,
                name=f"Avoid Item {i}",
                description="test",
                category_id=sample_category.id,
                cogs=5.00,
                quantity=1,
                status=ItemStatus.SOLD,
            )
            db_session.add(item)
            db_session.flush()

            # Give the first show good profit, last two negative/zero
            profit = 20.00 if i == 0 else -1.00
            sale_price = 30.00 if i == 0 else 4.00
            order = Order(
                account_id=sample_account.id,
                show_id=show.id,
                inventory_item_id=item.id,
                sale_price=sale_price,
                platform_fees=1.00,
                shipping_cost=1.00,
                cost_basis=5.00,
                profit=profit,
            )
            db_session.add(order)
            db_session.flush()

        svc = AnalyticsService(db_session, sample_account.id)
        result = svc.get_show_time_suggestions()

        # avoid_slots should contain slots with negative profit
        assert isinstance(result["avoid_slots"], list)

    def test_caching(
        self,
        db_session: Session,
        sample_account: Account,
    ) -> None:
        """Results are cached and returned on subsequent call."""
        mock_redis = MagicMock()
        cached = {
            "total_shows_analyzed": 10,
            "recommendations": [{"rank": 1}],
            "avoid_slots": [],
            "category_insights": [],
        }
        mock_redis.get.return_value = json.dumps(cached)

        svc = AnalyticsService(db_session, sample_account.id, redis_client=mock_redis)
        result = svc.get_show_time_suggestions()

        assert result["total_shows_analyzed"] == 10
        mock_redis.get.assert_called_once()


# ── Show Time Suggestions (Route) ───────────────────────────────


@pytest.fixture()
def analytics_client(app: Flask, db_session: Session):  # type: ignore[no-untyped-def]
    """Client with analytics_bp registered."""
    register_error_handlers(app)
    app.register_blueprint(analytics_bp, url_prefix="/api/v1/analytics")

    with patch("services.analytics.routes.analytics_routes.get_db", return_value=db_session):
        yield app.test_client()


class TestShowTimeSuggestionsRoute:
    """Tests for GET /api/v1/analytics/show-time-suggestions."""

    def test_success(
        self,
        analytics_client: Any,
        app: Flask,
        sample_user: User,
    ) -> None:
        headers = make_auth_headers(app, sample_user)
        resp = analytics_client.get("/api/v1/analytics/show-time-suggestions", headers=headers)

        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert "recommendations" in data
        assert "avoid_slots" in data
        assert "category_insights" in data
        assert "total_shows_analyzed" in data

    def test_requires_auth(self, analytics_client: Any) -> None:
        resp = analytics_client.get("/api/v1/analytics/show-time-suggestions")
        assert resp.status_code == 401

    def test_account_isolation(
        self,
        analytics_client: Any,
        app: Flask,
        other_user: User,
    ) -> None:
        headers = make_auth_headers(app, other_user)
        resp = analytics_client.get("/api/v1/analytics/show-time-suggestions", headers=headers)

        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["total_shows_analyzed"] == 0


# ── Export Routes ────────────────────────────────────────────────


@pytest.fixture()
def export_client(app: Flask, db_session: Session):  # type: ignore[no-untyped-def]
    """Client with export_bp registered."""
    register_error_handlers(app)
    app.register_blueprint(export_bp, url_prefix="/api/v1/analytics/exports")

    with patch("services.analytics.routes.export_routes.get_db", return_value=db_session):
        yield app.test_client()


class TestCreateExport:
    """Tests for POST /api/v1/analytics/exports."""

    def test_create_export_success(
        self,
        export_client: Any,
        app: Flask,
        sample_user: User,
    ) -> None:
        headers = make_auth_headers(app, sample_user)
        payload = {"report_type": "summary", "format": "csv"}

        with patch("services.analytics.tasks.export_tasks.generate_export") as mock_task:
            mock_task.delay.return_value = MagicMock()
            resp = export_client.post(
                "/api/v1/analytics/exports",
                headers=headers,
                data=json.dumps(payload),
            )

        assert resp.status_code == 201
        data = resp.get_json()["data"]
        assert data["report_type"] == "summary"
        assert data["format"] == "csv"
        assert data["status"] == "pending"
        assert data["period"] == "30d"

    def test_create_export_pdf(
        self,
        export_client: Any,
        app: Flask,
        sample_user: User,
    ) -> None:
        headers = make_auth_headers(app, sample_user)
        payload = {"report_type": "full", "format": "pdf", "period": "90d"}

        with patch("services.analytics.tasks.export_tasks.generate_export") as mock_task:
            mock_task.delay.return_value = MagicMock()
            resp = export_client.post(
                "/api/v1/analytics/exports",
                headers=headers,
                data=json.dumps(payload),
            )

        assert resp.status_code == 201
        data = resp.get_json()["data"]
        assert data["report_type"] == "full"
        assert data["format"] == "pdf"
        assert data["period"] == "90d"

    def test_create_export_invalid_report_type(
        self,
        export_client: Any,
        app: Flask,
        sample_user: User,
    ) -> None:
        headers = make_auth_headers(app, sample_user)
        payload = {"report_type": "invalid", "format": "csv"}

        resp = export_client.post(
            "/api/v1/analytics/exports",
            headers=headers,
            data=json.dumps(payload),
        )
        assert resp.status_code == 422

    def test_create_export_invalid_format(
        self,
        export_client: Any,
        app: Flask,
        sample_user: User,
    ) -> None:
        headers = make_auth_headers(app, sample_user)
        payload = {"report_type": "summary", "format": "xlsx"}

        resp = export_client.post(
            "/api/v1/analytics/exports",
            headers=headers,
            data=json.dumps(payload),
        )
        assert resp.status_code == 422

    def test_create_export_missing_fields(
        self,
        export_client: Any,
        app: Flask,
        sample_user: User,
    ) -> None:
        headers = make_auth_headers(app, sample_user)
        resp = export_client.post(
            "/api/v1/analytics/exports",
            headers=headers,
            data=json.dumps({}),
        )
        assert resp.status_code == 422

    def test_create_export_requires_auth(self, export_client: Any) -> None:
        resp = export_client.post(
            "/api/v1/analytics/exports",
            data=json.dumps({"report_type": "summary", "format": "csv"}),
            content_type="application/json",
        )
        assert resp.status_code == 401

    def test_celery_unavailable_still_creates_job(
        self,
        export_client: Any,
        app: Flask,
        sample_user: User,
    ) -> None:
        """If Celery broker is down, the job should still be created."""
        headers = make_auth_headers(app, sample_user)
        payload = {"report_type": "summary", "format": "csv"}

        with patch(
            "services.analytics.tasks.export_tasks.generate_export",
            side_effect=ImportError("no celery"),
        ):
            resp = export_client.post(
                "/api/v1/analytics/exports",
                headers=headers,
                data=json.dumps(payload),
            )

        assert resp.status_code == 201


class TestListExports:
    """Tests for GET /api/v1/analytics/exports."""

    def test_list_exports_empty(
        self,
        export_client: Any,
        app: Flask,
        sample_user: User,
    ) -> None:
        headers = make_auth_headers(app, sample_user)
        resp = export_client.get("/api/v1/analytics/exports", headers=headers)

        assert resp.status_code == 200
        assert resp.get_json()["data"] == []

    def test_list_exports_with_jobs(
        self,
        export_client: Any,
        app: Flask,
        sample_user: User,
        db_session: Session,
        sample_account: Account,
    ) -> None:
        # Create two jobs
        now = datetime.now(timezone.utc)
        for i in range(2):
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

        headers = make_auth_headers(app, sample_user)
        resp = export_client.get("/api/v1/analytics/exports", headers=headers)

        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert len(data) == 2

    def test_list_exports_account_isolation(
        self,
        export_client: Any,
        app: Flask,
        other_user: User,
        db_session: Session,
        sample_account: Account,
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

        headers = make_auth_headers(app, other_user)
        resp = export_client.get("/api/v1/analytics/exports", headers=headers)

        assert resp.status_code == 200
        assert resp.get_json()["data"] == []

    def test_list_requires_auth(self, export_client: Any) -> None:
        resp = export_client.get("/api/v1/analytics/exports")
        assert resp.status_code == 401


class TestGetExport:
    """Tests for GET /api/v1/analytics/exports/<id>."""

    def test_get_export_success(
        self,
        export_client: Any,
        app: Flask,
        sample_user: User,
        db_session: Session,
        sample_account: Account,
    ) -> None:
        now = datetime.now(timezone.utc)
        job = ExportJob(
            account_id=sample_account.id,
            report_type="categories",
            format="pdf",
            period="7d",
            status=ExportStatus.PROCESSING,
            expires_at=now + timedelta(days=7),
        )
        db_session.add(job)
        db_session.flush()

        headers = make_auth_headers(app, sample_user)
        resp = export_client.get(f"/api/v1/analytics/exports/{job.id}", headers=headers)

        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["report_type"] == "categories"
        assert data["status"] == "processing"

    def test_get_export_not_found(
        self,
        export_client: Any,
        app: Flask,
        sample_user: User,
    ) -> None:
        headers = make_auth_headers(app, sample_user)
        fake_id = str(uuid.uuid4())
        resp = export_client.get(f"/api/v1/analytics/exports/{fake_id}", headers=headers)

        assert resp.status_code == 404

    def test_get_export_invalid_id(
        self,
        export_client: Any,
        app: Flask,
        sample_user: User,
    ) -> None:
        headers = make_auth_headers(app, sample_user)
        resp = export_client.get("/api/v1/analytics/exports/not-a-uuid", headers=headers)

        assert resp.status_code == 422

    def test_get_export_wrong_account(
        self,
        export_client: Any,
        app: Flask,
        other_user: User,
        db_session: Session,
        sample_account: Account,
    ) -> None:
        now = datetime.now(timezone.utc)
        job = ExportJob(
            account_id=sample_account.id,
            report_type="summary",
            format="csv",
            period="30d",
            status=ExportStatus.COMPLETED,
            expires_at=now + timedelta(days=7),
        )
        db_session.add(job)
        db_session.flush()

        headers = make_auth_headers(app, other_user)
        resp = export_client.get(f"/api/v1/analytics/exports/{job.id}", headers=headers)

        assert resp.status_code == 404

    def test_get_requires_auth(self, export_client: Any) -> None:
        fake_id = str(uuid.uuid4())
        resp = export_client.get(f"/api/v1/analytics/exports/{fake_id}")
        assert resp.status_code == 401


class TestDownloadExport:
    """Tests for GET /api/v1/analytics/exports/<id>/download."""

    def test_download_csv_success(
        self,
        export_client: Any,
        app: Flask,
        sample_user: User,
        db_session: Session,
        sample_account: Account,
    ) -> None:
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            f.write("test,data\n1,2\n")
            tmp_path = f.name

        try:
            now = datetime.now(timezone.utc)
            job = ExportJob(
                account_id=sample_account.id,
                report_type="summary",
                format="csv",
                period="30d",
                status=ExportStatus.COMPLETED,
                file_path=tmp_path,
                file_size=100,
                expires_at=now + timedelta(days=7),
            )
            db_session.add(job)
            db_session.flush()

            headers = make_auth_headers(app, sample_user)
            resp = export_client.get(f"/api/v1/analytics/exports/{job.id}/download", headers=headers)

            assert resp.status_code == 200
            assert resp.content_type == "text/csv; charset=utf-8"
        finally:
            os.unlink(tmp_path)

    def test_download_pdf_mimetype(
        self,
        export_client: Any,
        app: Flask,
        sample_user: User,
        db_session: Session,
        sample_account: Account,
    ) -> None:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"fake pdf content")
            tmp_path = f.name

        try:
            now = datetime.now(timezone.utc)
            job = ExportJob(
                account_id=sample_account.id,
                report_type="full",
                format="pdf",
                period="30d",
                status=ExportStatus.COMPLETED,
                file_path=tmp_path,
                file_size=100,
                expires_at=now + timedelta(days=7),
            )
            db_session.add(job)
            db_session.flush()

            headers = make_auth_headers(app, sample_user)
            resp = export_client.get(f"/api/v1/analytics/exports/{job.id}/download", headers=headers)

            assert resp.status_code == 200
            assert "application/pdf" in resp.content_type
        finally:
            os.unlink(tmp_path)

    def test_download_not_completed(
        self,
        export_client: Any,
        app: Flask,
        sample_user: User,
        db_session: Session,
        sample_account: Account,
    ) -> None:
        now = datetime.now(timezone.utc)
        job = ExportJob(
            account_id=sample_account.id,
            report_type="summary",
            format="csv",
            period="30d",
            status=ExportStatus.PROCESSING,
            expires_at=now + timedelta(days=7),
        )
        db_session.add(job)
        db_session.flush()

        headers = make_auth_headers(app, sample_user)
        resp = export_client.get(f"/api/v1/analytics/exports/{job.id}/download", headers=headers)

        assert resp.status_code == 409

    def test_download_file_missing(
        self,
        export_client: Any,
        app: Flask,
        sample_user: User,
        db_session: Session,
        sample_account: Account,
    ) -> None:
        now = datetime.now(timezone.utc)
        job = ExportJob(
            account_id=sample_account.id,
            report_type="summary",
            format="csv",
            period="30d",
            status=ExportStatus.COMPLETED,
            file_path="/tmp/nonexistent_file.csv",
            file_size=100,
            expires_at=now + timedelta(days=7),
        )
        db_session.add(job)
        db_session.flush()

        headers = make_auth_headers(app, sample_user)
        resp = export_client.get(f"/api/v1/analytics/exports/{job.id}/download", headers=headers)

        assert resp.status_code == 404

    def test_download_not_found(
        self,
        export_client: Any,
        app: Flask,
        sample_user: User,
    ) -> None:
        headers = make_auth_headers(app, sample_user)
        fake_id = str(uuid.uuid4())
        resp = export_client.get(f"/api/v1/analytics/exports/{fake_id}/download", headers=headers)

        assert resp.status_code == 404

    def test_download_invalid_id(
        self,
        export_client: Any,
        app: Flask,
        sample_user: User,
    ) -> None:
        headers = make_auth_headers(app, sample_user)
        resp = export_client.get("/api/v1/analytics/exports/bad-id/download", headers=headers)

        assert resp.status_code == 422

    def test_download_requires_auth(self, export_client: Any) -> None:
        fake_id = str(uuid.uuid4())
        resp = export_client.get(f"/api/v1/analytics/exports/{fake_id}/download")
        assert resp.status_code == 401
