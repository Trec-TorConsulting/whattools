# Proposal: Add Super Admin Portal

## Summary

Add a platform-level Super Admin system to WhatTools, enabling platform operators to manage all customer accounts, users, subscriptions, and system health from a dedicated admin portal. Super Admins operate outside the normal tenant-scoped role model and have cross-account visibility and control.

## Motivation

Currently, all roles (owner/admin/member) are scoped to a single account's team. There is no way for WhatTools platform operators to:

- View or manage customer accounts
- Suspend/unsuspend problematic accounts
- Change subscription plans or billing status
- View platform-wide metrics (total accounts, revenue, growth)
- Impersonate a customer account for debugging
- View cross-account audit logs
- Manage the platform without direct database access

As the platform scales, operators need a self-service admin portal to handle support, billing issues, and platform health monitoring.

## Scope

### In Scope

1. **Platform Admin Role** — New `is_platform_admin` boolean flag on User model (not a TeamRole, since super admins exist outside tenant boundaries)
2. **Admin Auth** — JWT claims include `is_platform_admin: true`; dedicated middleware/decorator for admin-only routes
3. **Admin API** — New `/api/v1/admin/` route prefix on the auth service:
   - Account management: list, search, view detail, suspend, unsuspend, change plan
   - User management: list all users, view detail, deactivate, reset password
   - Platform metrics: account counts, user counts, plan distribution, revenue summary
   - Audit log viewer: cross-account audit log search and filtering  
   - Impersonation: generate a scoped token to act as a specific account (logged in audit trail)
4. **Admin Frontend** — New `/admin/*` routes with a dedicated AdminShell layout:
   - Dashboard with platform KPIs
   - Accounts list with search/filter/sort
   - Account detail page (info, users, subscription, activity)
   - Users search
   - Audit log viewer
   - Impersonation controls
5. **Gateway Routing** — `/api/v1/admin/` prefix routed to auth service
6. **Seeding** — CLI command to promote a user to platform admin
7. **Tests** — Full test coverage for admin routes, services, and frontend components

### Out of Scope

- Multi-tenancy changes (accounts remain isolated, admin reads across them)
- Admin API rate limiting changes (uses existing gateway rate limiter)
- Admin-specific notification system
- Customer-facing changes (no visible impact to existing users)
- Admin 2FA/MFA (can be added later)

## Design Decisions

### Why `is_platform_admin` flag vs. new TeamRole?

TeamRole is scoped to an account. Super admins need cross-account access that exists outside the tenant model. A boolean flag on User keeps the tenant role system clean while enabling platform-level privileges. A super admin can also be an owner/admin of their own account — the two are orthogonal.

### Why on the auth service?

The auth service already manages users, accounts, and JWT tokens. Adding admin routes here avoids creating a new service and keeps all identity/access logic centralized. Admin API calls query the same database tables.

### Impersonation Safety

Impersonation generates a time-limited JWT with the target account's `account_id` but includes an `impersonated_by` claim. All actions during impersonation are logged with the admin's real identity. Impersonation tokens have a 1-hour max lifetime and cannot be refreshed.

## Impact

- **Database:** One column added to `users` table (`is_platform_admin BOOLEAN DEFAULT FALSE`)
- **Auth service:** New admin routes module, admin service layer, admin middleware
- **Gateway:** One new route prefix mapping
- **Frontend:** New admin pages and layout (isolated from customer UI)
- **Existing functionality:** Zero impact — all existing routes, roles, and flows unchanged
