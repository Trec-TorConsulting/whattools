# Project Context

## Purpose

**WhatTools** is a **B2B SaaS** (Software as a Service) platform that provides tools for Whatnot live-selling platform sellers. It helps sellers manage inventory, track profitability, analyze sales performance, and streamline shipping — all from a single dashboard. Sellers sign up, log in, and use the product — no infrastructure or setup on their end.

### Goals
- Empower Whatnot sellers with professional-grade tools to run their businesses more efficiently
- Reduce manual work (spreadsheets, paper tracking, switching between apps)
- Provide actionable insights on profit margins, best-selling items, and optimal show timing
- API-first architecture so the platform can power web, mobile, CLI, or third-party integrations
- Launch as freemium MVP, grow through Whatnot seller communities

### Target Users
- Whatnot sellers of all sizes (hobbyist to full-time)
- Categories: collectibles, trading cards, sneakers, vintage, comics, toys, fashion, electronics
- Users who currently track inventory in spreadsheets or not at all
- Sellers who want to understand their true profit margins after fees, shipping, and cost of goods

---

## Tech Stack

### Backend (Core)
- **Language:** Python 3.12+
- **Framework:** Flask (API-first, RESTful)
- **API Layer:** Flask-Smorest (OpenAPI/Swagger auto-docs) + Marshmallow (serialization/validation)
- **ORM:** SQLAlchemy 2.0+ (async-compatible)
- **Database:** PostgreSQL 16+ (relational data: inventory, orders, users, analytics)
- **Migrations:** Alembic
- **Auth:** Flask-JWT-Extended (JWT access + refresh tokens), email/password to start
- **Email:** Auth service handles all transactional email (verification, password reset, team invites) — self-contained, no separate notification service
- **Task Queue:** Celery + Redis (background jobs: report generation, data sync, email sending, 30-day purge)
- **Caching:** Redis

### Frontend (Phase 2+)
- Web UI (technology TBD — will consume the API)
- PWA-capable for mobile-like experience on phones/tablets

### Infrastructure
- **Container Runtime:** Docker (all services containerized)
- **Orchestration:** K3S cluster (prod / MVP launch)
- **Future:** Cloud-hosted K8S cluster for production scale
- **Local Dev:** Docker Compose (all services run locally via `docker-compose up`)
- **Prod Deploy:** kubectl apply against K3S cluster
- **Domain:** whattools.trector.com
- **CI/CD:** Makefile-driven (all CI targets: `make lint`, `make test`, `make build`, `make deploy`)
- **K3S Deployment:** Raw kubectl YAML manifests (Deployments, Services, Ingress, ConfigMaps) — no Helm
- **Reverse Proxy:** Traefik (K3S ingress)
- **Secrets Management:** Kubernetes Secrets (local), Vault or sealed-secrets (production)

### Dev Tools
- **Package Manager:** uv (fast Python package management)
- **Linting:** Ruff (replaces flake8, isort, black)
- **Type Checking:** mypy (strict mode)
- **Testing:** pytest + pytest-cov (100% coverage target)
- **Security Scanning:** Bandit (SAST), Safety (dependency vulnerabilities)
- **API Documentation:** Auto-generated OpenAPI 3.1 via Flask-Smorest
- **Pre-commit Hooks:** ruff, mypy, bandit, pytest

### Repository Structure (Monorepo)
```
whattools/
├── services/              # Microservices (each is its own Flask app)
│   ├── auth/              # Auth service (register, login, JWT, teams, email/notifications)
│   ├── inventory/         # Inventory service (items, categories, CSV import)
│   ├── gateway/           # API gateway (lightweight Flask proxy, routing, rate limiting)
│   └── shared/            # Shared libraries (models base, utils, schemas, events)
├── k8s/                   # Kubernetes/K3S manifests
│   ├── dev/               # Dev-specific overrides
│   └── prod/              # Prod manifests (Deployments, Services, Ingress, ConfigMaps, Secrets)
├── docs/                  # All documentation (design docs, API docs, architecture, generated docs)
├── openspec/              # OpenSpec change management
├── docker-compose.yml     # Local development environment
├── Makefile               # All CI/CD targets
├── pyproject.toml         # Root Python config (shared tooling config)
├── README.md
└── .gitignore
```

### Repository Cleanliness
- **Clean repo policy:** No generated files, build artifacts, or IDE configs committed
- **Documentation:** All generated docs go in `/docs` folder (design docs, API docs, architecture diagrams, etc.)
- **Root directory:** Minimal files only — `Makefile`, `Dockerfile`, `pyproject.toml`, `README.md`, `.gitignore`, `docker-compose.yml`
- **No clutter:** Every file in the repo has a clear purpose; remove anything unused
- **Monorepo:** Single repo, clean folder separation per service and concern

