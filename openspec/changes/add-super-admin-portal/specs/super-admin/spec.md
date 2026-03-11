# Super Admin Portal

Platform-level administration system for WhatTools operators to manage all customer accounts, users, subscriptions, and system health.

## ADDED Requirements

### Requirement: ADMIN-001: Platform Admin Flag

The system MUST support a `is_platform_admin` boolean flag on the User model, independent of the tenant-scoped TeamRole. Platform admin privileges are orthogonal to account-level roles.

#### Scenario: User has platform admin flag
- Given a user with `is_platform_admin = true`
- When the user logs in
- Then the JWT token includes `is_platform_admin: true` in claims
- And the user can access `/api/v1/admin/` endpoints

#### Scenario: Regular user cannot access admin routes
- Given a user with `is_platform_admin = false`
- When the user requests any `/api/v1/admin/` endpoint
- Then the system returns 403 Forbidden

### Requirement: ADMIN-002: Account Management

Platform admins MUST be able to list, search, view, suspend, unsuspend, and change plans for any account on the platform.

#### Scenario: List accounts with search
- Given a platform admin
- When they request `GET /api/v1/admin/accounts?search=acme`
- Then the system returns a paginated list of accounts matching "acme"
- And each account includes name, plan tier, user count, subscription status, and creation date

#### Scenario: Suspend an account
- Given a platform admin and an active account
- When they request `POST /api/v1/admin/accounts/:id/suspend`
- Then the account's `is_suspended` flag is set to true
- And the action is logged in the audit trail
- And users of that account cannot log in until unsuspended

#### Scenario: Change account plan
- Given a platform admin
- When they request `PUT /api/v1/admin/accounts/:id/plan` with `{"plan_tier": "paid"}`
- Then the account's plan tier is updated
- And the action is logged in the audit trail

### Requirement: ADMIN-003: User Management

Platform admins MUST be able to list, search, view, activate, deactivate, and reset passwords for any user across all accounts.

#### Scenario: List users across accounts
- Given a platform admin
- When they request `GET /api/v1/admin/users?search=john`
- Then the system returns a paginated list of users matching "john" across all accounts
- And each user includes name, email, role, account name, is_active, and last login

#### Scenario: Deactivate a user
- Given a platform admin and an active user
- When they request `POST /api/v1/admin/users/:id/deactivate`
- Then the user's `is_active` flag is set to false
- And the action is logged in the audit trail

### Requirement: ADMIN-004: Platform Metrics

Platform admins MUST be able to view aggregate platform metrics including total accounts, users, plan distribution, and growth trends.

#### Scenario: View platform metrics
- Given a platform admin
- When they request `GET /api/v1/admin/metrics`
- Then the system returns total accounts, active accounts, suspended accounts, total users, plan distribution, recent signups (30d), and estimated MRR

### Requirement: ADMIN-005: Cross-Account Audit Logs

Platform admins MUST be able to search and filter audit logs across all accounts.

#### Scenario: Search audit logs
- Given a platform admin
- When they request `GET /api/v1/admin/audit-logs?action=create&resource_type=inventory_item`
- Then the system returns a paginated list of matching audit log entries from all accounts
- And each entry includes account name, actor email, action, resource type, timestamp, and description

### Requirement: ADMIN-006: Account Impersonation

Platform admins MUST be able to impersonate any account for debugging purposes, with full audit trail.

#### Scenario: Impersonate an account
- Given a platform admin
- When they request `POST /api/v1/admin/impersonate/:account_id`
- Then the system returns a time-limited JWT (1 hour) with the target account's context
- And the token includes an `impersonated_by` claim with the admin's user ID
- And the impersonation event is logged in the audit trail

#### Scenario: Impersonation token cannot be refreshed
- Given an impersonation token
- When the admin attempts to refresh it
- Then the system rejects the refresh with 403

### Requirement: ADMIN-007: Account Suspension Enforcement

The system MUST prevent users of suspended accounts from authenticating or making API calls.

#### Scenario: Suspended account login rejected
- Given an account with `is_suspended = true`
- When a user of that account attempts to log in
- Then the system returns 403 with message "Account suspended"

### Requirement: ADMIN-008: Admin CLI Seeding

The system MUST provide a CLI command to promote an existing user to platform admin. This is the only way to create platform admins (not exposed via API).

#### Scenario: Promote user via CLI
- Given an existing user with email "admin@example.com"
- When the operator runs `python -m scripts seed --promote-admin admin@example.com`
- Then the user's `is_platform_admin` flag is set to true

### Requirement: ADMIN-009: Admin Frontend Portal

The system MUST provide a dedicated admin UI at `/admin/*` routes with a separate layout, accessible only to platform admins.

#### Scenario: Admin accesses portal
- Given a platform admin user in the browser
- When they navigate to `/admin`
- Then they see the admin dashboard with platform KPIs
- And the admin sidebar shows Accounts, Users, and Audit Logs navigation

#### Scenario: Non-admin redirected
- Given a regular user in the browser
- When they navigate to `/admin`
- Then they are redirected to `/dashboard`
