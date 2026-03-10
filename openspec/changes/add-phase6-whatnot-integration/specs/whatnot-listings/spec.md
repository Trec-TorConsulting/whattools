## ADDED Requirements

### Requirement: Listing Creation
The system SHALL allow sellers to create listings on Whatnot in three types: BuyItNow (with price and offerable flag), Auction (with starting price, end time, sudden death), and Giveaway.

#### Scenario: Create BuyItNow listing
- **WHEN** a seller creates a BuyItNow listing for a product variant
- **THEN** the system calls `productVariantCreate` or `listingUpdate` with BuyItNowInput including price and offerable flag
- **AND** sets the inventory level quantity

#### Scenario: Create Auction listing
- **WHEN** a seller creates an Auction listing
- **THEN** the system creates the listing with startingPrice, endTime, and suddenDeathEnabled

#### Scenario: Create Giveaway listing
- **WHEN** a seller creates a Giveaway listing
- **THEN** the system creates a listing with no price, only inventory level

### Requirement: Listing Publish and Unpublish
The system SHALL allow sellers to publish and unpublish listings to control visibility on Whatnot.

#### Scenario: Publish a listing
- **WHEN** a seller publishes a listing
- **THEN** the system calls `listingPublish` and the listing becomes visible on Whatnot

#### Scenario: Unpublish a listing
- **WHEN** a seller unpublishes a listing
- **THEN** the system calls `listingUnpublish` and the listing is hidden

### Requirement: Listing Livestream Assignment
The system SHALL allow sellers to assign listings to livestreams and remove them.

#### Scenario: Assign listing to livestream
- **WHEN** a seller assigns a listing to a livestream
- **THEN** the system calls `listingAssignToLivestream` with the listing ID and livestream ID

#### Scenario: Remove listing from livestream
- **WHEN** a seller removes a listing from a livestream
- **THEN** the system calls `listingRemoveFromLivestream`

### Requirement: Listing Inventory Adjustment
The system SHALL allow sellers to adjust listing quantities on Whatnot.

#### Scenario: Increase listing quantity
- **WHEN** a seller adjusts a listing quantity
- **THEN** the system calls `listingAdjustQuantity` with the new quantity

### Requirement: Listing Status Display
The system SHALL display listing status (ACTIVE, INACTIVE, SOLD, SOLD_OUT) and provide direct links to listings on Whatnot.

#### Scenario: View listing status
- **WHEN** a seller views their listings
- **THEN** each listing shows current status, price/starting price, quantity, and a link to the Whatnot listing URL

### Requirement: Listing Delete
The system SHALL allow sellers to delete listings from Whatnot.

#### Scenario: Delete a listing
- **WHEN** a seller deletes a listing
- **THEN** the system calls `listingDelete` and removes the local listing record
