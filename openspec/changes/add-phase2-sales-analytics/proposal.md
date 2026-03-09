# Change: Add Phase 2 — Sales & Analytics

## Why
WhatTools has a working authentication and inventory system (Phase 1), but sellers can't track what they've sold, calculate profit margins, or understand their business performance. Profit opacity and lack of analytics are the #2 and #4 seller pain points. Without sales tracking and analytics, the platform delivers no revenue intelligence — the core value proposition.

## What Changes
- Add **sales service**: Shows (live selling sessions), Orders (items sold at a price), fee tracking (Whatnot take rate), shipping cost tracking, profit calculation per order and per show
- Add **analytics service**: Revenue summaries, profit margin analysis, per-category performance, per-show performance, time-series trends (daily/weekly/monthly), top-selling items, COGS vs revenue breakdowns
- Update **inventory service**: Mark items as sold (link to orders), add `sold` status, update item status transitions
- Update **API gateway**: Route /api/v1/shows/*, /api/v1/orders/*, /api/v1/analytics/* to new services
- Update **shared infrastructure**: Add new event types (sale.created, show.created, show.completed)
- Add database migrations for new tables (shows, orders, order_items)
- Update Docker Compose and K3S manifests for new services
- Update documentation with new API endpoints

## Impact
- Affected specs: sales (new), analytics (new), api-gateway (modified), shared-infrastructure (modified), inventory (modified)
- Affected code: services/sales/ (new), services/analytics/ (new), services/gateway/ (modified), services/inventory/ (modified), services/shared/ (modified)
- **BREAKING**: No — additive only, all Phase 1 APIs unchanged
- Risk: Analytics queries on large datasets could be slow; mitigated by database indexes and optional Redis caching for computed metrics
