# Change: Add Phase 3 — Shipping & Fulfillment Service

## Why
After a Whatnot show, sellers manually create shipping labels one-by-one and track shipments across multiple tools. WhatTools needs a shipping service to let sellers manage shipments in bulk, generate packing lists, store tracking numbers, and track ship-by deadlines — all from a single API.

## What Changes
- New **shipping microservice** (port 5005) with Shipment model, full CRUD, bulk operations, and packing list generation
- Shipment lifecycle: PENDING → LABEL_CREATED → SHIPPED → DELIVERED (+ CANCELLED)
- Bulk shipment creation from all pending orders in a completed show
- Packing list endpoint returning structured order/item data for a show
- Ship-by date tracking with overdue shipment queries
- Pluggable shipping provider interface (stub for MVP; Shippo/EasyPost in future phase)
- API gateway updated with `/api/v1/shipments` and `/api/v1/packing-lists` routes
- Database migration for `shipments` table
- Docker Compose and K8S manifests updated for shipping service

## Impact
- Affected specs: shipping (new capability)
- Affected code: services/shipping/ (new), services/gateway/proxy.py, docker-compose.yml, k8s/prod/, migrations/, docs/
