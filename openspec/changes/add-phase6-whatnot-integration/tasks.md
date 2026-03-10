## 1. Whatnot Service Foundation
- [ ] 1.1 Create `services/whatnot/` service structure (Flask app, blueprints, models)
- [ ] 1.2 Add new dependencies: `httpx`, `cryptography`, `stripe`
- [ ] 1.3 Create WhatnotCredential model (encrypted token storage)
- [ ] 1.4 Create SyncLog model (sync history tracking)
- [ ] 1.5 Create WebhookEvent model (idempotent event processing)
- [ ] 1.6 Create Subscription model (Stripe billing state)
- [ ] 1.7 Generate Alembic migrations for new tables
- [ ] 1.8 Add nullable Whatnot columns to existing inventory/order/show tables
- [ ] 1.9 Generate Alembic migrations for altered tables
- [ ] 1.10 Register whatnot service in gateway routing
- [ ] 1.11 Update docker-compose.yml with whatnot service

## 2. GraphQL Client
- [ ] 2.1 Build `graphql/client.py` — HTTP client with Bearer auth, rate limiting, error handling
- [ ] 2.2 Build `graphql/queries.py` — all read queries (products, variants, listings, orders, livestreams, taxonomy, me)
- [ ] 2.3 Build `graphql/mutations.py` — all write mutations (productCreate/Update/Delete, listing ops, tracking, order cancel, bulk ops, media, upload)

## 3. OAuth Flow
- [ ] 3.1 Create `routes/oauth.py` — authorize redirect, callback handler, disconnect
- [ ] 3.2 Create `services/oauth_service.py` — token exchange, refresh, encrypt/decrypt, scope management
- [ ] 3.3 Add `GET /api/v1/whatnot/connect` — initiate OAuth flow
- [ ] 3.4 Add `GET /api/v1/whatnot/callback` — handle OAuth callback
- [ ] 3.5 Add `POST /api/v1/whatnot/disconnect` — revoke and delete credentials
- [ ] 3.6 Add `GET /api/v1/whatnot/status` — connection status and scopes

## 4. Product Sync
- [ ] 4.1 Create `services/product_service.py` — pull products from Whatnot, map to inventory items
- [ ] 4.2 Implement product pull (Whatnot → WhatTools) with variant/listing/media mapping
- [ ] 4.3 Implement product push (WhatTools → Whatnot) with taxonomy, images, attributes
- [ ] 4.4 Implement product update sync (bidirectional conflict resolution)
- [ ] 4.5 Implement product delete sync
- [ ] 4.6 Add `POST /api/v1/whatnot/products/pull` — manual product import
- [ ] 4.7 Add `POST /api/v1/whatnot/products/push` — push selected items to Whatnot
- [ ] 4.8 Add `GET /api/v1/whatnot/taxonomy` — browse Whatnot category tree
- [ ] 4.9 Add `GET /api/v1/whatnot/taxonomy/{id}/attributes` — get attributes for category

## 5. Listing Management
- [ ] 5.1 Create `services/listing_service.py` — create/update/publish/unpublish listings
- [ ] 5.2 Support BuyItNow listings (price, offerable)
- [ ] 5.3 Support Auction listings (startingPrice, endTime, suddenDeath)
- [ ] 5.4 Support Giveaway listings
- [ ] 5.5 Implement listing publish/unpublish
- [ ] 5.6 Implement listing assign/remove from livestream
- [ ] 5.7 Implement listing quantity adjustment
- [ ] 5.8 Add `POST /api/v1/whatnot/listings` — create listing
- [ ] 5.9 Add `PUT /api/v1/whatnot/listings/{id}` — update listing
- [ ] 5.10 Add `POST /api/v1/whatnot/listings/{id}/publish` — publish
- [ ] 5.11 Add `POST /api/v1/whatnot/listings/{id}/unpublish` — unpublish
- [ ] 5.12 Add `POST /api/v1/whatnot/listings/{id}/assign-livestream` — assign to show
- [ ] 5.13 Add `POST /api/v1/whatnot/listings/{id}/adjust-quantity` — adjust inventory

