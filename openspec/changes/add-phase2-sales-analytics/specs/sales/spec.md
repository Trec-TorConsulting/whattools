## ADDED Requirements

### Requirement: Show Management
The system SHALL allow sellers to create, update, and manage live selling shows.

#### Scenario: Create a show
- **WHEN** an authenticated user submits a valid show (title, platform, scheduled_at)
- **THEN** the system creates a show with status "planned" scoped to the user's account
- **AND** returns a 201 response with the show details
- **AND** publishes a `show.created` event

#### Scenario: List shows
- **WHEN** an authenticated user requests their shows
- **THEN** the system returns paginated shows scoped to the user's account
- **AND** supports filtering by status and date range

#### Scenario: Start a show
- **WHEN** an authenticated user starts a "planned" show
- **THEN** the system transitions status to "live" and sets `started_at`
- **AND** publishes a `show.started` event

#### Scenario: Complete a show
- **WHEN** an authenticated user completes a "live" show
- **THEN** the system transitions status to "completed" and sets `ended_at`
- **AND** publishes a `show.completed` event

#### Scenario: Cancel a show
- **WHEN** an authenticated user cancels a "planned" or "live" show
- **THEN** the system transitions status to "cancelled"
- **AND** cancels all pending orders in the show
- **AND** restores linked inventory items to "active" status
- **AND** publishes a `show.cancelled` event

#### Scenario: Invalid status transition
- **WHEN** a user attempts an invalid status transition (e.g., complete a cancelled show)
- **THEN** the system returns a 409 Conflict error with allowed transitions

### Requirement: Order Management
The system SHALL allow sellers to record item sales (orders) within shows.

#### Scenario: Create an order
- **WHEN** an authenticated user creates an order with show_id, inventory_item_id, sale_price, platform_fees, shipping_cost
- **THEN** the system creates the order scoped to the user's account
- **AND** transitions the linked inventory item to "sold" status
- **AND** returns a 201 response with calculated profit
- **AND** publishes an `order.created` event

#### Scenario: Create order for already-sold item
- **WHEN** a user tries to create an order for an item that is already "sold"
- **THEN** the system returns a 409 Conflict error

#### Scenario: Create order for item in different account
- **WHEN** a user tries to create an order referencing another account's inventory item
- **THEN** the system returns a 404 Not Found (does not reveal existence)

#### Scenario: Cancel an order
- **WHEN** an authenticated user cancels an order
- **THEN** the system transitions order status to "cancelled"
- **AND** restores the linked inventory item to "active" status
- **AND** publishes an `order.cancelled` event

#### Scenario: List orders
- **WHEN** an authenticated user requests their orders
- **THEN** the system returns paginated orders scoped to the user's account
- **AND** supports filtering by show, status, date range

#### Scenario: List orders for a show
- **WHEN** an authenticated user requests orders for a specific show
- **THEN** the system returns all orders belonging to that show
- **AND** includes total revenue, total profit summary

### Requirement: Order Profit Calculation
The system SHALL automatically calculate profit for each order.

#### Scenario: Profit calculated on order creation
- **WHEN** an order is created with sale_price, platform_fees, shipping_cost
- **AND** the linked inventory item has a cost_basis (COGS)
- **THEN** the system calculates: profit = sale_price - platform_fees - shipping_cost - cost_basis
- **AND** stores the calculated profit on the order

#### Scenario: Profit with zero COGS
- **WHEN** an inventory item has no cost_basis (null or 0)
- **THEN** the system calculates profit as: sale_price - platform_fees - shipping_cost

### Requirement: Soft Delete for Shows and Orders
The system SHALL support soft deletion and restoration of shows and orders.

#### Scenario: Soft delete an order
- **WHEN** an authenticated user deletes an order
- **THEN** the system sets `deleted_at` timestamp
- **AND** restores linked inventory item to "active" status
- **AND** the order is excluded from normal queries

#### Scenario: Restore a deleted order
- **WHEN** an authenticated user restores a soft-deleted order
- **THEN** the system clears `deleted_at`
- **AND** transitions linked inventory item back to "sold" status

### Requirement: Audit Trail
The system SHALL log all show and order mutations in the audit trail.

#### Scenario: Order created audit
- **WHEN** an order is created
- **THEN** the system logs: actor, action "order.created", resource_type "order", resource_id, changes JSON

#### Scenario: Show status change audit
- **WHEN** a show status changes
- **THEN** the system logs the status transition with previous and new values
