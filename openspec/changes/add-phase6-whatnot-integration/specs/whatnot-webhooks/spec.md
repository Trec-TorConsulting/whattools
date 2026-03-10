## ADDED Requirements

### Requirement: Webhook Receiver
The system SHALL expose an endpoint to receive HTTP POST webhook events from Whatnot. The endpoint SHALL validate the HMAC SHA256 signature using `X-Whatnot-Webhook-Signature` header and the configured webhook secret.

#### Scenario: Valid webhook received
- **WHEN** Whatnot sends a POST with valid HMAC signature
- **THEN** the system accepts the event, stores it in the WebhookEvent log, and processes it
- **AND** responds with HTTP 200 OK

#### Scenario: Invalid webhook signature
- **WHEN** a POST is received with an invalid HMAC signature
- **THEN** the system rejects the request with HTTP 401
- **AND** logs the failed validation attempt

#### Scenario: Duplicate webhook event
- **WHEN** a webhook with an already-processed event ID is received
- **THEN** the system returns HTTP 200 OK without reprocessing (idempotent)

### Requirement: Product Sold Webhook
The system SHALL process `product/sold` webhook events to automatically decrement local inventory and create order records.

#### Scenario: Product sold event
- **WHEN** a `product/sold` event is received
- **THEN** the system decrements the inventory for the matching local item by the sold quantity
- **AND** creates a pending order record with the sold product/listing/order IDs

### Requirement: Bulk Operation Finished Webhook
The system SHALL process `bulk_operation/finished` webhook events to complete pending bulk operations.

#### Scenario: Bulk operation completed
- **WHEN** a `bulk_operation/finished` event with status COMPLETED is received
- **THEN** the system downloads and processes the bulk operation results

### Requirement: Listing Created/Updated Webhook
The system SHALL process `listing/created` and `listing/updated` webhook events to keep local listing data current.

#### Scenario: Listing created event
- **WHEN** a `listing/created` event is received
- **THEN** the system creates or updates the local listing record with transaction_type and quantity

#### Scenario: Listing updated event
- **WHEN** a `listing/updated` event is received
- **THEN** the system updates the local listing record