---

## Project Conventions

### Code Style
- **Formatter/Linter:** Ruff (configured to enforce PEP 8, import sorting, and consistent style)
- **Naming:** snake_case for functions/variables, PascalCase for classes, UPPER_SNAKE for constants
- **Max line length:** 120 characters
- **Docstrings:** Google-style docstrings on all public functions/classes
- **Type hints:** Required on all function signatures
- **Imports:** Grouped as stdlib → third-party → local, enforced by Ruff

### Architecture Patterns
- **API-First:** All functionality is exposed via RESTful JSON APIs before any UI is built
- **API Versioning:** URL-based versioning from day 1 (`/api/v1/...`) — never break clients
- **Full CRUD:** Every resource gets full Create, Read, Update, Delete endpoints — no partial implementations
- **Microservices:** Each domain (auth, inventory, etc.) is its own Flask service with its own container
- **API Gateway:** Lightweight Flask-based reverse proxy — simple routing, rate limiting, CORS. Scale pods horizontally if needed.
- **Database Strategy:** Shared PostgreSQL database for MVP. Services share the DB but use separate schema namespaces. Designed so heavy services can be split to their own DB later.
- **Inter-Service Communication:**
  - **External (user-facing):** REST via API gateway
  - **Internal (service-to-service):** Redis Pub/Sub for async events. No internal REST calls between services. This enables loose coupling and future growth.
  - **Event Examples:** `user.created`, `inventory.item.created`, `inventory.item.deleted`, `team.member.invited`
- **Per-Service Layered Architecture:**
  - `routes/` — Flask blueprints, request/response handling only
  - `services/` — Business logic layer (all logic lives here)
  - `models/` — SQLAlchemy models (data layer)
  - `schemas/` — Marshmallow schemas (serialization/validation)
  - `repositories/` — Database access abstracted behind repository classes
  - `events/` — Pub/Sub publishers and subscribers
- **Soft Deletes:** All records are soft-deleted (`deleted_at` timestamp), permanently purged after 30 days via scheduled job
- **Audit Trail:** All mutations on important records (inventory, sales, team membership) logged with who/what/when
- **Team Roles:**
  - `owner` — Full control: billing, delete account, manage team, all data
  - `admin` — Manage inventory, manage team members, view analytics
  - `member` — Read/write inventory only, no team or billing access
- **CSV Import:** Accept any CSV file; user maps source columns to WhatTools fields via a mapping step (no rigid template)
- **DTOs/Schemas:** Marshmallow schemas handle all input validation and output serialization
- **Config:** Environment-based configuration (dev/prod) via environment variables
- **Error Handling:** Centralized error handlers returning consistent JSON error responses
- **Pagination:** Cursor-based pagination on all list endpoints
- **Rate Limiting:** Flask-Limiter on all public endpoints
- **Health Checks:** Every service exposes `/health` (liveness) and `/ready` (readiness) endpoints for K3S probes
- **CORS:** Configured for known frontend origins only

### Security (OWASP Top 10 — Baked In From Day 1)
1. **Broken Access Control:** Role-based access, resource ownership checks on every endpoint
2. **Cryptographic Failures:** Passwords hashed with bcrypt, secrets in env vars, HTTPS enforced
3. **Injection:** Parameterized queries via SQLAlchemy ORM (never raw SQL), input validation via Marshmallow
4. **Insecure Design:** Threat modeling per feature, principle of least privilege
5. **Security Misconfiguration:** Hardened Flask config (no debug in prod, secure cookie flags, strict CORS)
6. **Vulnerable Components:** Automated dependency scanning via Safety, pinned versions
7. **Auth Failures:** JWT with short-lived access tokens + refresh tokens, account lockout after failed attempts
8. **Data Integrity:** CSRF protection, signed JWTs, database constraints
9. **Logging & Monitoring:** Structured JSON logging to stdout, security events logged, no sensitive data in logs. **Grafana Loki** for log aggregation (lightweight, Kubernetes-native, pairs with Grafana dashboards)
10. **SSRF:** No user-controlled URLs passed to backend HTTP calls without allowlist validation

