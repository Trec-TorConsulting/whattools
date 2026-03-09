## ADDED Requirements

### Requirement: User Registration
The system SHALL allow new users to register with email and password, creating a new account (organization) automatically.

#### Scenario: Successful registration
- **WHEN** a user submits a valid email and password (min 8 chars, at least one uppercase, one number)
- **THEN** the system creates an Account and a User with role "owner"
- **AND** sends a verification email with a confirmation token
- **AND** returns a 201 response with user profile (no token until verified)

#### Scenario: Duplicate email
- **WHEN** a user submits an email that is already registered
- **THEN** the system returns a 409 Conflict error
- **AND** does not reveal whether the email exists (generic error message)

#### Scenario: Invalid password
- **WHEN** a user submits a password that does not meet complexity requirements
- **THEN** the system returns a 422 Unprocessable Entity with specific validation errors

### Requirement: Email Verification
The system SHALL require email verification before allowing login.

#### Scenario: Verify email with valid token
- **WHEN** a user submits a valid, unexpired verification token
- **THEN** the system marks the user as verified
- **AND** returns a 200 response

#### Scenario: Expired or invalid token
- **WHEN** a user submits an expired or invalid verification token
- **THEN** the system returns a 400 Bad Request error

### Requirement: User Login
The system SHALL authenticate users via email and password, returning JWT access and refresh tokens.

#### Scenario: Successful login
- **WHEN** a verified user submits valid credentials
- **THEN** the system returns a JWT access token (15-minute expiry) and a refresh token (7-day expiry)
- **AND** stores the refresh token in the database for revocation tracking

#### Scenario: Invalid credentials
- **WHEN** a user submits incorrect email or password
- **THEN** the system returns a 401 Unauthorized error (generic message, no hint about which field is wrong)
- **AND** increments the failed login counter for that account

#### Scenario: Unverified email
- **WHEN** a user with an unverified email submits valid credentials
- **THEN** the system returns a 403 Forbidden error indicating email verification is required

### Requirement: Account Lockout
The system SHALL lock accounts after repeated failed login attempts to prevent brute-force attacks.

#### Scenario: Account locked after 5 failures
- **WHEN** 5 consecutive failed login attempts occur for the same account
- **THEN** the system locks the account for 15 minutes
- **AND** returns a 429 Too Many Requests error for subsequent attempts
- **AND** logs a security event

#### Scenario: Lockout expires
- **WHEN** 15 minutes have passed since lockout
- **THEN** the system allows login attempts again
- **AND** resets the failed attempt counter on successful login

### Requirement: Token Refresh
The system SHALL allow refreshing expired access tokens using a valid refresh token.

#### Scenario: Successful token refresh
- **WHEN** a user submits a valid, non-revoked refresh token
- **THEN** the system returns a new access token and a new refresh token
- **AND** revokes the old refresh token (rotation)

#### Scenario: Revoked or expired refresh token
- **WHEN** a user submits a revoked or expired refresh token
- **THEN** the system returns a 401 Unauthorized error

### Requirement: Logout
The system SHALL revoke refresh tokens on logout.

#### Scenario: Successful logout
- **WHEN** an authenticated user requests logout
- **THEN** the system revokes the current refresh token
- **AND** returns a 200 response

### Requirement: Password Reset
The system SHALL allow users to reset their password via email.

#### Scenario: Request password reset
- **WHEN** a user submits an email address for password reset
- **THEN** the system sends a reset email with a time-limited token (1 hour)
- **AND** returns a 200 response regardless of whether the email exists (prevent enumeration)

#### Scenario: Complete password reset
- **WHEN** a user submits a valid reset token and new password
- **THEN** the system updates the password hash
- **AND** revokes all existing refresh tokens for the user
- **AND** returns a 200 response

### Requirement: Account Management
The system SHALL allow account owners to manage their organization.

#### Scenario: View account details
- **WHEN** an authenticated user requests account details
- **THEN** the system returns account name, plan tier, creation date, and member count

#### Scenario: Update account
- **WHEN** an account owner or admin updates account details (e.g., business name)
- **THEN** the system updates the account and logs an audit entry

### Requirement: Team Management
The system SHALL allow account owners and admins to invite, manage, and remove team members with role-based access.

#### Scenario: Invite team member
- **WHEN** an owner or admin invites a user by email
- **THEN** the system creates a pending invite, sends an invitation email
- **AND** the invitee can register under the existing account

#### Scenario: Free tier team limit
- **WHEN** an owner on the free tier attempts to invite a third team member (already has 2)
- **THEN** the system returns a 403 Forbidden error indicating the plan limit is reached

#### Scenario: Update member role
- **WHEN** an owner updates a member's role (admin/member)
- **THEN** the system updates the role and logs an audit entry
- **AND** only owners can promote to admin or demote admins

#### Scenario: Remove team member
- **WHEN** an owner or admin removes a team member
- **THEN** the system deactivates the user's account and revokes all tokens
- **AND** logs an audit entry

#### Scenario: Member permission boundaries
- **WHEN** a member-role user attempts to invite, remove, or change roles
- **THEN** the system returns a 403 Forbidden error

### Requirement: User Profile Management
The system SHALL allow users to view and update their own profile.

#### Scenario: View own profile
- **WHEN** an authenticated user requests their profile
- **THEN** the system returns user details including email, name, role, and account info

#### Scenario: Update own profile
- **WHEN** an authenticated user updates their name or email
- **THEN** the system updates the profile and logs an audit entry
- **AND** if email changed, requires re-verification

#### Scenario: Delete own account
- **WHEN** an account owner requests account deletion
- **THEN** the system soft-deletes the account and all associated users and data
- **AND** schedules permanent deletion after 30 days
- **AND** sends a confirmation email

### Requirement: Auth Event Publishing
The system SHALL publish events to Redis Pub/Sub for all significant auth actions.

#### Scenario: User lifecycle events
- **WHEN** a user is created, verified, deleted, or has their role changed
- **THEN** the system publishes an event (e.g., user.created, user.verified, user.deleted, team.member.role_changed) to Redis Pub/Sub
- **AND** the event payload includes user_id, account_id, action, and timestamp