## 6. Order Sync
- [ ] 6.1 Create `services/order_service.py` — pull orders from Whatnot, map to local orders
- [ ] 6.2 Implement order pull with full details (items, customer, address, pricing)
- [ ] 6.3 Implement tracking code push (`addTrackingCode` mutation)
- [ ] 6.4 Implement order cancel (`orderCancel` mutation)
- [ ] 6.5 Add `POST /api/v1/whatnot/orders/sync` — manual order sync
- [ ] 6.6 Add `POST /api/v1/whatnot/orders/{id}/tracking` — push tracking to Whatnot
- [ ] 6.7 Add `POST /api/v1/whatnot/orders/{id}/cancel` — cancel on Whatnot

## 7. Livestream Sync
- [ ] 7.1 Create `services/livestream_service.py` — pull livestreams, map to shows
- [ ] 7.2 Implement livestream pull and mapping
- [ ] 7.3 Add `POST /api/v1/whatnot/livestreams/sync` — manual livestream sync

## 8. Webhooks
- [ ] 8.1 Create `routes/webhooks.py` — POST endpoint for Whatnot webhooks
- [ ] 8.2 Implement HMAC SHA256 signature validation
- [ ] 8.3 Handle `product/sold` — decrement inventory, create order
- [ ] 8.4 Handle `bulk_operation/finished` — process bulk operation results
- [ ] 8.5 Handle `listing/created` — sync new listing data
- [ ] 8.6 Handle `listing/updated` — sync listing changes
- [ ] 8.7 Implement idempotent processing (event ID dedup)

## 9. Background Sync Workers
- [ ] 9.1 Create `tasks/sync_tasks.py` with Celery beat schedule
- [ ] 9.2 Implement periodic order sync (every 15 min)
- [ ] 9.3 Implement periodic product sync (every hour)
- [ ] 9.4 Implement periodic livestream sync (every hour)
- [ ] 9.5 Implement initial full sync on account connection
- [ ] 9.6 Implement bulk operation status polling
- [ ] 9.7 Add `POST /api/v1/whatnot/sync/now` — trigger immediate full sync
- [ ] 9.8 Add `GET /api/v1/whatnot/sync/status` — get sync history/status

## 10. Stripe Billing
- [ ] 10.1 Create routes for Stripe in auth service (`routes/billing.py`)
- [ ] 10.2 Create `services/billing_service.py` — checkout, portal, webhook handling
- [ ] 10.3 Add `POST /api/v1/billing/checkout` — create Stripe Checkout session
- [ ] 10.4 Add `GET /api/v1/billing/portal` — create Stripe Customer Portal session
- [ ] 10.5 Add `POST /api/v1/billing/webhook` — Stripe webhook handler
- [ ] 10.6 Add `GET /api/v1/billing/subscription` — get current subscription status
- [ ] 10.7 Implement tier enforcement on item creation (free: 50 items)
- [ ] 10.8 Implement tier enforcement on team invites (free: 2 members)
- [ ] 10.9 Update account model with `stripe_customer_id`, `subscription_status`, `plan_tier`

## 11. Shipping Updates
- [ ] 11.1 Update shipping service to support Whatnot tracking code push
- [ ] 11.2 Validate carrier values (USPS, UPS, FEDEX per Whatnot API)
- [ ] 11.3 Remove ManualProvider stub, add WhatnotShippingProvider
- [ ] 11.4 Auto-push tracking on shipment status change

## 12. Existing Model Updates
- [ ] 12.1 Add `whatnot_product_id`, `whatnot_variant_id`, `whatnot_listing_id`, `image_urls` to inventory items
- [ ] 12.2 Add `whatnot_order_id`, `whatnot_customer_id`, `sales_channel`, `is_giveaway`, `is_pickup` to orders
- [ ] 12.3 Add `whatnot_livestream_id` to shows
- [ ] 12.4 Update schemas/serialization for new fields
- [ ] 12.5 Update inventory service to handle Whatnot-linked items
- [ ] 12.6 Update sales service to handle Whatnot-sourced orders

