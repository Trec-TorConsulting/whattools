## ADDED Requirements

### Requirement: Stripe Subscription Management
The system SHALL integrate Stripe Checkout for subscription creation and Stripe Customer Portal for self-service subscription management.

#### Scenario: Create checkout session
- **WHEN** a seller clicks "Upgrade to Paid"
- **THEN** the system creates a Stripe Checkout session with the paid tier price
- **AND** redirects the seller to Stripe's hosted checkout page

#### Scenario: Manage subscription
- **WHEN** a seller clicks "Manage Subscription"
- **THEN** the system creates a Stripe Customer Portal session
- **AND** redirects the seller to manage billing, cancel, or update payment method

### Requirement: Stripe Webhook Processing
The system SHALL process Stripe webhook events to maintain subscription state, including: checkout.session.completed, customer.subscription.updated, customer.subscription.deleted, invoice.payment_failed.

#### Scenario: Checkout completed
- **WHEN** a `checkout.session.completed` event is received
- **THEN** the system updates the account to paid tier with the Stripe subscription ID

#### Scenario: Subscription cancelled
- **WHEN** a `customer.subscription.deleted` event is received
- **THEN** the system downgrades the account to free tier

#### Scenario: Payment failed
- **WHEN** an `invoice.payment_failed` event is received
- **THEN** the system marks the subscription as past_due

### Requirement: Free Tier Limits
The system SHALL enforce free tier limits: maximum 50 inventory items and 2 team members. The system SHALL display usage warnings approaching limits.

#### Scenario: Item creation at limit
- **WHEN** a free-tier seller tries to create an inventory item beyond 50
- **THEN** the system rejects the creation with an error indicating the limit
- **AND** suggests upgrading to paid tier

#### Scenario: Team invite at limit
- **WHEN** a free-tier seller tries to invite a team member beyond 2
- **THEN** the system rejects the invite with an error indicating the limit

### Requirement: Plan Display and Usage
The system SHALL display the current plan tier, usage metrics (items count vs limit, members count vs limit), and upgrade options.

#### Scenario: Free tier user views billing
- **WHEN** a free-tier seller views the billing page
- **THEN** the system displays "Free" plan with usage (X/50 items, X/2 members) and an upgrade button

#### Scenario: Paid tier user views billing
- **WHEN** a paid-tier seller views the billing page
- **THEN** the system displays "Paid" plan with unlimited usage and a "Manage Subscription" button
