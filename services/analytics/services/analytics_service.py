"""Analytics service layer — revenue, profit, category, show, and trend analysis."""

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select, case, extract
from sqlalchemy.orm import Session

from services.inventory.models.models import Category, InventoryItem
from services.sales.models.models import Order, OrderStatus, Show
from services.shared.logging import get_logger

logger = get_logger("analytics_service")

# Supported period values and their timedelta
PERIOD_MAP: dict[str, timedelta | None] = {
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "90d": timedelta(days=90),
    "365d": timedelta(days=365),
    "all": None,
}

DEFAULT_PERIOD = "30d"


class AnalyticsService:
    """Read-only analytics with optional Redis caching."""

    def __init__(
        self,
        db: Session,
        account_id: uuid.UUID,
        *,
        redis_client: Any = None,
        cache_ttl: int = 300,
    ) -> None:
        self.db = db
        self.account_id = account_id
        self.redis = redis_client
        self.cache_ttl = cache_ttl

    # ── Revenue Summary ─────────────────────────────────────────────

    def get_summary(self, period: str = DEFAULT_PERIOD) -> dict[str, Any]:
        """Get aggregated revenue and profit summary."""
        cache_key = f"analytics:{self.account_id}:summary:{period}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        cutoff = self._get_cutoff(period)
        filters = self._base_order_filters(cutoff)

        row = self.db.execute(
            select(
                func.coalesce(func.count(Order.id), 0).label("order_count"),
                func.coalesce(func.sum(Order.sale_price), 0).label("total_revenue"),
                func.coalesce(func.sum(Order.cost_basis), 0).label("total_cogs"),
                func.coalesce(func.sum(Order.platform_fees), 0).label("total_fees"),
                func.coalesce(func.sum(Order.shipping_cost), 0).label("total_shipping"),
                func.coalesce(func.sum(Order.profit), 0).label("net_profit"),
            ).where(*filters)
        ).one()

        order_count = int(row.order_count)
        total_revenue = round(float(row.total_revenue), 2)
        total_cogs = round(float(row.total_cogs), 2)
        total_fees = round(float(row.total_fees), 2)
        total_shipping = round(float(row.total_shipping), 2)
        gross_profit = round(total_revenue - total_cogs, 2)
        net_profit = round(float(row.net_profit), 2)
        margin_percent = round((net_profit / total_revenue * 100), 2) if total_revenue > 0 else 0.0
        aov = round(total_revenue / order_count, 2) if order_count > 0 else 0.0

        # Sell-through rate
        total_items = self.db.execute(
            select(func.count(InventoryItem.id)).where(
                InventoryItem.account_id == self.account_id,
                InventoryItem.deleted_at.is_(None),
            )
        ).scalar_one()
        items_sold = self.db.execute(
            select(func.count(InventoryItem.id)).where(
                InventoryItem.account_id == self.account_id,
                InventoryItem.deleted_at.is_(None),
                InventoryItem.status == "sold",
            )
        ).scalar_one()
        sell_through = round((items_sold / total_items * 100), 2) if total_items > 0 else 0.0

        result = {
            "period": period,
            "order_count": order_count,
            "total_revenue": total_revenue,
            "total_cogs": total_cogs,
            "total_fees": total_fees,
            "total_shipping": total_shipping,
            "gross_profit": gross_profit,
            "net_profit": net_profit,
            "margin_percent": margin_percent,
            "average_order_value": aov,
            "sell_through_rate": sell_through,
        }

        self._set_cache(cache_key, result)
        return result

    # ── Category Performance ────────────────────────────────────────

    def get_category_performance(self, period: str = DEFAULT_PERIOD) -> list[dict[str, Any]]:
        """Get per-category revenue and profit breakdown."""
        cache_key = f"analytics:{self.account_id}:categories:{period}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        cutoff = self._get_cutoff(period)

        # Get all categories for this account
        categories = list(
            self.db.execute(
                select(Category).where(
                    Category.account_id == self.account_id,
                    Category.deleted_at.is_(None),
                )
            ).scalars().all()
        )

        results = []
        for cat in categories:
            # Count total items in category
            total_items = self.db.execute(
                select(func.count(InventoryItem.id)).where(
                    InventoryItem.account_id == self.account_id,
                    InventoryItem.category_id == cat.id,
                    InventoryItem.deleted_at.is_(None),
                )
            ).scalar_one()

            # Get order stats for items in this category
            filters = self._base_order_filters(cutoff)
            filters.append(
                Order.inventory_item_id.in_(
                    select(InventoryItem.id).where(
                        InventoryItem.category_id == cat.id,
                        InventoryItem.account_id == self.account_id,
                    )
                )
            )

            row = self.db.execute(
                select(
                    func.coalesce(func.count(Order.id), 0).label("item_count"),
                    func.coalesce(func.sum(Order.sale_price), 0).label("revenue"),
                    func.coalesce(func.sum(Order.profit), 0).label("profit"),
                ).where(*filters)
            ).one()

            items_sold = int(row.item_count)
            sell_through = round((items_sold / total_items * 100), 2) if total_items > 0 else 0.0

            results.append({
                "category_id": str(cat.id),
                "category_name": cat.name,
                "revenue": round(float(row.revenue), 2),
                "profit": round(float(row.profit), 2),
                "item_count": items_sold,
                "total_items": total_items,
                "sell_through_rate": sell_through,
            })

        results.sort(key=lambda x: x["revenue"], reverse=True)

        self._set_cache(cache_key, results)
        return results

    # ── Show Performance ────────────────────────────────────────────

    def get_show_performance(self, period: str = DEFAULT_PERIOD) -> list[dict[str, Any]]:
        """Get per-show revenue and profit analysis."""
        cache_key = f"analytics:{self.account_id}:shows:{period}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        cutoff = self._get_cutoff(period)

        # Get shows in period
        show_query = select(Show).where(
            Show.account_id == self.account_id,
            Show.deleted_at.is_(None),
        )
        if cutoff:
            show_query = show_query.where(Show.created_at >= cutoff)

        shows = list(self.db.execute(show_query.order_by(Show.created_at.desc())).scalars().all())

        results = []
        for show in shows:
            row = self.db.execute(
                select(
                    func.coalesce(func.count(Order.id), 0).label("order_count"),
                    func.coalesce(func.sum(Order.sale_price), 0).label("revenue"),
                    func.coalesce(func.sum(Order.profit), 0).label("profit"),
                ).where(
                    Order.account_id == self.account_id,
                    Order.show_id == show.id,
                    Order.deleted_at.is_(None),
                    Order.status != OrderStatus.CANCELLED,
                )
            ).one()

            duration_minutes = None
            if show.started_at and show.ended_at:
                delta = show.ended_at - show.started_at
                duration_minutes = round(delta.total_seconds() / 60, 1)

            results.append({
                "show_id": str(show.id),
                "show_title": show.title,
                "date": show.created_at.isoformat(),
                "status": show.status,
                "order_count": int(row.order_count),
                "revenue": round(float(row.revenue), 2),
                "profit": round(float(row.profit), 2),
                "duration_minutes": duration_minutes,
            })

        self._set_cache(cache_key, results)
        return results

    # ── Revenue Trends ──────────────────────────────────────────────

    def get_trends(self, period: str = DEFAULT_PERIOD, granularity: str = "day") -> list[dict[str, Any]]:
        """Get time-series revenue and profit data."""
        cache_key = f"analytics:{self.account_id}:trends:{period}:{granularity}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        cutoff = self._get_cutoff(period)
        if cutoff is None:
            # For "all", default to 365 days for trends
            cutoff = datetime.now(timezone.utc) - timedelta(days=365)

        # Generate date buckets
        now = datetime.now(timezone.utc)
        buckets = self._generate_buckets(cutoff, now, granularity)

        # Get all orders in the period
        filters = self._base_order_filters(cutoff)
        orders = list(
            self.db.execute(
                select(Order).where(*filters)
            ).scalars().all()
        )

        # Group orders into buckets
        results = []
        for bucket_start, bucket_end, label in buckets:
            bucket_orders = [
                o for o in orders
                if self._ensure_aware(o.created_at) >= bucket_start
                and self._ensure_aware(o.created_at) < bucket_end
            ]

            revenue = sum(float(o.sale_price) for o in bucket_orders)
            profit = sum(float(o.profit) for o in bucket_orders)

            results.append({
                "date": label,
                "revenue": round(revenue, 2),
                "profit": round(profit, 2),
                "order_count": len(bucket_orders),
            })

        self._set_cache(cache_key, results)
        return results

    # ── Top Selling Items ───────────────────────────────────────────

    def get_top_items(
        self,
        period: str = DEFAULT_PERIOD,
        sort_by: str = "revenue",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get top-performing items by revenue, profit, or quantity."""
        cache_key = f"analytics:{self.account_id}:top_items:{period}:{sort_by}:{limit}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        cutoff = self._get_cutoff(period)

        # Aggregate orders by inventory item
        query = (
            select(
                Order.inventory_item_id,
                func.count(Order.id).label("quantity_sold"),
                func.sum(Order.sale_price).label("revenue"),
                func.sum(Order.profit).label("profit"),
            )
            .where(
                Order.account_id == self.account_id,
                Order.deleted_at.is_(None),
                Order.status != OrderStatus.CANCELLED,
            )
            .group_by(Order.inventory_item_id)
        )

        if cutoff:
            query = query.where(Order.created_at >= cutoff)

        sort_map = {
            "revenue": func.sum(Order.sale_price).desc(),
            "profit": func.sum(Order.profit).desc(),
            "quantity": func.count(Order.id).desc(),
        }
        query = query.order_by(sort_map.get(sort_by, func.sum(Order.sale_price).desc()))
        query = query.limit(limit)

        rows = self.db.execute(query).all()

        results = []
        for row in rows:
            item = self.db.execute(
                select(InventoryItem).where(InventoryItem.id == row.inventory_item_id)
            ).scalar_one_or_none()

            if item is None:
                continue

            # Get category name
            cat_name = None
            if item.category_id:
                cat = self.db.execute(
                    select(Category).where(Category.id == item.category_id)
                ).scalar_one_or_none()
                if cat:
                    cat_name = cat.name

            revenue = round(float(row.revenue), 2)
            profit = round(float(row.profit), 2)
            margin = round((profit / revenue * 100), 2) if revenue > 0 else 0.0

            results.append({
                "item_id": str(row.inventory_item_id),
                "item_name": item.name,
                "category": cat_name,
                "quantity_sold": int(row.quantity_sold),
                "revenue": revenue,
                "profit": profit,
                "margin_percent": margin,
            })

        self._set_cache(cache_key, results)
        return results

    # ── Helpers ─────────────────────────────────────────────────────

    def _base_order_filters(self, cutoff: datetime | None) -> list:
        """Build a list of filter clauses for non-cancelled, non-deleted orders."""
        filters = [
            Order.account_id == self.account_id,
            Order.deleted_at.is_(None),
            Order.status != OrderStatus.CANCELLED,
        ]
        if cutoff:
            filters.append(Order.created_at >= cutoff)
        return filters

    def _get_cutoff(self, period: str) -> datetime | None:
        """Convert period string to a cutoff datetime."""
        delta = PERIOD_MAP.get(period)
        if delta is None:
            return None
        return datetime.now(timezone.utc) - delta

    def _generate_buckets(
        self, start: datetime, end: datetime, granularity: str
    ) -> list[tuple[datetime, datetime, str]]:
        """Generate time buckets for trend data."""
        buckets = []
        current = start.replace(hour=0, minute=0, second=0, microsecond=0)

        if granularity == "week":
            # Align to Monday
            current -= timedelta(days=current.weekday())
            delta = timedelta(weeks=1)
        elif granularity == "month":
            current = current.replace(day=1)
            delta = None  # handled specially
        else:
            delta = timedelta(days=1)

        while current < end:
            if granularity == "month":
                # Next month
                if current.month == 12:
                    next_bucket = current.replace(year=current.year + 1, month=1)
                else:
                    next_bucket = current.replace(month=current.month + 1)
                buckets.append((current, next_bucket, current.strftime("%Y-%m")))
                current = next_bucket
            else:
                assert delta is not None
                next_bucket = current + delta
                label = current.strftime("%Y-%m-%d")
                buckets.append((current, next_bucket, label))
                current = next_bucket

        return buckets

    @staticmethod
    def _ensure_aware(dt: datetime) -> datetime:
        """Ensure a datetime is timezone-aware (SQLite returns naive)."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def _get_cache(self, key: str) -> Any | None:
        """Get a value from Redis cache."""
        if self.redis is None:
            return None
        try:
            data = self.redis.get(key)
            if data:
                return json.loads(data)
        except Exception:
            logger.warning("Cache read failed for key: %s", key)
        return None

    def _set_cache(self, key: str, value: Any) -> None:
        """Set a value in Redis cache with TTL."""
        if self.redis is None:
            return
        try:
            self.redis.setex(key, self.cache_ttl, json.dumps(value, default=str))
        except Exception:
            logger.warning("Cache write failed for key: %s", key)
