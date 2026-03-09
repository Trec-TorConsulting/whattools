"""Chart generation for PDF reports using matplotlib."""

import io
from typing import Any

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def generate_trend_chart(trends: list[dict[str, Any]]) -> bytes:
    """Generate a revenue/profit trend line chart and return as PNG bytes."""
    if not trends:
        return _empty_chart("No trend data available")

    dates = [t["date"] for t in trends]
    revenues = [t["revenue"] for t in trends]
    profits = [t["profit"] for t in trends]

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(dates, revenues, label="Revenue", color="#2196F3", linewidth=2, marker="o", markersize=3)
    ax.plot(dates, profits, label="Profit", color="#4CAF50", linewidth=2, marker="o", markersize=3)
    ax.fill_between(range(len(dates)), profits, alpha=0.1, color="#4CAF50")
    ax.set_title("Revenue & Profit Trend", fontsize=14, fontweight="bold")
    ax.set_ylabel("Amount ($)")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Rotate x labels if more than 10 data points
    if len(dates) > 10:
        plt.xticks(rotation=45, ha="right")
        # Show fewer labels
        step = max(1, len(dates) // 10)
        ax.set_xticks(range(0, len(dates), step))
        ax.set_xticklabels([dates[i] for i in range(0, len(dates), step)])

    plt.tight_layout()
    return _fig_to_bytes(fig)


def generate_category_chart(categories: list[dict[str, Any]]) -> bytes:
    """Generate a category performance bar chart and return as PNG bytes."""
    if not categories:
        return _empty_chart("No category data available")

    # Show top 10 categories
    cats = categories[:10]
    names = [c["category_name"] for c in cats]
    revenues = [c["revenue"] for c in cats]
    profits = [c["profit"] for c in cats]

    fig, ax = plt.subplots(figsize=(10, 4))
    x = range(len(names))
    width = 0.35
    bars1 = ax.bar([i - width / 2 for i in x], revenues, width, label="Revenue", color="#2196F3")
    bars2 = ax.bar([i + width / 2 for i in x], profits, width, label="Profit", color="#4CAF50")
    ax.set_title("Category Performance", fontsize=14, fontweight="bold")
    ax.set_ylabel("Amount ($)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(names, rotation=30, ha="right")
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    return _fig_to_bytes(fig)


def generate_top_items_chart(top_items: list[dict[str, Any]]) -> bytes:
    """Generate a horizontal bar chart of top items and return as PNG bytes."""
    if not top_items:
        return _empty_chart("No top items data available")

    items = top_items[:10]
    names = [t["item_name"][:25] for t in items]  # Truncate long names
    revenues = [t["revenue"] for t in items]

    fig, ax = plt.subplots(figsize=(10, 4))
    y = range(len(names))
    bars = ax.barh(list(y), revenues, color="#FF9800", height=0.6)
    ax.set_yticks(list(y))
    ax.set_yticklabels(names)
    ax.set_xlabel("Revenue ($)")
    ax.set_title("Top Items by Revenue", fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3, axis="x")
    ax.invert_yaxis()

    # Add value labels
    for bar, rev in zip(bars, revenues):
        ax.text(bar.get_width() + max(revenues) * 0.01, bar.get_y() + bar.get_height() / 2,
                f"${rev:,.2f}", va="center", fontsize=9)

    plt.tight_layout()
    return _fig_to_bytes(fig)


def _fig_to_bytes(fig: plt.Figure) -> bytes:
    """Convert a matplotlib figure to PNG bytes."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _empty_chart(message: str) -> bytes:
    """Generate a placeholder chart with a message."""
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.text(0.5, 0.5, message, transform=ax.transAxes,
            fontsize=16, ha="center", va="center", color="#666")
    ax.set_axis_off()
    plt.tight_layout()
    return _fig_to_bytes(fig)
