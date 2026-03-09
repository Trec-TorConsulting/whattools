## ADDED Requirements

### Requirement: Soft Delete Mixin
The system SHALL provide a reusable soft delete mixin for all database models.

#### Scenario: Soft delete a record
- **WHEN** a record is soft-deleted via the repository
- **THEN** the deleted_at column is set to the current UTC timestamp
- **AND** the record is excluded from default queries

#### Scenario: Query excludes deleted records
- **WHEN** a standard query is executed through the repository
- **THEN** records with a non-null deleted_at are automatically excluded

#### Scenario: Query includes deleted records
- **WHEN** a query explicitly requests deleted records (e.g., trash listing)
- **THEN** the repository returns only records where deleted_at is not null and within the 30-day retention window

### Requirement: Audit Trail
The system SHALL maintain an audit log of all mutations on important resources.

#### Scenario: Log a mutation
- **WHEN** a create, update, delete, or restore operation is performed on an audited resource
- **THEN** the system creates an audit log entry with: action, actor_id, account_id, resource_type, resource_id, changes (JSON diff of old/new values), timestamp

#### Scenario: Audit log is immutable
- **WHEN** an audit log entry is created
- **THEN** it cannot be updated or deleted (append-only)

#### Scenario: Audit log is account-scoped
- **WHEN** an audit log is queried
- **THEN** results are filtered to the requesting user's account

### Requirement: Base Repository
The system SHALL provide a base repository class that enforces account scoping, soft delete filtering, and cursor-based pagination.

#### Scenario: Account scoping
- **WHEN** any query is executed through the base repository
- **THEN** the query is automatically scoped to the current user's account_id

#### Scenario: Cursor-based pagination
- **WHEN** a list query is executed with pagination parameters
- **THEN** the repository returns results with a next_cursor and total_count in metadata

#### Scenario: Prevent cross-account access
- **WHEN** a repository method receives a resource ID belonging to a different account
- **THEN** the repository returns None (resource not found) rather than the resource

### Requirement: Redis Pub/Sub Events
The system SHALL provide a shared event publishing and subscribing mechanism via Redis Pub/Sub.

#### Scenario: Publish event
- **WHEN** a service publishes an event (e.g., user.created)
- **THEN** the event is serialized to JSON with fields: event_type, payload, timestamp, source_service
- **AND** published to the appropriate Redis channel

#### Scenario: Subscribe to events
- **WHEN** a service subscribes to an event channel
- **THEN** it receives events as they are published and deserializes the JSON payload

#### Scenario: Event publishing failure
- **WHEN** Redis is unavailable during event publishing
- **THEN** the system logs a warning but does not fail the primary operation (fire-and-forget)

### Requirement: Health Check Endpoints
Every service SHALL expose /health and /ready endpoints for Kubernetes liveness and readiness probes.

#### Scenario: Liveness check
- **WHEN** a GET request is made to /health
- **THEN** the service returns 200 {"status": "ok"} if the process is running

#### Scenario: Readiness check
- **WHEN** a GET request is made to /ready
- **THEN** the service returns 200 {"status": "ready"} if the database connection is active and migrations are applied
- **AND** returns 503 {"status": "not_ready", "reason": "..."} if dependencies are unavailable

### Requirement: Structured Logging
The system SHALL use structured JSON logging via structlog across all services.

#### Scenario: Request logging
- **WHEN** any HTTP request is processed
- **THEN** the log entry includes: timestamp, level, service_name, request_id, method, path, status_code, duration_ms

#### Scenario: Security event logging
- **WHEN** a security-relevant event occurs (login failure, permission denied, account lockout)
- **THEN** the log entry includes event_type: "security" and relevant context (user_id, IP, reason)
- **AND** does not include passwords, tokens, or sensitive PII

#### Scenario: Error logging
- **WHEN** an unhandled exception occurs
- **THEN** the log entry includes the full stack trace, request_id, and service_name

### Requirement: Base Model
The system SHALL provide a base SQLAlchemy model with common fields for all database tables.

#### Scenario: Common fields
- **WHEN** a model inherits from the base model
- **THEN** it automatically has: id (UUID primary key), created_at (UTC timestamp), updated_at (UTC timestamp, auto-updated), deleted_at (nullable UTC timestamp for soft delete)

#### Scenario: UUID primary keys
- **WHEN** a new record is created
- **THEN** the id is a randomly generated UUID (v4), not an auto-incrementing integer

### Requirement: JSON Error Response Envelope
The system SHALL use a consistent JSON error response format across all services.

#### Scenario: Validation error
- **WHEN** a request fails input validation
- **THEN** the response format is: {"data": null, "meta": {"request_id": "..."}, "errors": [{"code": "validation_error", "message": "...", "field": "..."}]}

#### Scenario: Authentication error
- **WHEN** a request fails authentication
- **THEN** the response format is: {"data": null, "meta": {"request_id": "..."}, "errors": [{"code": "unauthorized", "message": "..."}]}

#### Scenario: Server error
- **WHEN** an unexpected server error occurs
- **THEN** the response format is: {"data": null, "meta": {"request_id": "..."}, "errors": [{"code": "internal_error", "message": "An unexpected error occurred"}]}
- **AND** the actual error details are logged but not exposed to the client
