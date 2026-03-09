## 1. Monorepo Scaffolding
- [ ] 1.1 Create folder structure: services/{auth,inventory,gateway,shared}, k8s/{dev,prod}, docs/
- [ ] 1.2 Create root pyproject.toml with shared tooling config (ruff, mypy, pytest, bandit)
- [ ] 1.3 Create Makefile with targets: lint, typecheck, security-scan, test, coverage, build, deploy, clean, dev-up, dev-down
- [ ] 1.4 Create root README.md with project overview, setup instructions, and Makefile usage
- [ ] 1.5 Create .env.example with all required environment variables documented

## 2. Shared Libraries (services/shared/)
- [ ] 2.1 Create base SQLAlchemy model with id (UUID), created_at, updated_at, deleted_at (soft delete mixin)
- [ ] 2.2 Create audit trail mixin/model (action, actor_id, resource_type, resource_id, changes JSON, timestamp)
- [ ] 2.3 Create base repository class with soft-delete-aware queries, pagination, and account scoping
- [ ] 2.4 Create Redis Pub/Sub event publisher and subscriber base classes
- [ ] 2.5 Create shared error handlers and JSON error response envelope
- [ ] 2.6 Create health check blueprint (/health, /ready endpoints)
- [ ] 2.7 Create structured logging setup (structlog, JSON format, request_id injection)
- [ ] 2.8 Create Flask app factory base with common configuration
- [ ] 2.9 Create shared test fixtures and factory_boy base factories
- [ ] 2.10 Write tests for all shared components (100% coverage)

## 3. Auth Service (services/auth/)
- [ ] 3.1 Create Flask app factory and configuration (dev/prod)
- [ ] 3.2 Create database models: Account, User, RefreshToken, TeamInvite
- [ ] 3.3 Create Marshmallow schemas: registration, login, token response, user profile, team invite
- [ ] 3.4 Create auth repository (user CRUD, token storage, invite management)
- [ ] 3.5 Create auth service layer (register, login, refresh, logout, password reset, email verification)
- [ ] 3.6 Create account/team service layer (create account, invite member, update role, remove member)
- [ ] 3.7 Create API routes: POST /register, POST /login, POST /refresh, POST /logout, POST /password-reset, POST /password-reset/confirm, POST /verify-email
- [ ] 3.8 Create API routes: GET /account, PUT /account, GET /account/members, POST /account/invite, PUT /account/members/{id}/role, DELETE /account/members/{id}
- [ ] 3.9 Create API routes: GET /users/me, PUT /users/me, DELETE /users/me (account deletion with data purge)
- [ ] 3.10 Implement account lockout (5 failed attempts, 15-minute cooldown)
- [ ] 3.11 Implement free tier enforcement (2 team members max)
- [ ] 3.12 Publish Pub/Sub events: user.created, user.deleted, team.member.invited, team.member.removed
- [ ] 3.13 Create Dockerfile (multi-stage build)
- [ ] 3.14 Create OpenAPI spec auto-generation config
- [ ] 3.15 Write unit tests for service and repository layers (100% coverage)
- [ ] 3.16 Write integration tests for all API endpoints
- [ ] 3.17 Write security tests (auth bypass, IDOR, injection, lockout)

