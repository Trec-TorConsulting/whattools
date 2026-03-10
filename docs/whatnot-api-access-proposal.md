# WhatTools — Whatnot Seller API Access Proposal

**To:** Whatnot Seller API Team (sellerapi@whatnot.com)
**From:** WhatTools (whattools.trector.com)
**Date:** [DATE]
**Subject:** Request for Whatnot Seller API Access — WhatTools B2B Seller Platform

---

## Executive Summary

WhatTools is a B2B SaaS platform purpose-built for Whatnot sellers. We provide professional-grade tools for inventory management, order tracking, profitability analysis, shipping automation, and livestream performance analytics — all from a single dashboard.

We are requesting access to the Whatnot Seller API to offer sellers a seamless, integrated experience that eliminates manual data entry and enables real-time synchronization between their Whatnot stores and WhatTools.

Our integration is **fully built, tested, and production-ready** — we are only waiting on API credentials to go live.

---

## About WhatTools

### What We Do

WhatTools empowers Whatnot sellers of all sizes — from hobbyists to full-time professionals — with tools they currently lack:

- **Inventory Management** — Centralized catalog with categories, cost-of-goods tracking, image management, CSV bulk import, and stock level monitoring
- **Sales & Order Tracking** — Order lifecycle management tied to Whatnot shows, real-time profit margin calculations after fees, shipping, and COGS
- **Profitability Analytics** — Revenue summaries, category performance breakdowns, show-by-show profit analysis, trending item reports, and best-seller identification
- **Shipping Automation** — Shipment creation, label generation, bulk shipping, and packing list production
- **Livestream Performance** — Show-level analytics including total revenue, order count, average order value, and item sell-through rates
- **Team Collaboration** — Multi-user accounts with role-based access (Owner, Admin, Member, Viewer) so sellers can delegate operations to staff

### Who We Serve

Our target users are Whatnot sellers across all categories:

- Trading cards, collectibles, sports memorabilia
- Sneakers, vintage clothing, fashion
- Comics, toys, figurines
- Electronics, home goods
- Sellers who currently rely on spreadsheets, pen-and-paper, or no tracking at all

### Business Model

WhatTools operates on a freemium model:

| | Free | Paid |
|---|---|---|
| Inventory Items | 50 | Unlimited |
| Team Members | 2 | 100 |
| Analytics | Basic | Advanced + Exports |
| CSV Import | ✓ | ✓ |
| **Whatnot Integration** | — | **✓** |
| **Automated Sync & Webhooks** | — | **✓** |
| Priority Support | — | ✓ |

Whatnot integration is a **paid-tier exclusive feature**, ensuring only committed sellers with active subscriptions access the API — which means responsible, well-supported usage.

---

## How We Use the Whatnot Seller API

### OAuth Scopes Requested

| Scope | Purpose |
|-------|---------|
| `read:inventory` | Import products, variants, listings, media, and product taxonomy from Whatnot |
| `write:inventory` | Push new products from WhatTools catalog to Whatnot, sync updates (price, quantity, descriptions), manage listings |
| `read:orders` | Import order history for profitability tracking and analytics |
| `write:orders` | Push tracking numbers (USPS, UPS, FedEx) to Whatnot orders, process cancellations |
| `read:customers` | Associate buyer information with orders for shipping and customer analytics |

### Integration Features

#### 1. Product Synchronization
- **Pull Products** — Import seller's full Whatnot catalog into WhatTools with pagination. Products are linked by `whatnot_product_id` for ongoing sync.
- **Push Products** — Create new Whatnot products directly from the WhatTools inventory, including title, description, weight, taxonomy category, and images.
- **Two-Way Sync** — Update price, quantity, description, and images in either direction. Linked items stay in sync across both platforms.
- **Taxonomy Browsing** — Query Whatnot's product taxonomy tree to assign correct categories when creating products.

