## MODIFIED Requirements

### Requirement: Event Types
The shared event system SHALL support new event types for shows and orders.

#### Scenario: Show events published
- **WHEN** a show is created, started, completed, or cancelled
- **THEN** the event publisher sends events: show.created, show.started, show.completed, show.cancelled

#### Scenario: Order events published
- **WHEN** an order is created, updated, or cancelled
- **THEN** the event publisher sends events: order.created, order.updated, order.cancelled

### Requirement: Inventory Item Status
The inventory item model SHALL support a "sold" status.

#### Scenario: Item marked as sold
- **WHEN** an order is created linking to an inventory item
- **THEN** the item's status transitions from "active" to "sold"

#### Scenario: Item restored to active
- **WHEN** an order is cancelled or deleted
- **THEN** the item's status transitions from "sold" to "active"
