# WhatTools API Guide

## Base URL

All API requests go through the gateway:
- **Local**: `http://localhost:5000/api/v1`
- **Production**: `https://whattools.trector.com/api/v1`

## Authentication Flow

### 1. Register an Account

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "seller@example.com",
  "password": "MyStr0ngP@ss!",
  "account_name": "My Whatnot Store",
  "name": "Jane Seller"
}
```

**Response** (201):
```json
{
  "data": {
    "user_id": "uuid",
    "account_id": "uuid",
    "email": "seller@example.com",
    "name": "Jane Seller",
    "role": "owner",
    "access_token": "eyJ...",
    "refresh_token": "eyJ..."
  },
  "meta": {},
  "errors": []
}
```

### 2. Login

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "seller@example.com",
  "password": "MyStr0ngP@ss!"
}
```

**Response** (200):
```json
{
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "user": {
      "id": "uuid",
      "email": "seller@example.com",
      "name": "Jane Seller",
      "role": "owner",
      "account_id": "uuid"
    }
  },
  "meta": {},
  "errors": []
}
```

### 3. Using Tokens

Include the access token as a Bearer token in all authenticated requests:

```http
GET /api/v1/items
Authorization: Bearer eyJ...
```

### 4. Refresh Tokens

When the access token expires (15 minutes), use the refresh token to get a new pair:

```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ..."
}
```

### 5. Logout

Revokes the refresh token:

```http
POST /api/v1/auth/logout
Authorization: Bearer eyJ...
Content-Type: application/json

{
  "refresh_token": "eyJ..."
}
```

---

## Inventory Management

### List Items

```http
GET /api/v1/items
Authorization: Bearer eyJ...
```

Query parameters:
- `search` — search by name (partial match)
- `status` — filter by status: `available`, `sold`, `reserved`, `listed`
- `category_id` — filter by category UUID
- `cursor` — pagination cursor (UUID of last item)
- `limit` — items per page (default: 20, max: 100)

### Create Item

```http
POST /api/v1/items
Authorization: Bearer eyJ...
Content-Type: application/json

{
  "name": "1986 Topps Baseball Card Set",
  "description": "Complete set, near mint condition",
  "category_id": "uuid",
  "cogs": 45.99,
  "quantity": 1,
  "status": "available"
}
```

### Update Item

```http
PUT /api/v1/items/{item_id}
Authorization: Bearer eyJ...
Content-Type: application/json

{
  "name": "Updated Name",
  "cogs": 49.99
}
```

### Delete Item (Soft Delete)

```http
DELETE /api/v1/items/{item_id}
Authorization: Bearer eyJ...
```

### Restore Deleted Item

```http
POST /api/v1/items/{item_id}/restore
Authorization: Bearer eyJ...
```

### List Deleted Items

```http
GET /api/v1/items/deleted
Authorization: Bearer eyJ...
```

---

## Categories

### List Categories

```http
GET /api/v1/categories
Authorization: Bearer eyJ...
```

### Create Category

```http
POST /api/v1/categories
Authorization: Bearer eyJ...
Content-Type: application/json

{
  "name": "Trading Cards",
  "description": "Sports and collectible trading cards"
}
```

---

## CSV Import

### Step 1: Upload CSV

```http
POST /api/v1/csv/upload
Authorization: Bearer eyJ...
Content-Type: multipart/form-data

file: items.csv
```

**Response**: Returns job ID with detected headers and preview rows.

### Step 2: Submit Column Mapping

```http
POST /api/v1/csv/{job_id}/map
Authorization: Bearer eyJ...
Content-Type: application/json

{
  "column_mapping": {
    "Item Name": "name",
    "Price Paid": "cogs",
    "Qty": "quantity",
    "Type": "category_name"
  }
}
```

### Step 3: Check Import Status

```http
GET /api/v1/csv/{job_id}
Authorization: Bearer eyJ...
```

---

## Team Management

### Invite a Team Member

```http
POST /api/v1/account/invite
Authorization: Bearer eyJ...
Content-Type: application/json

{
  "email": "assistant@example.com",
  "role": "member"
}
```

### List Team Members

```http
GET /api/v1/account/members
Authorization: Bearer eyJ...
```

### Update Member Role

```http
PUT /api/v1/account/members/{user_id}/role
Authorization: Bearer eyJ...
Content-Type: application/json

{
  "role": "admin"
}
```

### Remove Team Member

```http
DELETE /api/v1/account/members/{user_id}
Authorization: Bearer eyJ...
```

---

## Shows (Sales)

### Create Show

```http
POST /api/v1/shows
Authorization: Bearer eyJ...
Content-Type: application/json

{
  "title": "Friday Night Cards",
  "platform": "whatnot",
  "scheduled_at": "2026-03-14T20:00:00Z",
  "notes": "Sports cards auction"
}
```

