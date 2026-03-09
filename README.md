# WhatTools

B2B SaaS platform providing professional-grade tools for [Whatnot](https://www.whatnot.com) live-selling sellers.

## What is WhatTools?

WhatTools helps Whatnot sellers manage inventory, track profitability, analyze sales performance, and streamline shipping — all from a single API-first platform.

## Quick Start

### Prerequisites
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Docker & Docker Compose
- K3S (for production deployment)

### Local Development

```bash
# Install dependencies
uv sync --all-extras

# Start all services (PostgreSQL, Redis, Gateway, Auth, Inventory)
make dev-up

# Run database migrations
make db-upgrade

# Seed development data
make db-seed

# Verify everything is running
curl http://localhost:5000/api/v1/health
```

### Running Tests

```bash
# Run full test suite with 100% coverage enforcement
make test

# Run all CI checks (lint + typecheck + security + test)
make all
```

## Makefile Targets

| Target | Description |
|---|---|
| `make all` | Run all checks (lint + typecheck + security + test) |
| `make lint` | Run Ruff linter and formatter check |
| `make lint-fix` | Auto-fix lint issues and format code |
| `make typecheck` | Run mypy strict type checking |
| `make security-scan` | Run Bandit SAST and Safety dependency scan |
| `make test` | Run pytest with 100% coverage enforcement |
| `make coverage` | Generate HTML coverage report |
| `make build` | Build all Docker images |
| `make dev-up` | Start local dev environment (Docker Compose) |
| `make dev-down` | Stop local dev environment |
| `make dev-logs` | Tail logs from all services |
| `make db-upgrade` | Run database migrations |
| `make db-migrate msg="description"` | Generate new migration |
| `make db-seed` | Seed development database |
| `make deploy` | Deploy to K3S (prod) |
| `make deploy-status` | Check K3S deployment status |
| `make clean` | Remove caches and build artifacts |

## Project Structure

```
whattools/
├── services/
│   ├── auth/              # Auth service (registration, login, JWT, teams)
│   ├── inventory/         # Inventory service (items, categories, CSV import)
│   ├── gateway/           # API gateway (routing, rate limiting, CORS)
│   └── shared/            # Shared libraries (models, repos, events, logging)
├── k8s/
│   ├── dev/               # Dev K3S overrides
│   └── prod/              # Production kubectl YAML manifests
├── docs/                  # Documentation (architecture, API guide, deployment)
├── openspec/              # OpenSpec change management
├── docker-compose.yml     # Local development environment
├── Makefile               # CI/CD and dev targets
├── pyproject.toml         # Python project config (ruff, mypy, pytest, bandit)
└── README.md
```

## Tech Stack

- **Backend:** Python 3.12+, Flask, SQLAlchemy 2.0, Marshmallow
- **Database:** PostgreSQL 16+
- **Cache/Pub-Sub:** Redis 7+
- **Auth:** JWT (access + refresh tokens)
- **API Docs:** OpenAPI 3.1 (auto-generated via Flask-Smorest)
- **Testing:** pytest, 100% coverage enforced
- **Security:** OWASP Top 10, Bandit SAST, bcrypt password hashing
- **Infrastructure:** Docker, K3S, Traefik ingress

## API

All endpoints are versioned under `/api/v1/`. Full OpenAPI documentation is auto-generated and available at `/api/v1/docs` when the gateway is running.

## License

Proprietary. All rights reserved.
