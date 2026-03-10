## ADDED Requirements

### Requirement: Order Sync from Whatnot
The system SHALL automatically import orders from Whatnot with full details including items, customer information, pricing breakdown, and shipping address.

#### Scenario: Pull orders from Whatnot
- **WHEN** order sync is triggered (periodic or manual)
- **THEN** the system queries Whatnot's `orders` endpoint with pagination and date filter
- **AND** creates or updates local order records with all fields
- **AND** maps order items to local inventory items via Whatnot product/variant IDs

#### Scenario: Order with customer address
- **WHEN** an order includes shipping address (scope `read:customers`)
- **THEN** the system stores the full address (fullName, line1, line2, city, state, postalCode, countryCode, phoneNumber)

### Requirement: Push Tracking Code to Whatnot
The system SHALL allow sellers to push tracking codes back to Whatnot for fulfilled orders using the `addTrackingCode` mutation.

#### Scenario: Add tracking code
- **WHEN** a seller enters a tracking code and carrier for a Whatnot order
- **THEN** the system calls `addTrackingCode` with the order IDs, tracking code, and courier (USPS/UPS/FEDEX)

### Requirement: Cancel Order on Whatnot
The system SHALL allow sellers to cancel orders on Whatnot via the `orderCancel` mutation.

#### Scenario: Cancel a Whatnot order
- **WHEN** a seller cancels a Whatnot-linked order
- **THEN** the system calls `orderCancel` on Whatnot
- **AND** updates the local order status to cancelled

### Requirement: Order Sales Channel Tracking
The system SHALL track whether an order came from MARKETPLACE or LIVESTREAM sales channel and display the source.

#### Scenario: Livestream order display
- **WHEN** an order has sales channel type LIVESTREAM
- **THEN** the system displays the order as a livestream sale with link to the associated livestream

### Requirement: Giveaway Order Tracking
The system SHALL identify and display giveaway orders separately from paid orders.

#### Scenario: Giveaway order identification
- **WHEN** an order has `isGiveaway=true`
- **THEN** the system marks it as a giveaway
- **AND** excludes it from revenue calculations
