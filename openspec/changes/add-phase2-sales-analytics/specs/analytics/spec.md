## ADDED Requirements

### Requirement: Revenue Summary
The system SHALL provide an aggregated revenue and profit summary for a seller's account.

#### Scenario: Get summary for last 30 days
- **WHEN** an authenticated user requests GET /analytics/summary?period=30d
- **THEN** the system returns: total_revenue, total_cogs, total_fees, total_shipping, gross_profit, net_profit, margin_percent, average_order_value, order_count, sell_through_rate
- **AND** all values are scoped to the user's account and the specified period

#### Scenario: Get all-time summary
- **WHEN** an authenticated user requests GET /analytics/summary?period=all
- **THEN** the system returns lifetime aggregated metrics

#### Scenario: No sales data
- **WHEN** a user has no orders in the requested period
- **THEN** the system returns all metrics as 0 (not null)

### Requirement: Category Performance
The system SHALL provide per-category revenue and profit breakdown.

#### Scenario: Get category performance
- **WHEN** an authenticated user requests GET /analytics/categories?period=30d
- **THEN** the system returns an array of categories, each with: category_name, revenue, profit, item_count, sell_through_rate
- **AND** sorted by revenue descending by default

#### Scenario: Category with no sales
- **WHEN** a category has inventory items but no sales in the period
- **THEN** the category appears with revenue=0 and sell_through_rate=0

### Requirement: Show Performance
The system SHALL provide per-show revenue and profit analysis.

#### Scenario: Get show performance
- **WHEN** an authenticated user requests GET /analytics/shows?period=30d
- **THEN** the system returns an array of shows, each with: show_title, date, order_count, revenue, profit, duration_minutes
- **AND** sorted by date descending by default

### Requirement: Revenue Trends
The system SHALL provide time-series revenue and profit data for trend visualization.

#### Scenario: Daily trend for 30 days
- **WHEN** an authenticated user requests GET /analytics/trends?period=30d&granularity=day
- **THEN** the system returns an array of daily data points with: date, revenue, profit, order_count
- **AND** includes days with zero activity (revenue=0, profit=0, order_count=0)

#### Scenario: Weekly trend for 90 days
- **WHEN** an authenticated user requests GET /analytics/trends?period=90d&granularity=week
- **THEN** the system returns weekly aggregated data points

#### Scenario: Monthly trend for 365 days
- **WHEN** an authenticated user requests GET /analytics/trends?period=365d&granularity=month
- **THEN** the system returns monthly aggregated data points

### Requirement: Top Selling Items
The system SHALL identify top-performing inventory items by revenue, profit, or quantity.

#### Scenario: Top items by revenue
- **WHEN** an authenticated user requests GET /analytics/top-items?sort_by=revenue&limit=10&period=30d
- **THEN** the system returns the top 10 items by total revenue with: item_name, category, quantity_sold, revenue, profit, margin_percent

#### Scenario: Top items by profit
- **WHEN** an authenticated user requests GET /analytics/top-items?sort_by=profit&limit=10
- **THEN** the system returns the top 10 items by profit

### Requirement: Analytics Caching
The system SHALL cache analytics results for performance.

#### Scenario: Cache hit
- **WHEN** a user requests analytics that were computed within the last 5 minutes
- **THEN** the system returns cached results
- **AND** includes a `cached_at` timestamp in the response meta

#### Scenario: Cache invalidation
- **WHEN** a new order is created or cancelled
- **THEN** the system invalidates relevant analytics caches for that account

### Requirement: Account Isolation
The system SHALL ensure strict account isolation for all analytics queries.

#### Scenario: Cross-account data leak prevention
- **WHEN** an authenticated user requests analytics
- **THEN** the system only includes data from the user's own account
- **AND** never exposes other accounts' revenue, items, or performance data
