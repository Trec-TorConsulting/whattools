## ADDED Requirements

### Requirement: Whatnot OAuth Connection
The system SHALL allow sellers to connect their Whatnot account via OAuth 2.0 Authorization Code flow. The system SHALL store encrypted access and refresh tokens per seller account. The system SHALL automatically refresh expired access tokens.

#### Scenario: Seller initiates OAuth connection
- **WHEN** seller clicks "Connect Whatnot" and is redirected to Whatnot
- **THEN** the system generates an authorization URL with client_id, redirect_uri, response_type=code, state, and requested scopes
- **AND** the seller is redirected to Whatnot's authorization page

#### Scenario: OAuth callback success
- **WHEN** Whatnot redirects back with an authorization code
- **THEN** the system exchanges the code for access and refresh tokens
- **AND** stores encrypted tokens in the database
- **AND** triggers an initial full sync

#### Scenario: OAuth disconnect
- **WHEN** seller clicks "Disconnect Whatnot"
- **THEN** the system deletes stored credentials
- **AND** marks all Whatnot-linked items as disconnected

#### Scenario: Token refresh
- **WHEN** an access token is within 1 hour of expiry or returns 401
- **THEN** the system uses the refresh token to obtain new tokens
- **AND** stores the new encrypted tokens

### Requirement: Whatnot Connection Status
The system SHALL provide a connection status endpoint showing whether a Whatnot account is connected, which scopes are authorized, and the last sync timestamp.

#### Scenario: Connected account status check
- **WHEN** a connected seller queries their Whatnot status
- **THEN** the system returns connected=true, scopes list, and last_synced_at timestamp

#### Scenario: Disconnected account status check
- **WHEN** a disconnected seller queries their Whatnot status
- **THEN** the system returns connected=false

### Requirement: Periodic Background Sync
The system SHALL periodically sync data from Whatnot using Celery beat: orders every 15 minutes, products every hour, livestreams every hour.

#### Scenario: Periodic order sync
- **WHEN** the order sync schedule fires
- **THEN** the system pulls new/updated orders from Whatnot for all connected accounts
- **AND** creates or updates local order records

#### Scenario: Manual sync trigger
- **WHEN** a seller clicks "Sync Now"
- **THEN** the system immediately triggers a full sync for that account

### Requirement: Sync History and Status
The system SHALL maintain a log of all sync operations with timestamp, type, status, items processed, and any errors.

#### Scenario: View sync history
- **WHEN** a seller views the sync dashboard
- **THEN** the system displays recent sync operations with status indicators
