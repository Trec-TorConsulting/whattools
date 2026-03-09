## Context
WhatTools Phase 1 delivered auth, inventory, and API gateway. Phase 2 adds the revenue-tracking layer: sellers need to record what they sold, at what price, with what fees, and see whether they're making money. Analytics provides the intelligence layer that aggregates this data into actionable insights.

Key constraints:
- Solo developer + AI pair programming (same as Phase 1)
- Must integrate with existing inventory items (sold items link to inventory)
- Same architecture patterns: layered services, soft deletes, audit trail, pub/sub events
- No Whatnot API integration yet (sellers enter sales data manually or via CSV)
- No frontend — API-only (same as Phase 1)

## Goals / Non-Goals

**Goals:**
- Let sellers record shows and sales (orders) with full financial detail
- Calculate per-item, per-show, and overall profitability
- Provide analytics endpoints for revenue, profit, category performance, and trends
- Maintain 90%+ test coverage across all new code
- Keep same deployment patterns (Docker Compose + K3S)

**Non-Goals:**
- No Whatnot API auto-sync (Phase 3+)
- No shipping label generation (Phase 3+)
- No Stripe billing integration (Phase 3+)
- No frontend/dashboard UI (Phase 3+)
- No real-time streaming analytics (batch/request-time computation is sufficient)

## Decisions

### 1. Sales Service Scope
- **Decision:** Single service handles both Shows and Orders
- **Why:** Shows and orders are tightly coupled — an order always belongs to a show. Splitting them would create unnecessary inter-service calls.
- **Tables owned:** `shows`, `orders`
- **Port:** 5003

### 2. Analytics Service Scope
- **Decision:** Separate read-heavy service that queries across sales and inventory data
- **Why:** Analytics queries are fundamentally different (aggregation, time-series) from CRUD operations. Separating allows independent scaling and caching strategies.
- **Tables owned:** None — reads from shared DB (inventory_items, orders, shows)
- **Port:** 5004
- **Caching:** Redis-cached computed metrics with configurable TTL (5-minute default)

### 3. Order Data Model
- **Decision:** Each order represents a single item sale within a show
- **Fields:** `show_id`, `inventory_item_id`, `sale_price`, `platform_fees`, `shipping_cost`, `buyer_username`, `status` (pending/shipped/delivered/cancelled), `notes`
- **Profit calculation:** `sale_price - platform_fees - shipping_cost - item.cost_basis` (COGS from inventory)
- **Why:** One order per item is simpler and maps directly to how Whatnot works (each lot is a separate sale).

### 4. Show Data Model
- **Decision:** A show is a live selling session container for orders
- **Fields:** `title`, `platform` (whatnot/other), `scheduled_at`, `started_at`, `ended_at`, `status` (planned/live/completed/cancelled), `notes`
- **Why:** Groups sales by session, enabling per-show profitability analysis. `platform` field future-proofs for multi-platform sellers.

### 5. Inventory Status Transition
- **Decision:** Add `sold` to InventoryItem's `ItemStatus` enum
- **When an order is created:** Item status transitions from `active` → `sold`
- **When an order is cancelled:** Item status transitions from `sold` → `active`
- **Why:** Prevents double-selling and gives real-time inventory availability.

### 6. Analytics Computation Strategy
- **Decision:** Request-time computation with Redis caching
- **Why:** Pre-aggregated materialized views add complexity. At MVP scale (< 10K items per seller), request-time queries with proper indexes are fast enough. Redis cache prevents redundant computation.
- **Cache invalidation:** TTL-based (5 minutes). Sales events published via pub/sub can trigger early invalidation if needed.

### 7. Analytics Time Periods
- **Decision:** All time-series endpoints support `period` parameter: `7d`, `30d`, `90d`, `365d`, `all`
- **Default:** `30d`
- **Why:** Covers common seller needs without overcomplicating the API. Custom date ranges can be added later.

### 8. Analytics Metrics
- **Decision:** Core metrics computed by analytics service:
  - **Revenue:** Total sale price across orders
  - **COGS:** Total cost basis of sold items
  - **Fees:** Total platform fees
  - **Shipping:** Total shipping costs
  - **Gross Profit:** Revenue - COGS
  - **Net Profit:** Revenue - COGS - Fees - Shipping
  - **Margin %:** Net Profit / Revenue × 100
  - **Average Order Value (AOV):** Revenue / Order Count
  - **Sell-Through Rate:** Items Sold / Total Items × 100
