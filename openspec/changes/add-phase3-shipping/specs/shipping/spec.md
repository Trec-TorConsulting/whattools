## ADDED Requirements

### Requirement: Shipment Management
The system SHALL provide full CRUD operations for shipments linked to orders, with lifecycle status tracking (PENDING → LABEL_CREATED → SHIPPED → DELIVERED, plus CANCELLED).

#### Scenario: Create shipment for an order
- **WHEN** a user creates a shipment with a valid order_id, carrier, and optional address/tracking info
- **THEN** the system creates a shipment in PENDING status linked to the order
- **AND** an audit log entry is created

#### Scenario: Update shipment tracking information
- **WHEN** a user updates a shipment with a tracking number and carrier
- **THEN** the system updates the shipment and recalculates status if appropriate
- **AND** an audit log entry is created

#### Scenario: Mark shipment as shipped
- **WHEN** a user transitions a shipment to SHIPPED status
- **THEN** the system records the shipped_at timestamp
- **AND** the linked order status is updated to SHIPPED

#### Scenario: Mark shipment as delivered
- **WHEN** a user transitions a shipment to DELIVERED status
- **THEN** the system records the delivered_at timestamp
- **AND** the linked order status is updated to DELIVERED

#### Scenario: Cancel a shipment
- **WHEN** a user cancels a shipment that is not yet delivered
- **THEN** the shipment status changes to CANCELLED
- **AND** the linked order status remains unchanged

#### Scenario: Prevent duplicate shipments
- **WHEN** a user tries to create a shipment for an order that already has an active shipment
- **THEN** the system returns a 409 conflict error

### Requirement: Bulk Shipment Creation
The system SHALL support creating shipments for all pending orders in a completed show in a single operation.

#### Scenario: Bulk create shipments for a show
- **WHEN** a user submits a bulk shipment request with a show_id
- **THEN** the system creates one shipment per pending order that doesn't already have an active shipment
- **AND** returns the list of created shipments and any skipped orders

#### Scenario: Bulk create for show with no pending orders
- **WHEN** a user submits a bulk request for a show with no eligible orders
- **THEN** the system returns an empty created list with all orders marked as skipped

### Requirement: Packing List Generation
The system SHALL generate structured packing lists for a show, grouping orders by buyer with item details.

#### Scenario: Generate packing list for a show
- **WHEN** a user requests a packing list for a show_id
- **THEN** the system returns a JSON response grouping orders by buyer_username
- **AND** each group includes item name, sale price, quantity, and shipping address if available

#### Scenario: Packing list for show with no orders
- **WHEN** a user requests a packing list for a show with no orders
- **THEN** the system returns an empty buyers list with zero totals

### Requirement: Ship-by Date Tracking
The system SHALL track ship-by deadlines and provide an endpoint to query overdue shipments.

#### Scenario: Query overdue shipments
- **WHEN** a user requests overdue shipments
- **THEN** the system returns all shipments where ship_by_date is in the past and status is not SHIPPED, DELIVERED, or CANCELLED

#### Scenario: No overdue shipments
- **WHEN** a user requests overdue shipments and all are on time
- **THEN** the system returns an empty list

### Requirement: Shipping Provider Interface
The system SHALL use a pluggable provider interface for shipping operations, with a manual/stub provider at MVP.

#### Scenario: Manual provider label creation
- **WHEN** the system uses the ManualProvider to create a label
- **THEN** it returns a success result with no external API call
- **AND** the shipment status transitions to LABEL_CREATED

### Requirement: Soft Delete and Restore
The system SHALL support soft deletion and restoration of shipments following the existing 30-day retention pattern.

#### Scenario: Soft-delete a shipment
- **WHEN** a user deletes a shipment
- **THEN** the shipment's deleted_at timestamp is set
- **AND** an audit log entry is created

#### Scenario: Restore a deleted shipment
- **WHEN** a user restores a soft-deleted shipment within 30 days
- **THEN** the shipment's deleted_at is cleared and the shipment is active again