#### 2. Listing Management
- View, filter, and paginate all Whatnot listings
- Update listing fields (title, description, price)
- Publish and unpublish listings
- Assign and remove listings from livestreams
- Adjust inventory quantities for buy-it-now listings
- Support for all listing types: Buy It Now, Auction, and Giveaway

#### 3. Order Management
- **Import Orders** — Pull orders from Whatnot with full details: items, pricing, shipping address, customer info, and sales channel (marketplace vs. livestream)
- **Tracking Upload** — Push tracking numbers for USPS, UPS, and FedEx shipments directly to Whatnot orders
- **Cancellation** — Process order cancellations through WhatTools
- **Profit Calculation** — Combine order data with cost-of-goods from inventory to provide true per-item and per-show profit margins

#### 4. Livestream Analytics
- Import livestream records and link them to WhatTools shows
- Track per-show revenue, order count, and sell-through rates
- Historical livestream performance trending

#### 5. Webhook Processing
We consume the following webhook events for real-time updates:

| Event | Action |
|-------|--------|
| `product/sold` | Decrement local inventory, mark items as SOLD when quantity reaches 0 |
| `listing/created` | Update local item with new Whatnot listing ID |
| `listing/updated` | Sync listing changes back to local records |
| `bulk_operation/finished` | Log completion of bulk sync operations |

---

## Technical Architecture

### Platform Overview

WhatTools is a microservices architecture built with production-grade practices:

```
Architecture:
├── API Gateway          — Request routing, rate limiting (60 req/min), CORS, structured logging
├── Auth Service         — JWT auth, team management, Stripe billing
├── Inventory Service    — Item CRUD, categories, CSV import, tier enforcement
├── Sales Service        — Orders, shows, profit tracking
├── Analytics Service    — Revenue summaries, trends, category performance
├── Shipping Service     — Shipments, label generation, packing lists
├── Whatnot Service      — OAuth, product sync, order sync, webhooks, listings
└── Whatnot Worker       — Background sync jobs via Celery + Redis

Infrastructure:
├── PostgreSQL 16        — Primary database
├── Redis                — Caching, rate limiting, pub/sub, task queue
├── Docker               — Containerized services
└── K3S / Kubernetes     — Production orchestration
```

### Whatnot Service Architecture

The Whatnot integration is a dedicated microservice with the following components:

- **OAuth Service** — Handles the full Authorization Code flow, token storage, and automatic refresh
- **GraphQL Client** — Typed client for the Whatnot Seller API with built-in rate limiting (10 req/sec token bucket)
- **Product, Order, Listing, Livestream Services** — Domain-specific sync logic with pagination handling
- **Webhook Handler** — Signature validation, idempotent event processing, audit logging
- **Background Workers** — Celery tasks for async sync operations, scheduled data refresh

### Security Measures

We take security seriously and have implemented industry-standard protections:

| Measure | Implementation |
|---------|---------------|
| **Token Encryption** | OAuth tokens encrypted at rest using Fernet symmetric encryption (AES-128-CBC with HMAC-SHA256) via the `cryptography` library. Encryption key stored as environment variable, never in code. |
| **Proactive Token Refresh** | Tokens refreshed automatically when within 5 minutes of expiry. Failed refresh gracefully deactivates the connection. |
| **Webhook Signature Validation** | All incoming webhooks validated using HMAC-SHA256 with constant-time comparison (`hmac.compare_digest`). Invalid signatures rejected immediately. |
| **Idempotent Webhook Processing** | Every webhook event ID is tracked in the database. Duplicate events are detected and skipped to prevent double-processing. |
| **OAuth State (CSRF) Protection** | Random state tokens generated per authorization request and validated on callback. |
| **Rate Limiting** | Client-side token bucket rate limiter enforcing Whatnot's 10 req/sec limit. Gateway-level rate limiting at 60 req/min per client. |
| **JWT Authentication** | All API endpoints protected by JWT tokens (15-minute access, 7-day refresh with DB-backed revocation). |
| **Role-Based Access Control** | Team roles (Owner, Admin, Member, Viewer) with appropriate permission gates on all operations. |
| **No Plaintext Credentials** | Tokens never logged, never returned in API responses, decrypted only on-demand for API calls. |

