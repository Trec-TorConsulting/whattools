# Change: Add Phase 1 Foundation (MVP Core)

## Why
WhatTools has no codebase yet. This change establishes the entire foundation: monorepo structure, microservices scaffolding, authentication system, inventory management, API gateway, and deployment infrastructure. Without this, no subsequent features can be built.

## What Changes
- Add monorepo scaffolding with services/, k8s/, docs/ folder structure
- Add **auth service**: user registration, login, JWT auth, password reset, email verification, team/account management with role-based access (owner/admin/member)
- Add **inventory service**: full CRUD for items and categories, COGS tracking, CSV import with user-driven column mapping, search/filtering
- Add **API gateway service**: lightweight Flask reverse proxy, routing, rate limiting, CORS, API versioning (/api/v1/)
- Add **shared infrastructure**: PostgreSQL database models (soft deletes, audit trail), Redis Pub/Sub event system, health checks, structured logging
- Add Makefile with all CI targets (lint, test, type-check, security-scan, build, deploy)
- Add Docker Compose for local development
- Add K3S kubectl YAML manifests for production deployment (all services + PostgreSQL + Redis as pods)
- Add OpenAPI auto-generated documentation per service
- Enforce 100% test coverage from the start

## Impact
- Affected specs: auth, inventory, api-gateway, shared-infrastructure (all new)
- Affected code: entire codebase (greenfield)
- **BREAKING**: N/A (no existing system)
- Risk: Microservices add complexity vs monolith; mitigated by shared database and simple pub/sub patterns
