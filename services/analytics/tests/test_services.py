"""Unit tests for AnalyticsService."""

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from services.analytics.services.analytics_service import AnalyticsService, DEFAULT_PERIOD
from services.auth.models.models import Account, User
from services.inventory.models.models import Category, InventoryItem, ItemStatus
from services.sales.models.models import Order, OrderStatus, Show, ShowStatus


# ── Summary ────────────────────────────────────────────────────────


class TestSummary:
    """Tests for get_summary()."""

    def test_summary_no_orders(self, db_session: Session, sample_account: Account) -> None:
        svc = AnalyticsService(db_session, sample_account.id)
        result = svc.get_summary()

        assert result["order_count"] == 0
        assert result["total_revenue"] == 0
        assert result["net_profit"] == 0
        assert result["average_order_value"] == 0
        assert result["period"] == DEFAULT_PERIOD

    def test_summary_with_orders(
        self,
        db_session: Session,
        sample_account: Account,
        sample_order: Order,
        card_order: Order,
    ) -> None:
        svc = AnalyticsService(db_session, sample_account.id)
        result = svc.get_summary()

        assert result["order_count"] == 2
        assert result["total_revenue"] == 75.00  # 25 + 50
        assert result["total_cogs"] == 13.00  # 8 + 5
        assert result["total_fees"] == 7.50  # 2.50 + 5
        assert result["total_shipping"] == 8.00  # 5 + 3
        assert result["gross_profit"] == 62.00  # 75 - 13
        expected_net = round(25.00 - 2.50 - 5.00 - 8.00 + 50.00 - 5.00 - 3.00 - 5.00, 2)
        assert result["net_profit"] == expected_net
        assert result["average_order_value"] == 37.50

    def test_summary_excludes_cancelled_orders(
        self,
        db_session: Session,
        sample_account: Account,
        sample_order: Order,
        cancelled_order: Order,
    ) -> None:
        svc = AnalyticsService(db_session, sample_account.id)
        result = svc.get_summary()

        # Cancelled order should be excluded
        assert result["order_count"] == 1
        assert result["total_revenue"] == 25.00

    def test_summary_sell_through_rate(
        self,
        db_session: Session,
        sample_account: Account,
        sample_item: InventoryItem,
        sold_item: InventoryItem,
    ) -> None:
        svc = AnalyticsService(db_session, sample_account.id)
        result = svc.get_summary()

        # 1 sold out of 2 total = 50%
        assert result["sell_through_rate"] == 50.00

    def test_summary_margin_percent(
        self,
        db_session: Session,
        sample_account: Account,
        sample_order: Order,
    ) -> None:
        svc = AnalyticsService(db_session, sample_account.id)
        result = svc.get_summary()

        expected_margin = round((result["net_profit"] / result["total_revenue"]) * 100, 2)
        assert result["margin_percent"] == expected_margin

    def test_summary_period_filter(
        self, db_session: Session, sample_account: Account, sample_order: Order
    ) -> None:
        svc = AnalyticsService(db_session, sample_account.id)
        # 7d should include recent orders
        result = svc.get_summary("7d")
        assert result["period"] == "7d"
        assert result["order_count"] == 1

    def test_summary_period_all(
        self, db_session: Session, sample_account: Account, sample_order: Order
    ) -> None:
        svc = AnalyticsService(db_session, sample_account.id)
        result = svc.get_summary("all")
        assert result["period"] == "all"
        assert result["order_count"] == 1

    def test_summary_account_isolation(
        self,
        db_session: Session,
        sample_account: Account,
        other_account: Account,
        sample_order: Order,
    ) -> None:
        svc = AnalyticsService(db_session, other_account.id)
        result = svc.get_summary()

        # Other account should see no orders
        assert result["order_count"] == 0
        assert result["total_revenue"] == 0


# ── Category Performance ───────────────────────────────────────────


