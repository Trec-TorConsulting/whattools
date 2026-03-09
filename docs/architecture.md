# WhatTools Architecture

## System Overview

WhatTools is a B2B SaaS platform providing professional-grade tools for [Whatnot](https://www.whatnot.com/) live-selling platform sellers. The system is built as a Python/Flask microservices architecture deployed on K3S.

## Service Architecture

```
                    ┌─────────────────────────────────┐
                    │        Traefik Ingress           │
                    │    whattools.trector.com          │
                    └──────────┬──────────┬───────────┘
                               │ /api     │ /
                    ┌──────────▼──────┐ ┌─▼──────────────┐
                    │  API Gateway    │ │  Web Frontend   │
                    │  (:5000)        │ │  (nginx :80)    │
                    │ - Request route │ │ - React 19 SPA  │
                    │ - Rate limiting │ │ - shadcn/ui     │
                    │ - X-Request-ID  │ │ - Static assets │
                    │ - Access logs   │ │ - SPA fallback  │
                    │ - CORS          │ └─────────────────┘
                    │ - Health checks │
                    └──┬──────┬──────┬──────┬──────┬────────┘
                       │      │      │      │      │
          ┌────────────▼┐ ┌──▼──────────┐ ┌▼────────────┐ ┌──────────────┐ ┌──────────────┐
          │ Auth (:5001) │ │ Inv (:5002) │ │Sales (:5003)│ │Anlys (:5004) │ │Ship (:5005)  │
          │ - Register   │ │ - Item CRUD │ │- Show CRUD  │ │- Rev summary │ │- Shipment    │
          │ - Login      │ │ - Categories│ │- Order CRUD │ │- Category    │ │  CRUD        │
          │ - JWT tokens │ │ - CSV import│ │- Status     │ │  performance │ │- Label gen   │
          │ - Team mgmt  │ │ - Tier      │ │  transitions│ │- Show stats  │ │- Bulk create │
          │ - Password   │ │   enforce   │ │- Profit     │ │- Trends      │ │- Packing     │
          │   reset      │ │ - Soft del  │ │  tracking   │ │- Top items   │ │  lists       │
          └──────┬───────┘ └──────┬──────┘ └──────┬─────┘ └──────┬───────┘ └──────┬───────┘
                 │                │               │              │                │
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
- **Request routing**: Path-based resolution to auth, inventory, sales, analytics, or shipping services
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

### Shipping Service (port 5005)
Manages shipment fulfillment with pluggable carrier providers:
- Full CRUD for shipments linked to orders (one shipment per order)
- Status lifecycle management (pending → label_created → shipped → delivered/cancelled)
- Label generation via pluggable provider interface (ManualProvider at MVP)
- Bulk shipment creation for all pending orders in a show
- Packing list generation grouped by buyer with addresses and item details
- Overdue shipment detection (past ship-by date)
- Soft delete with restore and 30-day purge
- Order status sync on ship/deliver via cross-service events

### Analytics Service (port 5004)
Read-only aggregation service for business intelligence:
- Revenue summary (revenue, COGS, fees, shipping, gross/net profit, margin %, AOV)
- Per-category performance breakdown with sell-through rates
- Per-show performance with order counts and duration tracking
- Time-series trends (daily, weekly, monthly granularity)
- Top-performing items by revenue, profit, or quantity
- **Show time optimization**: ML-scored scheduling recommendations based on historical show performance across day/hour slots, with avoid-slots and per-category insights (minimum 3 completed shows required)
- **Async report exports**: CSV and PDF report generation via Celery worker with embedded matplotlib charts, status tracking, 7-day file expiry and automatic cleanup
- Redis caching with configurable TTL (default 5 minutes)
- Supports period filtering: 7d, 30d, 90d, 365d, all

### Analytics Worker
Celery worker process for async report generation:
- Processes export jobs (CSV, PDF with charts)
- Uses Redis DB 2 as broker (`redis://localhost:6379/2`)
- Beat scheduler runs daily cleanup of expired exports
- Generates professional PDF reports with ReportLab and matplotlib charts

### Monitoring Stack (Grafana + Loki)
Centralized log aggregation and dashboarding:
- **Loki 3.0.0**: Log aggregation with TSDB schema, 30-day retention
- **Promtail**: DaemonSet log collector with Kubernetes pod discovery and JSON pipeline
- **Grafana 11.1.0**: Dashboard UI with auto-provisioned Loki datasource
- Pre-built dashboards: Service Overview, Error Explorer, Health Monitor
- Accessible at `grafana.whattools.trector.com`

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
| `shipments` | Shipping | Order shipments with tracking |
| `audit_logs` | Shared | Immutable mutation audit trail |
| `export_jobs` | Analytics | Async report export tracking |

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
| Log Aggregation | Grafana Loki 3.0.0 + Promtail |
| Dashboards | Grafana 11.1.0 |
| PDF Reports | ReportLab, matplotlib |
| Containerization | Docker |
| Orchestration | K3S (Kubernetes) |
| Ingress | Traefik |
| Package Management | Helm 3 |
| Secrets | Bitnami SealedSecrets (optional) |
| Package Manager | uv |
| Frontend | React 19, TypeScript 5.7, Vite 6 |
| UI Components | shadcn/ui (Radix UI), Tailwind CSS 4 |
| Data Fetching | TanStack Query v5, TanStack React Table v8 |
| Charts | Recharts 2 |
| Frontend Testing | Vitest, React Testing Library, MSW 2 |
| E2E Testing | Playwright (Chromium) |
| Web Server | nginx 1.27 |

## Web Frontend

### Stack
| Layer | Technology |
|-------|-----------|
| Framework | React 19 |
| Build Tool | Vite 6 |
| Language | TypeScript 5.7 |
| Styling | Tailwind CSS 4 (OKLCH color tokens) |
| Components | shadcn/ui (Radix UI primitives) |
| Routing | React Router v7 |
| Data Fetching | TanStack Query v5 |
| Tables | TanStack React Table v8 |
| Charts | Recharts 2 |
| Forms | react-hook-form + Zod validation |
| Toasts | Sonner |
| Icons | Lucide React |
| Testing | Vitest + React Testing Library + MSW 2 |
| E2E Testing | Playwright (Chromium) |

### Architecture

```
web/src/
├── lib/              # Core utilities & configuration
│   ├── api-client    # HTTP client with JWT auth + silent refresh
│   ├── auth          # AuthProvider context (login/register/logout)
│   ├── schemas       # Zod schemas + TypeScript types
│   ├── role-utils    # Role-based permission checks
│   ├── query-keys    # TanStack Query key factory
│   └── utils         # Formatting helpers (currency, dates, numbers)
├── hooks/            # Custom React hooks (auth, pagination, theme)
├── components/
│   ├── ui/           # 15 shadcn/ui primitives (button, card, dialog, etc.)
│   └── *.tsx         # 9 shared app components (data-table, app-shell, etc.)
├── routes/           # Auth & role guards (ProtectedRoute, RoleRoute)
├── features/
│   ├── auth/         # Login, Register, Forgot Password, Verify Email
│   ├── dashboard/    # Role-aware KPI dashboard
│   ├── inventory/    # Items list, categories, CSV import
│   ├── sales/        # Shows, orders, profit tracking
│   ├── shipping/     # Shipments, label management
│   ├── analytics/    # Charts dashboard, async exports
│   └── settings/     # Profile, team management, account
└── test/             # Test setup, MSW mocks, render utilities
```

### Key Patterns
- **Component hierarchy**: UI primitives → shared components → feature pages
- **Role-based access**: Three-tier model (owner > admin > member) enforced at route and component level
- **JWT auth**: Access tokens in localStorage with automatic silent refresh and concurrent request queuing via mutex
- **Dark mode**: System preference detection with manual toggle, CSS class strategy
- **Code splitting**: Vite manual chunks — vendor (46KB), query (93KB), ui (145KB), charts (421KB), app (485KB) gzipped
- **API proxy**: Vite dev server proxies `/api` → gateway; nginx does the same in production

### Deployment
- **Docker**: Multi-stage build — `node:22-alpine` (build) → `nginx:1.27-alpine` (serve)
- **Nginx**: Gzip compression, security headers, asset caching (1yr immutable), SPA fallback, `/api` reverse proxy to gateway
- **K8S**: 2-replica Deployment (64Mi/50m request, 128Mi/100m limit), ClusterIP Service, Traefik Ingress at `/` with `/api` routed to gateway

### Testing Strategy
- **Unit tests**: Vitest + React Testing Library + MSW — 51 tests covering utils, role logic, component rendering, guards, and auth flows
- **E2E tests**: Playwright against full Docker Compose stack — auth flows, CRUD for inventory/sales/shipping, analytics, role-based access, settings, theme toggle
- **Test data**: Seeded via `scripts/seed.py` — owner (`demo@whattools.dev`) and member (`member@whattools.dev`) accounts with sample categories

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

## Production Hardening

### Helm Chart (`helm/whattools/`)
Full Helm chart packaging all 61 K8S resources with configurable `values.yaml`:
- **Parameterized**: image registry/tag, replicas, resource limits, storage classes, domain names
- **Init containers**: Database migration via Alembic runs before service startup
- **Rolling updates**: Zero-downtime deploys with `maxUnavailable: 0, maxSurge: 1`
- **SealedSecrets support**: Set `secrets.kind: SealedSecret` for encrypted secrets in Git

### Autoscaling (HPA)
HorizontalPodAutoscalers on all stateless services:
- CPU-based scaling (70% target utilization)
- Gradual scale-down (300s stabilization, 1 pod/min) to prevent flapping
- Aggressive scale-up (60s stabilization, 2 pods/min) for traffic spikes
- Per-service min/max: gateway 2–6, auth 2–8, web 2–10, analytics 2–4

### PodDisruptionBudgets
`minAvailable: 1` on all services ensuring availability during node drains and upgrades.

### Network Policies
Default-deny ingress with explicit allow rules:
- Ingress → gateway & web (external traffic)
- Gateway → all backend services (API proxy)
- All services → PostgreSQL & Redis (data layer)
- Promtail → Loki, Grafana → Loki (observability)

### Security Contexts
All service pods run with:
- `runAsNonRoot: true`, `runAsUser: 1000`
- `readOnlyRootFilesystem: true`
- `allowPrivilegeEscalation: false`
- `capabilities.drop: [ALL]`

### Health Probes
Every service has both liveness and readiness probes:
- **Backend services**: Liveness at `/health` (no DB), Readiness at `/ready` (DB connectivity check)
- **Gateway**: Both probes at `/health`
- **Web (nginx)**: Both probes at `/health`
- **Analytics worker**: Exec-based liveness probe
- **PostgreSQL**: `pg_isready` exec probe
- **Redis**: `redis-cli ping` exec probe

### Persistent Storage
- PostgreSQL: 10Gi PVC (ReadWriteOnce)
- Redis: 2Gi PVC (ReadWriteOnce) — previously emptyDir, now persistent
- Loki: 10Gi PVC
- Grafana: 2Gi PVC
- Export storage: 10Gi PVC (ReadWriteMany, shared between analytics service and worker)