### Testing Strategy
- **Target:** 100% code coverage from the start (enforced in CI)
- **Framework:** pytest
- **Unit Tests:** All services, models, schemas tested in isolation
- **Integration Tests:** API endpoint tests with test database
- **Security Tests:** Auth bypass attempts, injection attempts, IDOR checks
- **Fixtures:** Factory pattern (factory_boy) for test data
- **Database:** Separate test PostgreSQL database, transactions rolled back per test
- **Mocking:** unittest.mock for external services
- **Coverage:** pytest-cov, fail CI if coverage drops below 100%

### Git Workflow
- **Solo developer workflow** (just you + AI pair programming)
- **Branching:** `main` (stable) ← `develop` (integration) ← `feature/<name>` branches
- **Commits:** Conventional Commits format: `feat:`, `fix:`, `test:`, `docs:`, `chore:`, `security:`
- **PRs:** Feature branches merged to develop via PR (even solo — creates audit trail)
- **Tags:** Semantic versioning (v0.1.0, v0.2.0, etc.)
- **Protected branches:** main (no direct pushes)

---

## Domain Context

### What is Whatnot?
- A **live-selling/auction platform** where sellers stream live shows and sell items in real-time
- Sellers schedule "shows" (live streams) where they list items, and buyers bid or buy instantly
- Categories include: trading cards, sports cards, Pokémon, comics, sneakers, vintage clothing, toys, electronics, and more
- Whatnot takes a percentage of each sale (seller fees)
- Sellers often manage hundreds or thousands of unique items (especially in cards/collectibles)

### Seller Pain Points WhatTools Solves
1. **Inventory chaos** — Sellers track items in spreadsheets, notebooks, or not at all. They need to know what they have, what it cost, and where it is.
2. **Profit opacity** — After Whatnot fees, shipping costs, packaging, and cost of goods, sellers often don't know if they're actually profitable.
3. **Shipping inefficiency** — After a show, sellers manually create shipping labels one by one. Bulk label generation saves hours.
4. **No analytics** — Sellers don't know which items/categories perform best, what time to stream, or who their best buyers are.
5. **Show planning** — No tools exist to help plan show lineups, estimate revenue, or schedule across time zones.

### Whatnot API Integration Vision
WhatTools should fully leverage the Whatnot Seller API to cover **every available feature/endpoint**. The goal is not just to mirror Whatnot's capabilities, but to **improve upon them** — making things easier, faster, and smarter for sellers:
- **Auto-sync sales data** — No manual entry; pull orders, shows, and financials automatically
- **Enhanced show planning** — Use historical Whatnot data to suggest optimal show times, categories, and pricing
- **Smarter inventory** — Auto-match sold items, flag low stock, suggest restocks based on sell-through rate
- **Bulk operations Whatnot doesn't offer** — Batch listing, batch pricing updates, batch relisting
- **Unified dashboard** — Aggregate data Whatnot shows across multiple screens into one clear view
- **Alerts & automations** — Ship-by deadline reminders, low-stock alerts, price-drop suggestions based on comps
- **Better reporting** — Whatnot's seller dashboard is limited; WhatTools provides deep analytics, export, and trend analysis

> **Principle:** Anywhere Whatnot's native seller experience is clunky, slow, or limited — WhatTools should be the superior alternative.

### Key Domain Terms
- **Show** — A live stream selling session on Whatnot
- **Lot** — A single item or bundle listed for sale during a show
- **Break** — Opening sealed product (cards) live on stream; buyers purchase "spots"
- **Giveaway (GA)** — Free item given to a buyer (loyalty/engagement tool)
- **Comp** — Comparable recent sale price for an item
- **COG / COGS** — Cost of Goods (Sold); what the seller paid for the item
- **GMV** — Gross Merchandise Value; total sales before fees
- **Take Rate** — Whatnot's percentage fee on each sale
- **Ship-by Date** — Deadline to ship after a sale (Whatnot enforces this)

---

## Important Constraints

### Technical
- All services must run in Docker containers (K3S-compatible)
- API responses must follow a consistent JSON envelope: `{"data": ..., "meta": ..., "errors": [...]}`
- All endpoints must be documented in OpenAPI spec (auto-generated)
- No external SaaS dependencies that cost money at MVP (use self-hosted alternatives)
- Multi-tenancy via seller accounts: each seller owns an "account" (org), data isolated by account_id FK
- PostgreSQL and Redis run as their own pods in K3S (scalable independently)
- Two environments only: **dev** (local Docker Compose) and **prod** (K3S cluster)

### Business
- **Freemium model:**
  - **Free tier:** 50 inventory items, 2 team members
  - **Paid tier:** Unlimited inventory items, up to 100 team members