class TestCategoryPerformance:
    """Tests for get_category_performance()."""

    def test_no_categories(self, db_session: Session, sample_account: Account) -> None:
        svc = AnalyticsService(db_session, sample_account.id)
        result = svc.get_category_performance()
        assert result == []

    def test_categories_with_orders(
        self,
        db_session: Session,
        sample_account: Account,
        sample_category: Category,
        second_category: Category,
        sample_order: Order,
        card_order: Order,
    ) -> None:
        svc = AnalyticsService(db_session, sample_account.id)
        result = svc.get_category_performance()

        assert len(result) == 2
        # Sorted by revenue desc — Cards (50) should be first
        assert result[0]["category_name"] == "Cards"
        assert result[0]["revenue"] == 50.00
        assert result[1]["category_name"] == "Electronics"
        assert result[1]["revenue"] == 25.00

    def test_category_sell_through(
        self,
        db_session: Session,
        sample_account: Account,
        sample_category: Category,
        sample_item: InventoryItem,  # available
        sold_item: InventoryItem,  # sold, same category
        sample_order: Order,
    ) -> None:
        svc = AnalyticsService(db_session, sample_account.id)
        result = svc.get_category_performance()

        electronics = next(r for r in result if r["category_name"] == "Electronics")
        # 1 sold out of 2 items in Electronics = 50%
        assert electronics["sell_through_rate"] == 50.00

    def test_category_account_isolation(
        self,
        db_session: Session,
        other_account: Account,
        sample_category: Category,
    ) -> None:
        svc = AnalyticsService(db_session, other_account.id)
        result = svc.get_category_performance()
        # Other account's categories only
        assert result == []


# ── Show Performance ───────────────────────────────────────────────


class TestShowPerformance:
    """Tests for get_show_performance()."""

    def test_no_shows(self, db_session: Session, sample_account: Account) -> None:
        svc = AnalyticsService(db_session, sample_account.id)
        result = svc.get_show_performance()
        assert result == []

    def test_show_with_orders(
        self,
        db_session: Session,
        sample_account: Account,
        sample_show: Show,
        sample_order: Order,
        card_order: Order,
    ) -> None:
        svc = AnalyticsService(db_session, sample_account.id)
        result = svc.get_show_performance()

        assert len(result) == 1
        show = result[0]
        assert show["show_title"] == "Friday Night Cards"
        assert show["order_count"] == 2
        assert show["revenue"] == 75.00

    def test_completed_show_duration(
        self,
        db_session: Session,
        sample_account: Account,
        completed_show: Show,
    ) -> None:
        svc = AnalyticsService(db_session, sample_account.id)
        result = svc.get_show_performance()

        show = result[0]
        assert show["duration_minutes"] is not None
        assert show["duration_minutes"] == 120.0  # 2 hours

    def test_show_without_times(
        self,
        db_session: Session,
        sample_account: Account,
        sample_show: Show,
    ) -> None:
        svc = AnalyticsService(db_session, sample_account.id)
        result = svc.get_show_performance()

        assert result[0]["duration_minutes"] is None

    def test_show_account_isolation(
        self,
        db_session: Session,
        other_account: Account,
        sample_show: Show,
    ) -> None:
        svc = AnalyticsService(db_session, other_account.id)
        result = svc.get_show_performance()
        assert result == []


# ── Top Items ──────────────────────────────────────────────────────


class TestTopItems:
    """Tests for get_top_items()."""

    def test_no_orders(self, db_session: Session, sample_account: Account) -> None:
        svc = AnalyticsService(db_session, sample_account.id)
        result = svc.get_top_items()
        assert result == []

    def test_top_items_default_sort(
        self,
        db_session: Session,
        sample_account: Account,
        sample_order: Order,
        card_order: Order,
    ) -> None:
        svc = AnalyticsService(db_session, sample_account.id)
        result = svc.get_top_items()

        assert len(result) == 2
        # Default sort by revenue — card (50) first
        assert result[0]["item_name"] == "Rare Card"
        assert result[0]["revenue"] == 50.00
        assert result[1]["item_name"] == "Sold Widget"
        assert result[1]["revenue"] == 25.00

    def test_top_items_sort_by_profit(
        self,
        db_session: Session,
        sample_account: Account,
        sample_order: Order,
        card_order: Order,
    ) -> None:
        svc = AnalyticsService(db_session, sample_account.id)
        result = svc.get_top_items(sort_by="profit")

        assert len(result) == 2
        # Card profit = 50 - 5 - 3 - 5 = 37, Widget profit = 25 - 2.5 - 5 - 8 = 9.5
        assert result[0]["item_name"] == "Rare Card"

    def test_top_items_limit(
        self,
        db_session: Session,
        sample_account: Account,
        sample_order: Order,
        card_order: Order,
    ) -> None:
        svc = AnalyticsService(db_session, sample_account.id)
        result = svc.get_top_items(limit=1)
        assert len(result) == 1

    def test_top_items_includes_category(
        self,
        db_session: Session,
        sample_account: Account,
        sample_order: Order,
    ) -> None:
        svc = AnalyticsService(db_session, sample_account.id)
        result = svc.get_top_items()

        assert result[0]["category"] == "Electronics"

    def test_top_items_margin_percent(
        self,
        db_session: Session,
        sample_account: Account,
        sample_order: Order,
    ) -> None:
        svc = AnalyticsService(db_session, sample_account.id)
        result = svc.get_top_items()

        item = result[0]
        expected = round((item["profit"] / item["revenue"]) * 100, 2)
        assert item["margin_percent"] == expected

    def test_top_items_excludes_cancelled(
        self,
        db_session: Session,
        sample_account: Account,
        sample_order: Order,
        cancelled_order: Order,
    ) -> None:
        svc = AnalyticsService(db_session, sample_account.id)
        result = svc.get_top_items()

        # Only the non-cancelled order
        assert len(result) == 1