### API Compliance

- **Rate Limiting** — Our GraphQL client implements a token bucket rate limiter that respects Whatnot's 10 req/sec limit
- **Pagination** — All list queries use cursor-based pagination as specified in the Seller API documentation
- **Error Handling** — GraphQL `userErrors` are parsed and surfaced; transport errors trigger appropriate retries or user notifications
- **Staging Support** — Our client supports both production (`api.whatnot.com`) and staging (`api.stage.whatnot.com`) environments

---

## Integration Readiness

Our Whatnot integration is **fully implemented and tested**. Here is the current status:

| Component | Status |
|-----------|--------|
| OAuth Authorization Code flow | ✅ Complete |
| Token encryption & auto-refresh | ✅ Complete |
| GraphQL client with rate limiting | ✅ Complete |
| Product sync (pull/push/two-way) | ✅ Complete |
| Listing management (CRUD, publish/unpublish) | ✅ Complete |
| Order sync & tracking upload | ✅ Complete |
| Livestream import | ✅ Complete |
| Webhook handler (HMAC validation, idempotency) | ✅ Complete |
| Background sync workers (Celery) | ✅ Complete |
| Frontend UI (dashboard, settings, listings, callback) | ✅ Complete |
| Database migrations | ✅ Complete |
| Backend test suite | ✅ 688 tests passing |
| Frontend test suite | ✅ 79 tests passing |
| 100% code coverage enforcement | ✅ Active |
| Security scanning (Bandit SAST + Safety) | ✅ Active |
| Strict type checking (mypy) | ✅ Active |

**We are production-ready and only require OAuth credentials (`client_id`, `client_secret`) to activate the integration for our users.**

---

## OAuth Configuration

| Field | Value |
|-------|-------|
| **Application Name** | WhatTools |
| **Application Website** | https://whattools.trector.com |
| **Redirect URI(s)** | `https://whattools.trector.com/whatnot/callback` |
| **Scopes Requested** | `read:inventory write:inventory read:orders write:orders read:customers` |
| **Webhook Endpoint** | `https://whattools.trector.com/api/v1/whatnot/webhooks` |

---

## Value to the Whatnot Ecosystem

WhatTools directly benefits the Whatnot platform and its sellers:

1. **Seller Retention** — Professional tools reduce friction and help sellers run sustainable businesses on Whatnot, increasing long-term platform retention.

2. **Seller Growth** — Better inventory and profit visibility helps sellers make smarter purchasing and pricing decisions, leading to more and higher-quality listings.

3. **Operational Efficiency** — Automated sync eliminates manual data entry. Sellers spend less time on operations and more time on selling.

4. **Shipping Speed** — Integrated tracking upload means buyers get tracking numbers faster, improving the buyer experience and platform ratings.

5. **Data Accuracy** — Real-time inventory sync via webhooks prevents overselling and stock discrepancies, reducing customer complaints and cancellations.

6. **Platform Ecosystem** — Third-party tools like WhatTools strengthen Whatnot's competitive position by offering sellers an ecosystem of professional services, similar to how Shopify apps enrich that platform.

---

## Requested Next Steps

1. **API Credentials** — Issue OAuth `client_id` and `client_secret` for WhatTools
2. **Webhook Registration** — Register our webhook endpoint for `product/sold`, `listing/created`, `listing/updated`, and `bulk_operation/finished` events
3. **Staging Access** — If available, provide staging environment credentials for integration testing before production launch
4. **Technical Review** — We welcome any review of our integration architecture and are happy to answer technical questions or make adjustments per your requirements

---

## Contact

**Application:** WhatTools
**Website:** https://whattools.trector.com
**Email:** [YOUR_EMAIL]
**Name:** [YOUR_NAME]

We're excited about the opportunity to enhance the Whatnot seller experience and look forward to your response.