## 13. Web UI — Whatnot Connection
- [ ] 13.1 Create Whatnot settings page (`/settings/whatnot`)
- [ ] 13.2 "Connect Whatnot" button → OAuth redirect
- [ ] 13.3 OAuth callback page → success/error display
- [ ] 13.4 Connection status indicator (connected/disconnected, scopes, last sync)
- [ ] 13.5 "Disconnect" button with confirmation

## 14. Web UI — Sync Dashboard
- [ ] 14.1 Create sync dashboard page or section
- [ ] 14.2 Last sync timestamps per type (products, orders, livestreams)
- [ ] 14.3 "Sync Now" button per type + "Sync All"
- [ ] 14.4 Sync history table (time, type, status, items synced, errors)
- [ ] 14.5 Error log with details

## 15. Web UI — Product Management
- [ ] 15.1 Add "Import from Whatnot" button on inventory page
- [ ] 15.2 Add "Push to Whatnot" button on item detail/list
- [ ] 15.3 Product image upload component (temp local → push to Whatnot)
- [ ] 15.4 Taxonomy picker (hierarchical category browser)
- [ ] 15.5 Variant management UI (options, SKU per variant)
- [ ] 15.6 Whatnot sync indicator on each item (synced/local only/out of date)

## 16. Web UI — Listing Management
- [ ] 16.1 Create listings page (`/listings`)
- [ ] 16.2 Create listing form (BuyItNow/Auction/Giveaway tabs)
- [ ] 16.3 Listing status badges (ACTIVE, INACTIVE, SOLD, SOLD_OUT)
- [ ] 16.4 Publish/unpublish actions
- [ ] 16.5 Assign to livestream action
- [ ] 16.6 Adjust quantity action
- [ ] 16.7 Link to Whatnot listing URL

## 17. Web UI — Enhanced Orders
- [ ] 17.1 Update order list to show Whatnot-synced orders with source badge
- [ ] 17.2 Order detail with customer info (username, display name)
- [ ] 17.3 Shipping address display (from Whatnot `read:customers` scope)
- [ ] 17.4 "Push Tracking" button on order detail
- [ ] 17.5 "Cancel on Whatnot" button with confirmation
- [ ] 17.6 Sales channel filter (MARKETPLACE/LIVESTREAM)
- [ ] 17.7 Giveaway order indicator

## 18. Web UI — Billing
- [ ] 18.1 Create billing page (`/settings/billing`)
- [ ] 18.2 Current plan display with tier details
- [ ] 18.3 "Upgrade to Paid" button → Stripe Checkout redirect
- [ ] 18.4 "Manage Subscription" button → Stripe Customer Portal
- [ ] 18.5 Usage display (items used / limit, members used / limit)
- [ ] 18.6 Upgrade prompts when hitting limits

## 19. Web UI — Notifications
- [ ] 19.1 Add notification indicator to app shell header
- [ ] 19.2 Notification dropdown with recent events
- [ ] 19.3 Notification types: sync complete, sync error, product sold (webhook), limit warning

## 20. Tests
- [ ] 20.1 Unit tests for GraphQL client (queries, mutations, error handling)
- [ ] 20.2 Unit tests for OAuth service (token exchange, refresh, encryption)
- [ ] 20.3 Unit tests for product sync service
- [ ] 20.4 Unit tests for listing service
- [ ] 20.5 Unit tests for order sync service
- [ ] 20.6 Unit tests for livestream sync service
- [ ] 20.7 Unit tests for webhook handler (signature validation, all topics)
- [ ] 20.8 Unit tests for Stripe billing service
- [ ] 20.9 Integration tests for all new API endpoints
- [ ] 20.10 Integration tests for webhook endpoint
- [ ] 20.11 Integration tests for OAuth flow
- [ ] 20.12 Update existing inventory/sales/shipping tests for new fields
- [ ] 20.13 Frontend tests for new components (Vitest)
- [ ] 20.14 E2E tests for critical flows (Playwright)
- [ ] 20.15 Verify 100% coverage maintained
