## 1. Shipping Service Core
- [ ] 1.1 Create service directory structure (`services/shipping/`)
- [ ] 1.2 Create Shipment model with ShipmentStatus enum
- [ ] 1.3 Create Marshmallow schemas (create, update, response, list query, bulk create)
- [ ] 1.4 Create ShipmentRepository with CRUD, pagination, overdue queries
- [ ] 1.5 Create abstract ShippingProvider and ManualProvider stub
- [ ] 1.6 Create ShippingService (business logic layer)
- [ ] 1.7 Create shipment routes (CRUD + bulk + overdue)
- [ ] 1.8 Create packing list routes
- [ ] 1.9 Create app factory and WSGI entry point
- [ ] 1.10 Create Dockerfile for shipping service

## 2. Database Migration
- [ ] 2.1 Create Alembic migration for `shipments` table

## 3. Gateway Integration
- [ ] 3.1 Add shipping service URL to gateway proxy SERVICE_URLS
- [ ] 3.2 Add `/api/v1/shipments` and `/api/v1/packing-lists` to ROUTE_MAP
- [ ] 3.3 Update gateway tests for new routes

## 4. Infrastructure
- [ ] 4.1 Add shipping service to docker-compose.yml
- [ ] 4.2 Add K8S deployment, service, and configmap for shipping
- [ ] 4.3 Update gateway configmap with SHIPPING_SERVICE_URL

## 5. Testing
- [ ] 5.1 Create conftest.py with test fixtures
- [ ] 5.2 Write model tests
- [ ] 5.3 Write schema tests
- [ ] 5.4 Write service layer tests (CRUD, bulk, packing lists, overdue)
- [ ] 5.5 Write shipment route tests
- [ ] 5.6 Write packing list route tests
- [ ] 5.7 Write provider tests
- [ ] 5.8 Run full test suite — all services must pass with ≥90% coverage

## 6. Documentation
- [ ] 6.1 Update docs/architecture.md with shipping service
- [ ] 6.2 Update docs/api-guide.md with shipping endpoints
- [ ] 6.3 Update docs/deployment.md with shipping service
