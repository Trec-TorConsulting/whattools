## ADDED Requirements

### Requirement: Request Routing
The API gateway SHALL route all external requests to the appropriate internal service based on URL path.

#### Scenario: Route auth requests
- **WHEN** a request is made to /api/v1/auth/* or /api/v1/account/* or /api/v1/users/*
- **THEN** the gateway proxies the request to the auth service
- **AND** preserves all headers, query parameters, and request body

#### Scenario: Route inventory requests
- **WHEN** a request is made to /api/v1/items/* or /api/v1/categories/*
- **THEN** the gateway proxies the request to the inventory service

#### Scenario: Unknown route
- **WHEN** a request is made to an unrecognized path under /api/v1/
- **THEN** the gateway returns a 404 Not Found with a JSON error envelope

### Requirement: API Versioning
The API gateway SHALL enforce URL-based API versioning on all routes.

#### Scenario: Versioned route
- **WHEN** a request is made to /api/v1/items
- **THEN** the gateway routes to the v1 handler for the inventory service

#### Scenario: Missing version prefix
- **WHEN** a request is made to /items (without /api/v1/ prefix)
- **THEN** the gateway returns a 404 Not Found

### Requirement: Rate Limiting
The API gateway SHALL enforce rate limits to protect backend services from abuse.

#### Scenario: Per-IP rate limiting
- **WHEN** an unauthenticated client exceeds 60 requests per minute from the same IP
- **THEN** the gateway returns a 429 Too Many Requests error with Retry-After header

#### Scenario: Per-user rate limiting
- **WHEN** an authenticated user exceeds 120 requests per minute
- **THEN** the gateway returns a 429 Too Many Requests error with Retry-After header

### Requirement: CORS Configuration
The API gateway SHALL handle CORS with an explicit allowlist of trusted origins.

#### Scenario: Allowed origin
- **WHEN** a request includes an Origin header matching the allowlist
- **THEN** the gateway includes appropriate Access-Control-Allow-* headers in the response

#### Scenario: Disallowed origin
- **WHEN** a request includes an Origin header not on the allowlist
- **THEN** the gateway does not include CORS headers, causing the browser to block the request

#### Scenario: Preflight request
- **WHEN** a browser sends an OPTIONS preflight request for an allowed origin
- **THEN** the gateway returns a 200 response with CORS headers and no body

### Requirement: Request ID Injection
The API gateway SHALL inject a unique request ID into every request for traceability.

#### Scenario: Generate request ID
- **WHEN** a request arrives without an X-Request-ID header
- **THEN** the gateway generates a UUID and adds it as X-Request-ID to both the forwarded request and the response

#### Scenario: Preserve existing request ID
- **WHEN** a request arrives with an X-Request-ID header
- **THEN** the gateway preserves and forwards the existing ID

### Requirement: Request and Response Logging
The API gateway SHALL log all requests and responses in structured JSON format.

#### Scenario: Log request
- **WHEN** any request passes through the gateway
- **THEN** the gateway logs: method, path, client IP, user_id (if authenticated), request_id, status code, response time in milliseconds
- **AND** does not log request or response bodies (to prevent sensitive data exposure)

### Requirement: Aggregated Health Check
The API gateway SHALL provide a health endpoint that reports the status of all downstream services.

#### Scenario: All services healthy
- **WHEN** a request is made to /api/v1/health
- **THEN** the gateway checks /health on each internal service
- **AND** returns 200 with status of each service: {"gateway": "ok", "auth": "ok", "inventory": "ok"}

#### Scenario: Downstream service unhealthy
- **WHEN** a downstream service's /health check fails or times out
- **THEN** the gateway returns 503 Service Unavailable
- **AND** indicates which service is down in the response body

### Requirement: JSON Response Envelope
The API gateway SHALL ensure all responses follow a consistent JSON envelope format.

#### Scenario: Success response format
- **WHEN** a downstream service returns a successful response
- **THEN** the gateway ensures the response follows the format: {"data": ..., "meta": {...}, "errors": []}

#### Scenario: Error response format
- **WHEN** a downstream service or the gateway itself returns an error
- **THEN** the response follows the format: {"data": null, "meta": {...}, "errors": [{"code": "...", "message": "..."}]}