- No Whatnot API integration at launch (users enter data via UI/API manually)
- Must not violate Whatnot's Terms of Service
- User data privacy is paramount (sellers' inventory and financials are sensitive)
- Teams: Sellers can invite team members (employees, assistants) to their account with role-based permissions

### Regulatory
- Must comply with basic data protection (user can delete account + data)
- Payment processing (Stripe) must be PCI-compliant (handled by Stripe's hosted elements)
- Must have Terms of Service and Privacy Policy before public launch

---

## External Dependencies

### APIs
- **Whatnot Seller API** — Full integration with every available endpoint: sales, shows, listings, payouts, shipping. Goal: complete feature parity + enhancements. **API keys and dev access secured.**
- **Shippo or EasyPost** — Shipping label generation and rate comparison
- **Stripe** — Subscription billing for paid tiers
- **SendGrid or Resend** — Transactional emails (verification, password reset, reports) — called from auth service

### Infrastructure Services
- **PostgreSQL 16+** — Primary shared database (self-hosted on K3S, own pod, scalable independently)
- **Redis 7+** — Pub/Sub message broker + caching + Celery task broker (self-hosted on K3S, own pod)
- **Grafana Loki** — Log aggregation (self-hosted on K3S, own pod)
- **Grafana** — Dashboards for logs, metrics, and monitoring (self-hosted on K3S)
- **Traefik** — Ingress controller / reverse proxy (included in K3S)
- **Docker Registry** — Local or GitHub Container Registry for images

---

## Development Phases

### Phase 1: Foundation (MVP Core)
- [ ] Monorepo scaffolding (folder structure, shared libs, Makefile, docker-compose.yml)
- [ ] Auth service: User registration, login, JWT (access + refresh), password reset
- [ ] Account/Team model: seller accounts, invite team members, role-based access (owner/admin/member)
- [ ] Inventory service: Full CRUD for items + categories with COGS tracking
- [ ] CSV import for inventory (bulk onboarding from spreadsheets)
- [ ] Soft deletes with 30-day retention + purge job
- [ ] Audit trail on all mutations
- [ ] API gateway service (routing, rate limiting, CORS)
- [ ] API versioning (`/api/v1/...`)
- [ ] Search and filtering on inventory (by category, name, status, price range)
- [ ] OpenAPI documentation auto-generated per service
- [ ] 100% test coverage, Makefile-driven CI (`make lint test build`)
- [ ] K3S kubectl YAML manifests (all services + PostgreSQL + Redis as pods)
- [ ] Deploy to K3S at whattools.trector.com/api

### Phase 2: Whatnot Sync & Sales Tracking
- [ ] Whatnot API integration: authenticate seller's Whatnot account
- [ ] Auto-sync sales data from Whatnot (orders, show history, payouts)
- [ ] Sale recording (manual entry fallback: item sold, sale price, platform fees)
- [ ] Show/session model (group sales by show date/time)
- [ ] Profit calculator (sale price - COGS - fees - shipping = true profit)
- [ ] Dashboard API endpoints (total revenue, profit, margins, top items)
- [ ] Bulk operations (mark multiple items as sold)
- [ ] Redis Pub/Sub events for sale lifecycle

### Phase 3: Shipping & Fulfillment
- [ ] Shipping integration (Shippo or EasyPost API)
- [ ] Bulk label generation after a show
- [ ] Packing list generation
- [ ] Tracking number storage and buyer notification prep
- [ ] Ship-by date reminders

### Phase 4: Analytics & Insights
- [ ] Sales analytics (by category, time period, show)
- [ ] Profit trend charts (daily/weekly/monthly)
- [ ] Best-selling items and categories
- [ ] Show performance comparison
- [ ] Optimal show time suggestions (based on historical data)
- [ ] Export reports (CSV, PDF)
- [ ] Grafana Loki + Grafana deployment for platform monitoring

### Phase 5: Web UI
- [ ] Frontend framework selection and setup
- [ ] Auth pages (login, register, forgot password)
- [ ] Inventory management UI
- [ ] Sales entry and show management UI
- [ ] Dashboard with charts and KPIs
- [ ] PWA configuration for mobile

### Phase 6: Growth & Monetization
- [ ] Stripe integration for subscriptions
- [ ] Free/Pro/Business tier implementation
- [ ] Usage limits on free tier (50 items, 2 team members)
- [ ] Social auth (Google, Apple)
- [ ] Deep Whatnot API: batch listing, batch pricing, batch relisting
- [ ] Cross-listing support
- [ ] CRM / buyer tracking
- [ ] Smart alerts (ship-by reminders, low stock, price-drop suggestions)
- [ ] Community features (optional)
