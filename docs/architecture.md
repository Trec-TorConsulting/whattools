# WhatTools Architecture

## System Overview

WhatTools is a B2B SaaS platform providing professional-grade tools for [Whatnot](https://www.whatnot.com/) live-selling platform sellers. The system is built as a Python/Flask microservices architecture deployed on K3S.

## Service Architecture

```
                    ┌─────────────────────────────────┐
                    │        Traefik Ingress           │
                    │    whattools.trector.com          │
                    └──────────────┬──────────────────┘
                                   │
                    ┌──────────────▼──────────────────┐
                    │       API Gateway (:5000)        │
                    │  - Request routing & proxy       │
                    │  - Rate limiting (60/min/IP)     │
                    │  - X-Request-ID injection        │
                    │  - Structured access logging     │
                    │  - CORS enforcement              │
                    │  - Aggregated health checks      │
                    └──┬──────┬──────┬──────┬─────────┘
                       │      │      │      │
          ┌────────────▼┐ ┌──▼──────────┐ ┌▼────────────┐ ┌──────────────┐
          │ Auth (:5001) │ │ Inv (:5002) │ │Sales (:5003)│ │Anlys (:5004) │
          │ - Register   │ │ - Item CRUD │ │- Show CRUD  │ │- Rev summary │
          │ - Login      │ │ - Categories│ │- Order CRUD │ │- Category    │
          │ - JWT tokens │ │ - CSV import│ │- Status     │ │  performance │
          │ - Team mgmt  │ │ - Tier      │ │  transitions│ │- Show stats  │
          │ - Password   │ │   enforce   │ │- Profit     │ │- Trends      │
          │   reset      │ │ - Soft del  │ │  tracking   │ │- Top items   │
          └──────┬───────┘ └──────┬──────┘ └──────┬─────┘ └──────┬───────┘
                 │                │               │              │
        ┌────────▼────────────────▼───────────────▼──────────────▼─────┐
        │                     PostgreSQL (:5432)                       │
        │               Shared DB, schema-separated                    │
        └──────────────────────────┬───────────────────────────────────┘
                                   │
        ┌──────────────────────────▼───────────────────────────────────┐
        │                      Redis (:6379)                           │
        │          Pub/Sub · Rate Limit Store · Cache                   │
        └─────────────────────────────────────────────────────────────┘
```

## Services

### API Gateway (port 5000)
Lightweight Flask proxy that routes all `/api/v1/*` requests to the appropriate backend service via httpx. Provides cross-cutting concerns:
- **Request routing**: Path-based resolution to auth, inventory, sales, or analytics services
- **Rate limiting**: 60 requests/minute per IP (Flask-Limiter + Redis)
- **Request ID**: Generates/preserves `X-Request-ID` UUID on every request
- **Logging**: Structured JSON access logs (method, path, status, duration, client IP)
- **Health**: `/health` (gateway liveness) and `/api/v1/health` (aggregated downstream check)

### Auth Service (port 5001)
Handles authentication, authorization, and team management:
- JWT-based auth (15-min access tokens, 7-day refresh tokens with DB-backed revocation)
- Account registration with email verification
- Team invitations (owner/admin/member roles)
- Password reset flow
- Account lockout (5 failed attempts → 15-minute lockout)
- bcrypt password hashing

### Inventory Service (port 5002)
Manages seller inventory with:
- Full CRUD for items and categories
- CSV import workflow (upload → preview → column mapping → import)
- Tier enforcement (free: 50 items, paid: unlimited)
- Soft delete with 30-day retention and restore
- Search/filter/pagination
- Audit trail on all mutations

### Sales Service (port 5003)
Manages live shows and order tracking with profit calculation:
- Show lifecycle management (planned → live → completed/cancelled)
- Order creation with automatic profit calculation from item COGS
- Status transition validation with cascading actions
- Show cancellation cascades to cancel all pending orders and restore inventory
- Soft delete with restore for orders
- Redis event publishing for inter-service communication

### Analytics Service (port 5004)
Read-only aggregation service for business intelligence:
- Revenue summary (revenue, COGS, fees, shipping, gross/net profit, margin %, AOV)
- Per-category performance breakdown with sell-through rates
- Per-show performance with order counts and duration tracking
- Time-series trends (daily, weekly, monthly granularity)
- Top-performing items by revenue, profit, or quantity
- Redis caching with configurable TTL (default 5 minutes)
- Supports period filtering: 7d, 30d, 90d, 365d, all

## Data Model

All models extend `BaseModel` with UUID primary keys, `created_at`/`updated_at` timestamps, and `deleted_at` for soft delete.

### Tables
| Table | Owner | Description |
|-------|-------|-------------|
| `accounts` | Auth | Business accounts with plan tier |
| `users` | Auth | Users with credentials and team role |
| `refresh_tokens` | Auth | JWT refresh token tracking |
| `team_invites` | Auth | Pending team invitations |
| `categories` | Inventory | Item categories per account |
| `inventory_items` | Inventory | Seller inventory items |
| `csv_import_jobs` | Inventory | CSV import job tracking |
| `shows` | Sales | Live selling sessions |
| `orders` | Sales | Item sales with profit tracking |
| `audit_logs` | Shared | Immutable mutation audit trail |

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| Framework | Flask |
| ORM | SQLAlchemy 2.0 (MappedAsDataclass) |
| Serialization | Marshmallow |
| Auth | Flask-JWT-Extended, bcrypt |
| Database | PostgreSQL 16+ |
| Cache/Pub-Sub | Redis 7+ |
| Task Queue | Celery (Redis broker) |
| HTTP Proxy | httpx |
| Rate Limiting | Flask-Limiter |
| Logging | structlog (JSON) |
| Containerization | Docker |
| Orchestration | K3S (Kubernetes) |
| Ingress | Traefik |
| Package Manager | uv |

## Security

- OWASP Top 10 compliant
- bcrypt password hashing with configurable work factor
- JWT with short-lived access tokens and rotatable refresh tokens
- Account lockout after failed login attempts
- Rate limiting on all endpoints
- CORS allowlist enforcement
- Input validation at API boundaries (Marshmallow schemas)
- SQL injection prevention (parameterized queries via SQLAlchemy)
- Account-scoped data isolation in all queries
