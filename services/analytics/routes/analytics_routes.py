"""Analytics routes — read-only aggregate endpoints."""

import uuid

from flask import Blueprint, current_app, request
from flask_jwt_extended import get_jwt, jwt_required

from services.analytics.services.analytics_service import AnalyticsService, PERIOD_MAP
from services.shared.database import get_db
from services.shared.errors import error_response, success_response

analytics_bp = Blueprint("analytics", __name__)

VALID_PERIODS = set(PERIOD_MAP.keys())
VALID_SORT_BY = {"revenue", "profit", "quantity"}
VALID_GRANULARITY = {"day", "week", "month"}


def _get_service() -> AnalyticsService:
    db = get_db()
    claims = get_jwt()
    account_id = uuid.UUID(claims["account_id"])
    redis_client = current_app.config.get("_REDIS_CLIENT")
    cache_ttl = current_app.config.get("ANALYTICS_CACHE_TTL", 300)
    return AnalyticsService(db, account_id, redis_client=redis_client, cache_ttl=cache_ttl)


def _validate_period(period: str | None) -> str:
    """Validate and return period parameter."""
    if period is None:
        return "30d"
    if period not in VALID_PERIODS:
        raise ValueError(f"Invalid period. Must be one of: {', '.join(sorted(VALID_PERIODS))}")
    return period


@analytics_bp.route("/summary", methods=["GET"])
@jwt_required()
def get_summary():  # type: ignore[no-untyped-def]
    """Get aggregated revenue and profit summary."""
    try:
        period = _validate_period(request.args.get("period"))
    except ValueError as e:
        return error_response("validation_error", str(e), status_code=422)

    svc = _get_service()
    result = svc.get_summary(period)
    return success_response(result)


@analytics_bp.route("/categories", methods=["GET"])
@jwt_required()
def get_categories():  # type: ignore[no-untyped-def]
    """Get per-category performance breakdown."""
    try:
        period = _validate_period(request.args.get("period"))
    except ValueError as e:
        return error_response("validation_error", str(e), status_code=422)

    svc = _get_service()
    result = svc.get_category_performance(period)
    return success_response(result)


@analytics_bp.route("/shows", methods=["GET"])
@jwt_required()
def get_shows():  # type: ignore[no-untyped-def]
    """Get per-show performance analysis."""
    try:
        period = _validate_period(request.args.get("period"))
    except ValueError as e:
        return error_response("validation_error", str(e), status_code=422)

    svc = _get_service()
    result = svc.get_show_performance(period)
    return success_response(result)


@analytics_bp.route("/trends", methods=["GET"])
@jwt_required()
def get_trends():  # type: ignore[no-untyped-def]
    """Get time-series revenue and profit data."""
    try:
        period = _validate_period(request.args.get("period"))
    except ValueError as e:
        return error_response("validation_error", str(e), status_code=422)

    granularity = request.args.get("granularity", "day")
    if granularity not in VALID_GRANULARITY:
        return error_response(
            "validation_error",
            f"Invalid granularity. Must be one of: {', '.join(sorted(VALID_GRANULARITY))}",
            status_code=422,
        )

    svc = _get_service()
    result = svc.get_trends(period, granularity)
    return success_response(result)


@analytics_bp.route("/top-items", methods=["GET"])
@jwt_required()
def get_top_items():  # type: ignore[no-untyped-def]
    """Get top-performing items."""
    try:
        period = _validate_period(request.args.get("period"))
    except ValueError as e:
        return error_response("validation_error", str(e), status_code=422)

    sort_by = request.args.get("sort_by", "revenue")
    if sort_by not in VALID_SORT_BY:
        return error_response(
            "validation_error",
            f"Invalid sort_by. Must be one of: {', '.join(sorted(VALID_SORT_BY))}",
            status_code=422,
        )

    try:
        limit = int(request.args.get("limit", "10"))
        if limit < 1 or limit > 100:
            raise ValueError()
    except (ValueError, TypeError):
        return error_response("validation_error", "limit must be an integer between 1 and 100.", status_code=422)

    svc = _get_service()
    result = svc.get_top_items(period, sort_by=sort_by, limit=limit)
    return success_response(result)
