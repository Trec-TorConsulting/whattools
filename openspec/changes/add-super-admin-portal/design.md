# Design: Super Admin Portal

## Data Model Changes

### User Table — Add Column

```sql
ALTER TABLE users ADD COLUMN is_platform_admin BOOLEAN NOT NULL DEFAULT FALSE;
```

This flag is orthogonal to `role` (TeamRole). A user can be both a platform admin AND an owner/admin/member of their own account.

### Account Table — Add Column

```sql
ALTER TABLE accounts ADD COLUMN is_suspended BOOLEAN NOT NULL DEFAULT FALSE;
```

Suspended accounts cannot log in or make API calls. The gateway or auth middleware checks this on every request.

## JWT Token Changes

### Standard User Token (unchanged)
```json
{
  "sub": "<user_id>",
  "account_id": "<account_id>",
  "role": "owner",
  "is_platform_admin": false
}
```

### Platform Admin Token
```json
{
  "sub": "<user_id>",
  "account_id": "<account_id>",
  "role": "owner",
  "is_platform_admin": true
}
```

### Impersonation Token
```json
{
  "sub": "<admin_user_id>",
  "account_id": "<target_account_id>",
  "role": "owner",
  "is_platform_admin": true,
  "impersonated_by": "<admin_user_id>",
  "impersonation_account": "<admin_original_account_id>"
}
```

- Max lifetime: 1 hour
- Cannot be refreshed
- All actions logged with `impersonated_by` in audit trail

## Auth Middleware

### `require_platform_admin()` Decorator

```python
def require_platform_admin():
    """Decorator that restricts access to platform admins only."""
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def wrapper(*args, **kwargs):
            claims = get_jwt()
            if not claims.get("is_platform_admin"):
                return error_response("forbidden", "Platform admin access required", status_code=403)
            return f(*args, **kwargs)
        return wrapper
    return decorator
```

### Account Suspension Check

Added to existing auth flow — when a user logs in or refreshes a token, check `account.is_suspended`. If suspended, reject with 403 "Account suspended".

## API Design

### All admin endpoints require `is_platform_admin: true` in JWT claims.

### Account Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/admin/accounts` | List accounts (paginated, searchable) |
| GET | `/api/v1/admin/accounts/:id` | Account detail with users + subscription |
| POST | `/api/v1/admin/accounts/:id/suspend` | Suspend account |
| POST | `/api/v1/admin/accounts/:id/unsuspend` | Unsuspend account |
| PUT | `/api/v1/admin/accounts/:id/plan` | Change plan tier |

### User Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/admin/users` | List all users (paginated, searchable) |
| GET | `/api/v1/admin/users/:id` | User detail with account info |
| POST | `/api/v1/admin/users/:id/deactivate` | Deactivate user |
| POST | `/api/v1/admin/users/:id/activate` | Activate user |
| POST | `/api/v1/admin/users/:id/reset-password` | Reset user's password |

### Platform Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/admin/metrics` | Platform-wide KPIs |
| GET | `/api/v1/admin/audit-logs` | Cross-account audit log search |
| POST | `/api/v1/admin/impersonate/:account_id` | Get impersonation token |

### Query Parameters (List endpoints)

```
GET /api/v1/admin/accounts?search=acme&plan_tier=paid&status=active&sort=created_at&order=desc&page=1&per_page=25
GET /api/v1/admin/users?search=john@example.com&account_id=<uuid>&is_active=true&page=1&per_page=25
GET /api/v1/admin/audit-logs?account_id=<uuid>&actor_id=<uuid>&action=create&resource_type=inventory_item&from=2026-01-01&to=2026-03-10&page=1&per_page=50
```

### Metrics Response Shape

```json
{
  "data": {
    "total_accounts": 142,
    "active_accounts": 130,
    "suspended_accounts": 2,
    "total_users": 385,
    "plan_distribution": {
      "free": 98,
      "paid": 44
    },
    "recent_signups_30d": 18,
    "mrr_estimate": 4400.00
  }
}
```

## Frontend Architecture

### Routing

```
/admin                    → AdminDashboardPage (KPI overview)
/admin/accounts           → AccountsListPage (search, filter, paginated table)
/admin/accounts/:id       → AccountDetailPage (info, users, subscription, actions)
/admin/users              → UsersListPage (search, paginated table)
/admin/audit-logs         → AuditLogsPage (search, filter, paginated table)
```

### Layout

`AdminShell` — Separate layout from `AppShell`:
- Distinct sidebar with admin-specific navigation
- Banner indicating "Admin Portal"
- Impersonation indicator bar when impersonating
- "Back to App" link to return to normal user experience

### Access Control

- `AdminRoute` component checks `is_platform_admin` claim from JWT
- Redirects non-admins to `/dashboard` 
- Admin nav link in `AppShell` sidebar only visible to platform admins

## Seeding / Bootstrap

```bash
python -m scripts seed --promote-admin user@example.com
```

This sets `is_platform_admin = True` on the specified user. Must be run by someone with DB access (not exposed via API for security).

## Security Considerations

1. **No self-promotion** — Users cannot make themselves platform admins via API
2. **Audit everything** — All admin actions logged with admin's user_id
3. **Impersonation trail** — Impersonation tokens carry `impersonated_by` claim; all actions during impersonation are attributable to the admin
4. **Time-limited impersonation** — 1-hour max, non-refreshable
5. **Suspended account enforcement** — Checked at login and token refresh, not at every request (performance tradeoff; revoked sessions expire naturally)
6. **Admin routes isolated** — Separate blueprint, separate route prefix, explicit decorator on every endpoint
