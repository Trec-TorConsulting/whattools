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
    "inventory": "ok"
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
