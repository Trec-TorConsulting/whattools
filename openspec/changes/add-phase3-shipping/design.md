## Context
Sellers need to ship items after each show. Currently this is done manually — one label at a time, tracking numbers scattered across email and shipping sites. The shipping service centralizes fulfillment: track what needs to ship, create shipments in bulk, generate packing lists, and monitor ship-by deadlines.

The project constraint "No external SaaS dependencies that cost money at MVP" means we build a pluggable provider interface with a stub/manual provider. Actual Shippo/EasyPost integration will be added in a future phase.

## Goals / Non-Goals
- **Goals:**
  - Shipment CRUD with lifecycle management (pending → label_created → shipped → delivered)
  - Bulk shipment creation for all pending orders in a show
  - Packing list generation (structured JSON per show)
  - Ship-by date tracking and overdue queries
  - Pluggable provider interface for future Shippo/EasyPost integration
  - Full test coverage following existing patterns

- **Non-Goals:**
  - Actual external shipping API calls (deferred to future phase)
  - PDF packing list rendering (JSON only for now)
  - Buyer notification sending (prep data only)
  - Rate comparison across carriers (deferred)

## Decisions

### D1: Shipment Model
- One `Shipment` per `Order` (1:1 relationship)
- Fields: carrier, tracking_number, label_url, ship_by_date, shipped_at, delivered_at, weight, dimensions
- Shipment address fields: buyer_name, address_line1, address_line2, city, state, zip_code, country
- ShipmentStatus enum: PENDING, LABEL_CREATED, SHIPPED, DELIVERED, CANCELLED

### D2: Bulk Shipment Creation
- POST `/api/v1/shipments/bulk` accepts a `show_id`
- Creates one shipment per pending order in the show that doesn't already have a shipment
- Returns list of created shipments and skipped orders
- Atomic: all-or-nothing within a transaction

### D3: Packing Lists
- GET `/api/v1/packing-lists/<show_id>` returns structured JSON
- Groups orders by buyer, includes item details, quantities, addresses
- Read-only aggregation — no new data model needed

### D4: Provider Interface
- Abstract `ShippingProvider` class with methods: `create_label()`, `get_rates()`, `track_shipment()`
- `ManualProvider` implements stub versions (no-op label creation, manual tracking entry)
- Provider selected via config, swappable for Shippo/EasyPost later

### D5: Ship-by Date Tracking
- Optional `ship_by_date` on Shipment (set from Order or manually)
- GET `/api/v1/shipments/overdue` returns shipments past their ship-by date that haven't shipped
- No background task/Celery for reminders yet — API-driven only

## Service Architecture
```
services/shipping/
├── __init__.py
├── app.py                      # Flask app factory
├── wsgi.py                     # WSGI entry point (port 5005)
├── Dockerfile
├── models/
│   ├── __init__.py
│   └── models.py               # Shipment model
├── schemas/
│   ├── __init__.py
│   └── schemas.py               # Marshmallow schemas
├── repositories/
│   ├── __init__.py
│   └── shipping_repository.py   # Data access
├── services/
│   ├── __init__.py
│   └── shipping_service.py      # Business logic
├── providers/
│   ├── __init__.py
│   ├── base.py                  # Abstract ShippingProvider
│   └── manual.py                # ManualProvider (stub)
├── routes/
│   ├── __init__.py
│   ├── shipment_routes.py       # Shipment CRUD + bulk
│   └── packing_list_routes.py   # Packing list generation
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_models.py
    ├── test_schemas.py
    ├── test_services.py
    ├── test_shipment_routes.py
    ├── test_packing_list_routes.py
    └── test_providers.py
```
