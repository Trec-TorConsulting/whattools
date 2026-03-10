# Change: Full Whatnot Seller API Integration + Stripe Billing

## Why
WhatTools currently requires 100% manual data entry — sellers re-type orders, products, and show details that already exist in Whatnot. This defeats the value proposition. The Whatnot Seller API (GraphQL) provides full read/write access to products, listings, orders, livestreams, and webhooks. Integrating it eliminates manual work, enables real-time sync, and unlocks features impossible without API access (batch listing, live inventory sync, automatic order import). Stripe billing enables the freemium model needed for monetization.

## What Changes

### 1. Whatnot OAuth + Account Linking (new service: `services/whatnot/`)
- OAuth 2.0 Authorization Code flow with Whatnot
- Encrypted credential storage per seller account (client_id, tokens)
- Token refresh lifecycle (24h access, 1yr refresh)
- Scope-based authorization: `read:inventory`, `write:inventory`, `read:orders`, `write:orders`, `read:customers`
- "Connect Whatnot" and "Disconnect" flows

### 2. Whatnot GraphQL Client (new shared module)
- GraphQL client for `POST https://api.whatnot.com/seller-api/graphql`
- Rate limiting (max 10 req/sec per Whatnot's rules)
- Automatic token refresh on 401
- Error handling with Whatnot's `userErrors` pattern
- Bulk operation support (JSONL export/import)

### 3. Product Sync (bidirectional)
- Pull products from Whatnot → local inventory (with variants, listings, media)
- Push new products from WhatTools → Whatnot (with images, taxonomy, attributes)
- Map WhatTools inventory items ↔ Whatnot products via `externalId`
- Product taxonomy support (Whatnot's category tree)
- Product attributes (boolean, enum, string, int, float)
- Product images/media management
- Batch import/export via bulk operations

### 4. Listing Management
- Support three listing types: BuyItNow, Auction, Giveaway
- Create/update/delete/publish/unpublish listings
- Assign/remove listings to/from livestreams
- Adjust inventory quantities
- Track listing status: ACTIVE, INACTIVE, SOLD, SOLD_OUT

### 5. Order Sync (from Whatnot)
- Auto-import orders with full details (items, pricing, customer, address)
- Map to existing WhatTools order model with enhanced fields
- Track order status: PENDING → CREATED → PROCESSING → COMPLETED/CANCELLED/FAILED
- Push tracking codes back to Whatnot (`addTrackingCode` mutation)
- Cancel orders on Whatnot (`orderCancel` mutation)
- Support pickup orders (`isPickup` flag)
- Giveaway order tracking (`isGiveaway` flag)
- Sales channel tracking (MARKETPLACE vs LIVESTREAM)

### 6. Livestream Sync
- Import livestream data from Whatnot
- Link orders to livestreams
- Map to existing WhatTools "shows" model
- Track `numOrders` per livestream

### 7. Webhook Receiver
- Endpoint to receive Whatnot webhook POST requests
- HMAC SHA256 signature validation (`X-Whatnot-Webhook-Signature`)
- Handle topics: `product/sold`, `bulk_operation/finished`, `listing/created`, `listing/updated`
- Real-time inventory decrements on `product/sold`
- Webhook event log with retry tracking

### 8. Background Sync Workers (Celery)
- Periodic full product sync (configurable interval)
- Periodic order sync
- Periodic livestream sync
- Bulk operation polling (check completion status)
- One-time initial sync on account connection

### 9. Stripe Billing
- Stripe Checkout for subscription creation
- Stripe Customer Portal for self-service management
- Webhook handler for Stripe events (subscription.created, updated, cancelled, invoice.paid, etc.)
- Free tier: 50 inventory items, 2 team members
- Paid tier: unlimited items, 100 team members
- Tier enforcement on item creation and team invites

### 10. Updated Shipping Model
- Remove `ManualProvider` stub
- Shipping handled by Whatnot (tracking codes pushed via API)
- Carrier support: USPS, UPS, FEDEX (per Whatnot's `AddTrackingCodeInput`)
- Remove Shippo/EasyPost dependency (Whatnot manages shipping)

### 11. Web UI — New Pages
- **Whatnot Connection**: OAuth connect/disconnect, connection status, sync controls
- **Sync Dashboard**: Last sync time, sync status, error log, manual "Sync Now"
- **Product Management**: Push/pull products, image upload, taxonomy picker, variant management
- **Listing Management**: Create BuyItNow/Auction/Giveaway, publish/unpublish, assign to livestream
- **Enhanced Orders**: Auto-synced orders with Whatnot details, push tracking, cancel
- **Billing/Subscription**: Plan display, upgrade/downgrade, billing history
- **Notification Center**: Sync events, webhook events, alerts

### 12. **BREAKING** Model Changes
- Inventory items get `whatnot_product_id`, `whatnot_variant_id`, variant support, image URLs
- Orders get `whatnot_order_id`, enhanced status enum, sales channel, giveaway flag
- Shows become "Livestreams" internally mapped to Whatnot livestream objects
- New models: WhatnotCredential, WhatnotSyncLog, WebhookEvent, Subscription, ListingRecord

## Impact
- Affected specs: inventory, sales, shipping, analytics, auth (all services)
- New service: `services/whatnot/` (OAuth, GraphQL client, sync workers, webhooks)
- New shared modules: `services/shared/whatnot_client.py`, `services/shared/stripe_client.py`
- Database: ~8 new tables, ~15 column additions to existing tables
- New dependencies: `gql`, `stripe`, `cryptography` (for token encryption)
- Environment variables: `WHATNOT_CLIENT_ID`, `WHATNOT_CLIENT_SECRET`, `WHATNOT_WEBHOOK_SECRET`, `WHATNOT_REDIRECT_URI`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID_PAID`, `ENCRYPTION_KEY`