## 4. Inventory Service (services/inventory/)
- [ ] 4.1 Create Flask app factory and configuration (dev/prod)
- [ ] 4.2 Create database models: InventoryItem, Category, CSVImportJob
- [ ] 4.3 Create Marshmallow schemas: item create/update/response, category CRUD, CSV upload/mapping/result
- [ ] 4.4 Create inventory repository (item CRUD, category CRUD, search/filter, account-scoped)
- [ ] 4.5 Create inventory service layer (item management, category management, search, tier limit enforcement)
- [ ] 4.6 Create CSV import service (upload, detect columns, accept mapping, validate rows, import with error report)
- [ ] 4.7 Create API routes: full CRUD for items — POST /items, GET /items, GET /items/{id}, PUT /items/{id}, DELETE /items/{id}
- [ ] 4.8 Create API routes: full CRUD for categories — POST /categories, GET /categories, GET /categories/{id}, PUT /categories/{id}, DELETE /categories/{id}
- [ ] 4.9 Create API routes: POST /items/import/upload, POST /items/import/map, GET /items/import/{job_id}/status
- [ ] 4.10 Create API routes: GET /items/deleted (list soft-deleted), POST /items/{id}/restore
- [ ] 4.11 Implement search and filtering (by category, name, status, price range, date added)
- [ ] 4.12 Implement free tier enforcement (50 items max)
- [ ] 4.13 Implement audit trail logging on all item/category mutations
- [ ] 4.14 Publish Pub/Sub events: inventory.item.created, inventory.item.updated, inventory.item.deleted, inventory.item.restored
- [ ] 4.15 Create Celery task: 30-day soft delete purge job
- [ ] 4.16 Create Dockerfile (multi-stage build)
- [ ] 4.17 Create OpenAPI spec auto-generation config
- [ ] 4.18 Write unit tests for service, repository, and CSV import layers (100% coverage)
- [ ] 4.19 Write integration tests for all API endpoints
- [ ] 4.20 Write security tests (IDOR across accounts, injection, tier bypass)

## 5. API Gateway (services/gateway/)
- [ ] 5.1 Create Flask app factory and configuration (dev/prod)
- [ ] 5.2 Create route definitions mapping /api/v1/* to internal services
- [ ] 5.3 Implement request proxying to auth and inventory services
- [ ] 5.4 Implement rate limiting (Flask-Limiter, per-user and per-IP)
- [ ] 5.5 Implement CORS configuration (allowlisted origins only)
- [ ] 5.6 Implement request ID injection (X-Request-ID header)
- [ ] 5.7 Implement request/response logging
- [ ] 5.8 Create aggregated health check endpoint (/api/v1/health — checks all downstream services)
- [ ] 5.9 Create Dockerfile (multi-stage build)
- [ ] 5.10 Write unit tests for routing and middleware (100% coverage)
- [ ] 5.11 Write integration tests for end-to-end request flow

## 6. Database & Migrations
- [ ] 6.1 Create Alembic configuration and initial migration (all tables)
- [ ] 6.2 Create seed data script (dev environment: test account, test user, sample categories)
- [ ] 6.3 Verify all foreign keys, indexes, and constraints are correct

## 7. Docker & Local Development
- [ ] 7.1 Create docker-compose.yml (gateway, auth, inventory, postgres, redis — 5 services)
- [ ] 7.2 Create .env.example with all environment variables
- [ ] 7.3 Verify `make dev-up` starts all services and they communicate correctly
- [ ] 7.4 Verify `make test` runs full test suite with coverage report

## 8. K3S Production Deployment
- [ ] 8.1 Create k8s/prod/ manifests: Namespace, ConfigMap, Secrets template
- [ ] 8.2 Create k8s/prod/ manifests: PostgreSQL Deployment + Service + PersistentVolumeClaim
- [ ] 8.3 Create k8s/prod/ manifests: Redis Deployment + Service
- [ ] 8.4 Create k8s/prod/ manifests: Auth Deployment + Service
- [ ] 8.5 Create k8s/prod/ manifests: Inventory Deployment + Service
- [ ] 8.6 Create k8s/prod/ manifests: Gateway Deployment + Service
- [ ] 8.7 Create k8s/prod/ manifests: Ingress (Traefik) for whattools.trector.com
- [ ] 8.8 Add liveness and readiness probes to all service Deployments
- [ ] 8.9 Add `make deploy` target that applies all manifests via kubectl
- [ ] 8.10 Verify full deployment works on K3S cluster

## 9. Documentation
- [ ] 9.1 Generate OpenAPI docs for auth and inventory services into docs/
- [ ] 9.2 Create docs/architecture.md with service diagram and data flow
- [ ] 9.3 Create docs/api-guide.md with authentication flow and example requests
- [ ] 9.4 Create docs/deployment.md with K3S setup and deployment instructions
