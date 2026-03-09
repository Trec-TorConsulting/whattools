## Context
WhatTools is a greenfield B2B SaaS for Whatnot sellers. Phase 1 establishes the foundational architecture that all future phases build upon. Decisions made here affect every service and feature going forward.

Key constraints:
- Solo developer + AI pair programming
- Local K3S cluster for prod, Docker Compose for dev
- Security-first (OWASP Top 10), 100% test coverage from day 1
- API-first: all functionality via REST before any UI exists

## Goals / Non-Goals

**Goals:**
- Establish clean monorepo structure with clear service boundaries
- Deliver working auth and inventory APIs with full CRUD
- Production-ready deployment to K3S
- Patterns that scale: soft deletes, audit trail, pub/sub, health checks

**Non-Goals:**
- No frontend/UI in Phase 1
- No Whatnot API integration (Phase 2)
- No payment/billing (Phase 6)
- No performance optimization beyond reasonable defaults

## Decisions

### 1. Microservice Communication
- **Decision:** Redis Pub/Sub for internal, REST for external
- **Why:** Loose coupling between services. If inventory creates an item, auth service doesn't need to know synchronously. Events like `user.created`, `inventory.item.created` flow via pub/sub.
- **Alternative:** Internal REST calls — rejected because it creates tight coupling and cascading failures.

### 2. Shared Database
- **Decision:** Single PostgreSQL instance, logical separation via SQLAlchemy metadata/table prefixes per service
- **Why:** Microservices purist approach (DB per service) adds operational complexity we don't need at MVP. Services own their tables but share the instance.
- **Migration path:** When a service needs its own DB, extract its tables — the repository pattern makes this a config change, not a code rewrite.

### 3. API Gateway
- **Decision:** Lightweight Flask app that proxies requests to internal services
- **Why:** Keeps it simple, same language/framework as services. No need for Kong/Ambassador at this scale.
- **Responsibilities:** Route matching, JWT validation forwarding, rate limiting (Flask-Limiter), CORS, request ID injection, health aggregation.
- **Alternative:** Traefik IngressRoute rules — rejected because we need request-level logic (rate limiting per user, request logging).

### 4. Auth Architecture
- **Decision:** JWT with short-lived access tokens (15min) + long-lived refresh tokens (7 days), stored refresh tokens in DB for revocation
- **Why:** Stateless auth for scalability, refresh tokens for UX, DB-backed revocation for security.
- **Password hashing:** bcrypt with work factor 12
- **Account lockout:** 5 failed attempts → 15-minute lockout

### 5. Multi-Tenancy / Teams
- **Decision:** Account model — every seller has an "account" (org). Users belong to accounts with roles.
- **Schema:** `accounts` table, `users` table with `account_id` FK, `roles` enum (owner/admin/member)
- **Data isolation:** Every data table has `account_id` FK. All queries scoped by account automatically via repository base class.
- **Invites:** Owner/admin sends invite → email with token → invitee registers under that account.

### 6. Soft Deletes
- **Decision:** `deleted_at` nullable timestamp column on all data models via a SQLAlchemy mixin
- **Behavior:** Queries automatically exclude soft-deleted records. Dedicated endpoints to list/restore deleted items.
- **Purge:** Celery beat job runs daily, permanently deletes records where `deleted_at` > 30 days ago.
- **Audit:** Soft delete and restore actions logged in audit trail.

### 7. CSV Import
- **Decision:** Two-step process: (1) upload CSV, get back detected columns; (2) submit column mapping, system imports
- **Why:** Sellers use wildly different spreadsheet formats. Rigid templates cause friction.
- **Validation:** After mapping, validate each row. Return success/error counts with per-row error details.
- **Limits:** Max 10,000 rows per import (free tier: 50 items enforced after import).

### 8. Logging
- **Decision:** Structured JSON logs to stdout via `structlog`
- **Fields:** timestamp, level, service, request_id, user_id (if authenticated), message, extra
- **Security events:** Login success/failure, permission denied, account lockout — all logged with distinct event types
- **Sensitive data:** Never log passwords, tokens, or PII beyond user_id
- **Aggregation:** Grafana Loki (Phase 4 deployment, but log format is set now)

### 9. Testing Strategy
- **Unit tests:** pytest, every service/model/schema function tested
- **Integration tests:** Flask test client against each service with test DB
- **Fixtures:** factory_boy for consistent test data generation
- **DB per test:** Each test runs in a transaction that gets rolled back
- **Coverage:** pytest-cov, Makefile target fails if < 100%
- **Security tests:** IDOR checks, auth bypass attempts, injection attempts

### 10. Container & Deployment
- **Dev:** `docker-compose.yml` — gateway, auth, inventory, postgres, redis (5 containers)
- **Prod:** kubectl YAML manifests in `k8s/prod/` — Deployments, Services, Ingress, ConfigMaps, Secrets
- **Images:** One Dockerfile per service (multi-stage: build → slim runtime)
- **Health:** `/health` (liveness — am I alive?) and `/ready` (readiness — can I serve traffic?) on every service

## Risks / Trade-offs

| Risk | Impact | Mitigation |
|---|---|---|
| Microservices overhead for solo dev | Slower initial velocity | Shared DB, shared libs, Makefile automation |
| Redis Pub/Sub has no persistence | Lost events on crash | Acceptable for MVP; upgrade to Redis Streams or RabbitMQ if needed |
| Shared DB couples services at data layer | Harder to extract later | Repository pattern + service-owned tables make extraction mechanical |
| 100% coverage is strict | Slower feature velocity | Worth it for greenfield — prevents debt accumulation |

## Open Questions
- None — all architectural decisions resolved in planning sessions.