# ── Trends ─────────────────────────────────────────────────────────


class TestTrends:
    """Tests for get_trends()."""

    def test_trends_daily(
        self,
        db_session: Session,
        sample_account: Account,
        sample_order: Order,
    ) -> None:
        svc = AnalyticsService(db_session, sample_account.id)
        result = svc.get_trends("7d", "day")

        assert isinstance(result, list)
        assert len(result) >= 1
        # At least one bucket should have our order
        total_revenue = sum(b["revenue"] for b in result)
        assert total_revenue == 25.00

    def test_trends_weekly(
        self,
        db_session: Session,
        sample_account: Account,
        sample_order: Order,
    ) -> None:
        svc = AnalyticsService(db_session, sample_account.id)
        result = svc.get_trends("30d", "week")

        assert isinstance(result, list)
        total_revenue = sum(b["revenue"] for b in result)
        assert total_revenue == 25.00

    def test_trends_monthly(
        self,
        db_session: Session,
        sample_account: Account,
        sample_order: Order,
    ) -> None:
        svc = AnalyticsService(db_session, sample_account.id)
        result = svc.get_trends("90d", "month")

        assert isinstance(result, list)
        total_revenue = sum(b["revenue"] for b in result)
        assert total_revenue == 25.00

    def test_trends_all_period(
        self,
        db_session: Session,
        sample_account: Account,
        sample_order: Order,
    ) -> None:
        svc = AnalyticsService(db_session, sample_account.id)
        result = svc.get_trends("all", "month")
        total_revenue = sum(b["revenue"] for b in result)
        assert total_revenue == 25.00

    def test_trends_empty(self, db_session: Session, sample_account: Account) -> None:
        svc = AnalyticsService(db_session, sample_account.id)
        result = svc.get_trends("7d")
        total_revenue = sum(b["revenue"] for b in result)
        assert total_revenue == 0


# ── Caching ────────────────────────────────────────────────────────


class TestCaching:
    """Tests for Redis caching behaviour."""

    def test_cache_hit(
        self, db_session: Session, sample_account: Account, sample_order: Order
    ) -> None:
        mock_redis = MagicMock()
        cached_data = json.dumps({"order_count": 999, "cached": True})
        mock_redis.get.return_value = cached_data

        svc = AnalyticsService(db_session, sample_account.id, redis_client=mock_redis)
        result = svc.get_summary()

        assert result["cached"] is True
        assert result["order_count"] == 999
        mock_redis.get.assert_called_once()

    def test_cache_miss_then_set(
        self, db_session: Session, sample_account: Account, sample_order: Order
    ) -> None:
        mock_redis = MagicMock()
        mock_redis.get.return_value = None

        svc = AnalyticsService(db_session, sample_account.id, redis_client=mock_redis, cache_ttl=60)
        result = svc.get_summary()

        assert result["order_count"] == 1
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 60  # TTL

    def test_cache_error_graceful(
        self, db_session: Session, sample_account: Account, sample_order: Order
    ) -> None:
        mock_redis = MagicMock()
        mock_redis.get.side_effect = ConnectionError("Redis down")

        svc = AnalyticsService(db_session, sample_account.id, redis_client=mock_redis)
        # Should not raise, falls through to DB
        result = svc.get_summary()
        assert result["order_count"] == 1

    def test_cache_write_error_graceful(
        self, db_session: Session, sample_account: Account, sample_order: Order
    ) -> None:
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        mock_redis.setex.side_effect = ConnectionError("Redis down")

        svc = AnalyticsService(db_session, sample_account.id, redis_client=mock_redis)
        result = svc.get_summary()
        assert result["order_count"] == 1

    def test_no_cache_without_redis(
        self, db_session: Session, sample_account: Account, sample_order: Order
    ) -> None:
        svc = AnalyticsService(db_session, sample_account.id, redis_client=None)
        result = svc.get_summary()
        assert result["order_count"] == 1