### List Shows

```http
GET /api/v1/shows
Authorization: Bearer eyJ...
```

Query parameters:
- `status` — filter by status: `planned`, `live`, `completed`, `cancelled`
- `cursor` — pagination cursor (UUID of last show)
- `limit` — items per page (default: 20, max: 100)

### Show Lifecycle

```http
POST /api/v1/shows/{show_id}/start      # planned → live
POST /api/v1/shows/{show_id}/complete    # live → completed
POST /api/v1/shows/{show_id}/cancel      # planned/live → cancelled
```

Cancelling a show also cancels all pending orders and restores inventory items to available.

---

## Orders (Sales)

### Create Order

```http
POST /api/v1/orders
Authorization: Bearer eyJ...
Content-Type: application/json

{
  "show_id": "uuid",
  "inventory_item_id": "uuid",
  "sale_price": 49.99,
  "platform_fees": 5.00,
  "shipping_cost": 3.50,
  "buyer_username": "buyer123",
  "notes": "Paid via PayPal"
}
```

Profit is automatically calculated as: `sale_price - platform_fees - shipping_cost - item.cogs`

### List Orders

```http
GET /api/v1/orders
Authorization: Bearer eyJ...
```

Query parameters:
- `status` — filter by status: `pending`, `shipped`, `delivered`, `cancelled`
- `show_id` — filter by show UUID
- `cursor` — pagination cursor
- `limit` — items per page (default: 20, max: 100)

### Cancel Order

```http
POST /api/v1/orders/{order_id}/cancel
Authorization: Bearer eyJ...
```

Cancelling restores the inventory item to available status.

### Soft Delete / Restore

```http
DELETE /api/v1/orders/{order_id}
POST /api/v1/orders/{order_id}/restore
GET /api/v1/orders/deleted
```

---

## Analytics

All analytics endpoints require authentication and return account-scoped data.

### Revenue Summary

```http
GET /api/v1/analytics/summary?period=30d
Authorization: Bearer eyJ...
```

Query parameters:
- `period` — `7d`, `30d`, `90d`, `365d`, `all` (default: `30d`)

**Response** (200):
```json
{
  "data": {
    "period": "30d",
    "order_count": 47,
    "total_revenue": 2350.00,
    "total_cogs": 940.00,
    "total_fees": 235.00,
    "total_shipping": 188.00,
    "gross_profit": 1410.00,
    "net_profit": 987.00,
    "margin_percent": 42.0,
    "average_order_value": 50.0,
    "sell_through_rate": 68.5
  }
}
```

### Category Performance

```http
GET /api/v1/analytics/categories?period=30d
Authorization: Bearer eyJ...
```

### Show Performance

```http
GET /api/v1/analytics/shows?period=30d
Authorization: Bearer eyJ...
```

### Revenue Trends

```http
GET /api/v1/analytics/trends?period=30d&granularity=day
Authorization: Bearer eyJ...
```

Query parameters:
- `period` — `7d`, `30d`, `90d`, `365d`, `all`
- `granularity` — `day`, `week`, `month` (default: `day`)

### Top Selling Items

```http
GET /api/v1/analytics/top-items?period=30d&sort_by=revenue&limit=10
Authorization: Bearer eyJ...
```

Query parameters:
- `period` — `7d`, `30d`, `90d`, `365d`, `all`
- `sort_by` — `revenue`, `profit`, `quantity` (default: `revenue`)
- `limit` — 1-100 (default: 10)

### Show Time Suggestions

```http
GET /api/v1/analytics/show-time-suggestions
Authorization: Bearer eyJ...
```

Returns actionable scheduling recommendations based on historical show performance. Requires at least 3 completed shows.

**Response** (200):
```json
{
  "data": {
    "total_shows_analyzed": 15,
    "recommendations": [
      {
        "rank": 1,
        "day_of_week": "Friday",
        "hour": 19,
        "label": "Friday 7:00 PM",
        "score": 0.95,
        "avg_revenue": 450.00,
        "avg_profit": 280.00,
        "avg_orders": 12.5,
        "show_count": 4
      }
    ],
    "avoid_slots": [
      {
        "day_of_week": "Monday",
        "hour": 10,
        "label": "Monday 10:00 AM",
        "avg_revenue": 50.00,
        "avg_profit": -5.00,
        "show_count": 2
      }
    ],
    "category_insights": [
      {
        "category": "Trading Cards",
        "best_day": "Saturday",
        "best_hour": 20,
        "avg_profit": 350.00
      }
    ]
  }
}
```

---

## Report Exports

Async report generation via Celery worker. Supports CSV and PDF formats with embedded charts.

### Create Export

```http
POST /api/v1/analytics/exports
Authorization: Bearer eyJ...
Content-Type: application/json

{
  "report_type": "full",
  "format": "pdf",
  "period": "30d"
}
```

