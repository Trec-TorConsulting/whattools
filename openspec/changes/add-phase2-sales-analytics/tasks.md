## 1. Sales Service Setup (services/sales/)
- [ ] 1.1 Create Flask app factory and configuration (dev/prod)
- [ ] 1.2 Create database models: Show, Order
- [ ] 1.3 Create Marshmallow schemas: show create/update/response, order create/update/response, show summary
- [ ] 1.4 Create show repository (CRUD, account-scoped, soft-delete-aware, filter by status/date)
- [ ] 1.5 Create order repository (CRUD, account-scoped, soft-delete-aware, filter by show/status/date)
- [ ] 1.6 Create show service layer (create, update, start, complete, cancel shows)
- [ ] 1.7 Create order service layer (create order linked to show + inventory item, update, cancel with inventory status rollback)
- [ ] 1.8 Create API routes: POST /shows, GET /shows, GET /shows/{id}, PUT /shows/{id}, DELETE /shows/{id}
- [ ] 1.9 Create API routes: POST /shows/{id}/start, POST /shows/{id}/complete, POST /shows/{id}/cancel
- [ ] 1.10 Create API routes: POST /orders, GET /orders, GET /orders/{id}, PUT /orders/{id}, DELETE /orders/{id}
- [ ] 1.11 Create API routes: GET /shows/{id}/orders (list orders for a show)
- [ ] 1.12 Create API routes: GET /orders/deleted, POST /orders/{id}/restore
- [ ] 1.13 Implement profit calculation per order (sale_price - platform_fees - shipping_cost - item.cost_basis)
- [ ] 1.14 Publish Pub/Sub events: show.created, show.started, show.completed, show.cancelled, order.created, order.updated, order.cancelled
- [ ] 1.15 Implement audit trail logging on all show/order mutations
- [ ] 1.16 Create Dockerfile (multi-stage build)
- [ ] 1.17 Write unit tests for service and repository layers (90%+ coverage)
- [ ] 1.18 Write integration tests for all API endpoints
- [ ] 1.19 Write security tests (IDOR across accounts, status transition validation)

## 2. Inventory Service Updates
- [ ] 2.1 Add `sold` status to ItemStatus enum
- [ ] 2.2 Create Alembic migration for ItemStatus enum update
- [ ] 2.3 Add internal endpoint or service method to transition item status (active ↔ sold)
- [ ] 2.4 Subscribe to order.created and order.cancelled events to update item status
- [ ] 2.5 Write tests for new status transitions and event handling

## 3. Analytics Service Setup (services/analytics/)
- [ ] 3.1 Create Flask app factory and configuration (dev/prod)
- [ ] 3.2 Create analytics service layer (revenue, profit, margin calculations with period filtering)
- [ ] 3.3 Create analytics cache layer (Redis-backed with configurable TTL)
- [ ] 3.4 Create API routes: GET /analytics/summary (revenue, COGS, fees, shipping, gross profit, net profit, margin %, AOV)
- [ ] 3.5 Create API routes: GET /analytics/categories (per-category revenue, profit, item count, sell-through rate)
- [ ] 3.6 Create API routes: GET /analytics/shows (per-show revenue, profit, order count, duration)
- [ ] 3.7 Create API routes: GET /analytics/trends (time-series revenue and profit by day/week/month)
- [ ] 3.8 Create API routes: GET /analytics/top-items (top selling items by revenue, profit, or quantity)
- [ ] 3.9 Subscribe to sale/order events for cache invalidation
- [ ] 3.10 Create Dockerfile (multi-stage build)
- [ ] 3.11 Write unit tests for analytics calculations (90%+ coverage)
- [ ] 3.12 Write integration tests for all API endpoints
- [ ] 3.13 Write security tests (account isolation, no cross-account data leakage)

## 4. API Gateway Updates
- [ ] 4.1 Add route mappings for sales service (/api/v1/shows/*, /api/v1/orders/*)
- [ ] 4.2 Add route mappings for analytics service (/api/v1/analytics/*)
- [ ] 4.3 Update health check aggregation to include sales and analytics services
- [ ] 4.4 Write tests for new routing rules

## 5. Shared Infrastructure Updates
- [ ] 5.1 Add new event type constants (show.*, order.*)
- [ ] 5.2 Update shared test fixtures with show and order factories
- [ ] 5.3 Write tests for new shared components

## 6. Database & Migrations
- [ ] 6.1 Create Alembic migration for shows table
- [ ] 6.2 Create Alembic migration for orders table
- [ ] 6.3 Update seed data script with sample shows and orders
- [ ] 6.4 Verify all foreign keys, indexes, and constraints

## 7. Docker & K3S Updates
- [ ] 7.1 Add sales and analytics services to docker-compose.yml
- [ ] 7.2 Update .env.example with new service environment variables
- [ ] 7.3 Create k8s/prod/ manifests: Sales Deployment + Service
- [ ] 7.4 Create k8s/prod/ manifests: Analytics Deployment + Service
- [ ] 7.5 Update k8s/prod/gateway.yaml with new upstream service URLs
- [ ] 7.6 Update k8s/prod/configmap.yaml with new service config

## 8. Documentation
- [ ] 8.1 Update docs/openapi.yaml with sales and analytics endpoints
- [ ] 8.2 Update docs/api-guide.md with sales workflow and analytics examples
- [ ] 8.3 Update docs/architecture.md with new services diagram
- [ ] 8.4 Update docs/deployment.md with new services
