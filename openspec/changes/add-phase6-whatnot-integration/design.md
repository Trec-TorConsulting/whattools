## Context
WhatTools is a B2B SaaS for Whatnot sellers with a complete internal API (auth, inventory, sales, analytics, shipping) and React web UI. Currently all data is manually entered. This change integrates the real Whatnot Seller API (GraphQL) for bidirectional data sync, adds Stripe billing for freemium monetization, and updates the web UI for all new capabilities.

### Key Technical Facts
- Whatnot Seller API is **GraphQL** at `POST https://api.whatnot.com/seller-api/graphql`
- OAuth 2.0 Authorization Code flow for 3rd-party access
- Access tokens expire in 24 hours, refresh tokens in 1 year
- Rate limit: 10 requests/second, bulk operations for large datasets
- Webhooks: HMAC SHA256 signature validation
- Shipping is handled by Whatnot — WhatTools only needs to push tracking codes (USPS/UPS/FedEx)

## Goals
- 100% coverage of Whatnot Seller API endpoints (all queries and mutations)
- Bidirectional product/listing sync
- Automatic order import with real-time webhook updates
- Stripe-powered freemium billing with tier enforcement
- Full UI coverage for all new backend features

## Non-Goals
- Whatnot buyer-side features (only seller API)
- Custom shipping label generation (Whatnot handles labels)
- Real-time streaming integration (Whatnot doesn't expose this)
- Payout/financial data (not available in current Whatnot API)

## Architecture Decisions

### 1. New `services/whatnot/` Service
A dedicated Flask microservice following existing service patterns:
```
services/whatnot/
├── __init__.py
├── routes/
│   ├── __init__.py
│   ├── oauth.py          # OAuth flow endpoints
│   ├── sync.py           # Manual sync triggers
│   ├── webhooks.py       # Webhook receiver
│   └── products.py       # Product/listing push operations
├── services/
│   ├── __init__.py
│   ├── oauth_service.py
│   ├── sync_service.py
│   ├── product_service.py
│   ├── listing_service.py
│   ├── order_service.py
│   └── livestream_service.py
├── models/
│   ├── __init__.py
│   └── models.py         # WhatnotCredential, SyncLog, WebhookEvent
├── schemas/
│   ├── __init__.py
│   └── schemas.py
├── repositories/
│   ├── __init__.py
│   └── whatnot_repository.py
├── tasks/
│   ├── __init__.py
│   ├── celery_app.py
│   └── sync_tasks.py     # Periodic sync workers
└── graphql/
    ├── __init__.py
    ├── client.py          # GraphQL HTTP client with auth
    ├── queries.py         # All query strings
    └── mutations.py       # All mutation strings
```

### 2. GraphQL Client (not REST)
Whatnot's API is GraphQL. We'll use `httpx` for HTTP calls with manual query construction (no heavy GQL framework dependency). Queries stored as string constants for clarity and testability.

### 3. Token Encryption
Whatnot OAuth tokens stored encrypted using `cryptography.fernet` with `ENCRYPTION_KEY` env var. Tokens decrypted only at request time, never logged.

### 4. Sync Strategy
- **Initial sync**: On OAuth connection, full pull of products, orders, livestreams
- **Periodic sync**: Celery beat every 15 minutes for orders, hourly for products
- **Real-time**: Webhooks for `product/sold`, `listing/created`, `listing/updated`
- **Manual**: "Sync Now" button triggers immediate full sync
- **Conflict resolution**: Whatnot is source of truth for orders/livestreams; WhatTools is source of truth for local enrichment (COGS, notes, categories)

### 5. Existing Model Changes (Backward Compatible)
Add nullable columns to existing tables rather than breaking changes:
- `inventory_items`: add `whatnot_product_id`, `whatnot_variant_id`, `whatnot_listing_id`, `image_urls` (JSON)
- `orders`: add `whatnot_order_id`, `whatnot_customer_id`, `sales_channel`, `is_giveaway`, `is_pickup`
- `shows`: add `whatnot_livestream_id`, `whatnot_num_orders`

### 6. Stripe Integration
Using Stripe Checkout Sessions for subscription creation and Stripe Customer Portal for management. Webhook-driven status updates (no polling).

### 7. Image Storage
Product images stored temporarily in local filesystem (`data/uploads/`) during product creation workflow. Once pushed to Whatnot via `CreateMediaInput.source` URL, the local copy is the cache. Whatnot-hosted URLs stored in `image_urls` JSON field.

## Risks / Trade-offs
- **Whatnot API is in Developer Preview**: Schema may change. Mitigation: version the GraphQL queries, handle `userErrors` gracefully.
- **Rate limiting at 10 req/sec**: Mitigation: use bulk operations for large syncs, queue mutations.
- **Token expiration**: 24h access tokens require proactive refresh. Mitigation: refresh on every request if within 1h of expiry.
- **Webhook reliability**: Whatnot retries 5 times over ~10 minutes. Mitigation: idempotent webhook handler using event IDs.

## Migration Plan
1. Add new database tables (Alembic migration)
2. Add nullable columns to existing tables (Alembic migration)
3. Deploy new `whatnot` service
4. Users connect Whatnot accounts via OAuth
5. Initial sync populates data
6. Periodic sync keeps data current
7. Stripe billing activation is opt-in (existing users stay on free tier)