Valid `report_type` values: `summary`, `categories`, `shows`, `trends`, `top_items`, `full`
Valid `format` values: `csv`, `pdf`
Valid `period` values: `7d`, `30d`, `90d`, `365d`, `all`

**Response** (201):
```json
{
  "data": {
    "id": "uuid",
    "report_type": "full",
    "format": "pdf",
    "period": "30d",
    "status": "pending",
    "file_size": 0,
    "expires_at": "2025-01-22T12:00:00Z",
    "created_at": "2025-01-15T12:00:00Z"
  }
}
```

### List Exports

```http
GET /api/v1/analytics/exports
Authorization: Bearer eyJ...
```

### Get Export Status

```http
GET /api/v1/analytics/exports/{export_id}
Authorization: Bearer eyJ...
```

### Download Export

```http
GET /api/v1/analytics/exports/{export_id}/download
Authorization: Bearer eyJ...
```

Returns the file with appropriate `Content-Type` (`application/pdf`, `text/csv`, or `application/zip`). Only available when status is `completed`.

---

## Shipping

All shipping endpoints require authentication.

### Create Shipment

```http
POST /api/v1/shipments
Authorization: Bearer <token>
Content-Type: application/json

{
  "order_id": "uuid",
  "carrier": "USPS",
  "weight_oz": 12.5,
  "buyer_name": "John Buyer",
  "address_line1": "123 Main St",
  "city": "Portland",
  "state": "OR",
  "zip_code": "97201",
  "country": "US",
  "ship_by_date": "2025-01-15T00:00:00Z",
  "notes": "Fragile item"
}
```

### List Shipments

```http
GET /api/v1/shipments?page=1&per_page=20&status=pending
```

Query parameters:
- `page` — Page number (default: 1)
- `per_page` — Items per page (default: 20, max: 100)
- `status` — Filter by status: `pending`, `label_created`, `shipped`, `delivered`, `cancelled`

### Get Shipment

```http
GET /api/v1/shipments/<id>
```

### Update Shipment

```http
PUT /api/v1/shipments/<id>
Content-Type: application/json

{
  "carrier": "UPS",
  "tracking_number": "1Z999999999",
  "weight_oz": 14.0
}
```

### Delete Shipment (Soft Delete)

```http
DELETE /api/v1/shipments/<id>
```

### Ship

```http
POST /api/v1/shipments/<id>/ship
```

Transitions status to `shipped`, sets `shipped_at`, updates linked order status to `shipped`.

### Deliver

```http
POST /api/v1/shipments/<id>/deliver
```

Transitions status to `delivered`, sets `delivered_at`, updates linked order status to `delivered`.

### Cancel

```http
POST /api/v1/shipments/<id>/cancel
```

### Create Label

```http
POST /api/v1/shipments/<id>/label
```

Generates a shipping label via the configured provider. At MVP, uses ManualProvider (stub).

### Bulk Create Shipments

```http
POST /api/v1/shipments/bulk
Content-Type: application/json

{
  "show_id": "uuid"
}
```

Creates shipments for all pending orders in the specified show that don't already have a shipment.

### List Overdue Shipments

```http
GET /api/v1/shipments/overdue
```

Returns shipments past their `ship_by_date` that haven't been shipped yet.

### List Deleted Shipments

```http
GET /api/v1/shipments/deleted
```

### Restore Shipment

```http
POST /api/v1/shipments/<id>/restore
```

### Generate Packing List

```http
GET /api/v1/packing-lists/<show_id>
```

Returns a packing list grouped by buyer with addresses and order item details.

---

## Health Checks

### Gateway Health (Liveness)

```http
GET /health
```

### Aggregated Health

```http
GET /api/v1/health
```

**Response** (200 if all healthy, 503 if degraded):
```json
{
  "status": "ok",
  "services": {
    "gateway": "ok",
    "auth": "ok",
    "inventory": "ok",
    "sales": "ok",
    "analytics": "ok",
    "shipping": "ok"
  }
}
```

---

## Error Format

All errors follow a consistent envelope:

```json
{
  "data": null,
  "meta": {},
  "errors": [
    {
      "code": "validation_error",
      "message": "Invalid email format"
    }
  ]
}
```

Common error codes:
- `validation_error` (400)
- `unauthorized` (401)
- `forbidden` (403)
- `not_found` (404)
- `conflict` (409)
- `rate_limited` (429)
- `internal_error` (500)
- `bad_gateway` (502)
- `gateway_timeout` (504)

## Rate Limits

- Default: 60 requests/minute per IP
- Rate limit headers included in responses:
  - `X-RateLimit-Limit`
  - `X-RateLimit-Remaining`
  - `X-RateLimit-Reset`
