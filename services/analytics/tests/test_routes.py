"""Integration tests for analytics routes."""

import uuid
from typing import Any
from unittest.mock import patch

import pytest
from flask import Flask
from sqlalchemy.orm import Session

from services.analytics.routes.analytics_routes import analytics_bp
from services.auth.models.models import Account, User
from services.inventory.models.models import Category, InventoryItem
from services.sales.models.models import Order, Show
from services.shared.errors import register_error_handlers

from .conftest import make_auth_headers


@pytest.fixture()
def client(app: Flask, db_session: Session):  # type: ignore[no-untyped-def]
    """Create a test client with analytics routes registered."""
    register_error_handlers(app)
    app.register_blueprint(analytics_bp, url_prefix="/api/v1/analytics")

    with patch("services.analytics.routes.analytics_routes.get_db", return_value=db_session):
        yield app.test_client()


# ── Summary Endpoint ───────────────────────────────────────────────


class TestSummaryEndpoint:
    """Tests for GET /api/v1/analytics/summary."""

    def test_summary_success(
        self,
        client: Any,
        app: Flask,
        sample_user: User,
        sample_order: Order,
    ) -> None:
        headers = make_auth_headers(app, sample_user)
        resp = client.get("/api/v1/analytics/summary", headers=headers)

        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["order_count"] == 1
        assert data["total_revenue"] == 25.00

    def test_summary_with_period(
        self,
        client: Any,
        app: Flask,
        sample_user: User,
        sample_order: Order,
    ) -> None:
        headers = make_auth_headers(app, sample_user)
        resp = client.get("/api/v1/analytics/summary?period=7d", headers=headers)

        assert resp.status_code == 200
        assert resp.get_json()["data"]["period"] == "7d"

    def test_summary_invalid_period(
        self,
        client: Any,
        app: Flask,
        sample_user: User,
    ) -> None:
        headers = make_auth_headers(app, sample_user)
        resp = client.get("/api/v1/analytics/summary?period=2d", headers=headers)

        assert resp.status_code == 422

    def test_summary_requires_auth(self, client: Any) -> None:
        resp = client.get("/api/v1/analytics/summary")
        assert resp.status_code == 401

    def test_summary_account_isolation(
        self,
        client: Any,
        app: Flask,
        other_user: User,
        sample_order: Order,
    ) -> None:
        headers = make_auth_headers(app, other_user)
        resp = client.get("/api/v1/analytics/summary", headers=headers)

        assert resp.status_code == 200
        assert resp.get_json()["data"]["order_count"] == 0


# ── Categories Endpoint ────────────────────────────────────────────


class TestCategoriesEndpoint:
    """Tests for GET /api/v1/analytics/categories."""

    def test_categories_success(
        self,
        client: Any,
        app: Flask,
        sample_user: User,
        sample_category: Category,
        sample_order: Order,
    ) -> None:
        headers = make_auth_headers(app, sample_user)
        resp = client.get("/api/v1/analytics/categories", headers=headers)

        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_categories_with_period(
        self,
        client: Any,
        app: Flask,
        sample_user: User,
        sample_category: Category,
    ) -> None:
        headers = make_auth_headers(app, sample_user)
        resp = client.get("/api/v1/analytics/categories?period=90d", headers=headers)

        assert resp.status_code == 200

    def test_categories_requires_auth(self, client: Any) -> None:
        resp = client.get("/api/v1/analytics/categories")
        assert resp.status_code == 401


# ── Shows Endpoint ─────────────────────────────────────────────────


class TestShowsEndpoint:
    """Tests for GET /api/v1/analytics/shows."""

    def test_shows_success(
        self,
        client: Any,
        app: Flask,
        sample_user: User,
        sample_show: Show,
        sample_order: Order,
    ) -> None:
        headers = make_auth_headers(app, sample_user)
        resp = client.get("/api/v1/analytics/shows", headers=headers)

        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_shows_requires_auth(self, client: Any) -> None:
        resp = client.get("/api/v1/analytics/shows")
        assert resp.status_code == 401


# ── Trends Endpoint ────────────────────────────────────────────────


class TestTrendsEndpoint:
    """Tests for GET /api/v1/analytics/trends."""

    def test_trends_success(
        self,
        client: Any,
        app: Flask,
        sample_user: User,
        sample_order: Order,
    ) -> None:
        headers = make_auth_headers(app, sample_user)
        resp = client.get("/api/v1/analytics/trends", headers=headers)

        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert isinstance(data, list)

    def test_trends_with_granularity(
        self,
        client: Any,
        app: Flask,
        sample_user: User,
        sample_order: Order,
    ) -> None:
        headers = make_auth_headers(app, sample_user)
        resp = client.get("/api/v1/analytics/trends?granularity=week", headers=headers)

        assert resp.status_code == 200

    def test_trends_invalid_granularity(
        self,
        client: Any,
        app: Flask,
        sample_user: User,
    ) -> None:
        headers = make_auth_headers(app, sample_user)
        resp = client.get("/api/v1/analytics/trends?granularity=hour", headers=headers)

        assert resp.status_code == 422

    def test_trends_requires_auth(self, client: Any) -> None:
        resp = client.get("/api/v1/analytics/trends")
        assert resp.status_code == 401


# ── Top Items Endpoint ─────────────────────────────────────────────


class TestTopItemsEndpoint:
    """Tests for GET /api/v1/analytics/top-items."""

    def test_top_items_success(
        self,
        client: Any,
        app: Flask,
        sample_user: User,
        sample_order: Order,
    ) -> None:
        headers = make_auth_headers(app, sample_user)
        resp = client.get("/api/v1/analytics/top-items", headers=headers)

        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert isinstance(data, list)
        assert len(data) == 1

    def test_top_items_sort_by(
        self,
        client: Any,
        app: Flask,
        sample_user: User,
        sample_order: Order,
    ) -> None:
        headers = make_auth_headers(app, sample_user)
        resp = client.get("/api/v1/analytics/top-items?sort_by=profit", headers=headers)

        assert resp.status_code == 200

    def test_top_items_invalid_sort_by(
        self,
        client: Any,
        app: Flask,
        sample_user: User,
    ) -> None:
        headers = make_auth_headers(app, sample_user)
        resp = client.get("/api/v1/analytics/top-items?sort_by=foo", headers=headers)

        assert resp.status_code == 422

    def test_top_items_limit(
        self,
        client: Any,
        app: Flask,
        sample_user: User,
        sample_order: Order,
        card_order: Order,
    ) -> None:
        headers = make_auth_headers(app, sample_user)
        resp = client.get("/api/v1/analytics/top-items?limit=1", headers=headers)

        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert len(data) == 1

    def test_top_items_invalid_limit(
        self,
        client: Any,
        app: Flask,
        sample_user: User,
    ) -> None:
        headers = make_auth_headers(app, sample_user)
        resp = client.get("/api/v1/analytics/top-items?limit=0", headers=headers)

        assert resp.status_code == 422

    def test_top_items_requires_auth(self, client: Any) -> None:
        resp = client.get("/api/v1/analytics/top-items")
        assert resp.status_code == 401
