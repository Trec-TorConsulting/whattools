## MODIFIED Requirements

### Requirement: Gateway Route Mapping
The API gateway SHALL route requests to the sales and analytics services in addition to auth and inventory.

#### Scenario: Route sales requests
- **WHEN** a request arrives at /api/v1/shows/* or /api/v1/orders/*
- **THEN** the gateway proxies to the sales service at port 5003

#### Scenario: Route analytics requests
- **WHEN** a request arrives at /api/v1/analytics/*
- **THEN** the gateway proxies to the analytics service at port 5004

### Requirement: Health Check Aggregation
The API gateway SHALL include sales and analytics services in the aggregated health check.

#### Scenario: All services healthy
- **WHEN** a request arrives at /api/v1/health
- **THEN** the gateway checks health of auth, inventory, sales, and analytics services
- **AND** reports overall status and per-service status
