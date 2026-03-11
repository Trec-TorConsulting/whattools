# Tasks: Add Super Admin Portal

## Phase 1: Backend Foundation

- [ ] Add `is_platform_admin` column to User model with Alembic migration
- [ ] Add `require_platform_admin()` decorator in auth service
- [ ] Add `is_platform_admin` claim to JWT token generation
- [ ] Update `scripts/seed.py` with `--promote-admin` CLI command
- [ ] Add `/api/v1/admin/` route prefix to gateway proxy config

## Phase 2: Admin Service Layer

- [ ] Create `services/auth/services/admin_service.py` with:
  - [ ] `list_accounts()` — paginated, searchable, filterable by plan/status
  - [ ] `get_account_detail(account_id)` — full account info + user count + subscription
  - [ ] `suspend_account(account_id)` — set suspended flag, log audit
  - [ ] `unsuspend_account(account_id)` — clear suspended flag, log audit
  - [ ] `change_account_plan(account_id, plan_tier)` — update plan, log audit
  - [ ] `list_users()` — paginated, searchable across all accounts
  - [ ] `get_user_detail(user_id)` — full user info with account context
  - [ ] `deactivate_user(user_id)` — set `is_active=False`, log audit
  - [ ] `activate_user(user_id)` — set `is_active=True`, log audit
  - [ ] `reset_user_password(user_id)` — generate reset token
  - [ ] `get_platform_metrics()` — aggregate counts, plan distribution, growth
  - [ ] `search_audit_logs()` — cross-account audit log query
  - [ ] `create_impersonation_token(account_id)` — scoped JWT with `impersonated_by` claim

## Phase 3: Admin Routes

- [ ] Create `services/auth/routes/admin_routes.py` with:
  - [ ] `GET /api/v1/admin/accounts` — list accounts
  - [ ] `GET /api/v1/admin/accounts/<id>` — account detail
  - [ ] `POST /api/v1/admin/accounts/<id>/suspend` — suspend
  - [ ] `POST /api/v1/admin/accounts/<id>/unsuspend` — unsuspend
  - [ ] `PUT /api/v1/admin/accounts/<id>/plan` — change plan
  - [ ] `GET /api/v1/admin/users` — list users
  - [ ] `GET /api/v1/admin/users/<id>` — user detail
  - [ ] `POST /api/v1/admin/users/<id>/deactivate` — deactivate
  - [ ] `POST /api/v1/admin/users/<id>/activate` — activate
  - [ ] `POST /api/v1/admin/users/<id>/reset-password` — trigger reset
  - [ ] `GET /api/v1/admin/metrics` — platform metrics
  - [ ] `GET /api/v1/admin/audit-logs` — audit log search
  - [ ] `POST /api/v1/admin/impersonate/<account_id>` — impersonate
- [ ] Create `services/auth/schemas/admin_schemas.py` — request/response schemas

## Phase 4: Admin API Tests

- [ ] Create `services/auth/tests/test_admin_service.py` — unit tests for admin service
- [ ] Create `services/auth/tests/test_admin_routes.py` — integration tests for admin routes
- [ ] Verify coverage threshold maintained

## Phase 5: Frontend Admin Portal

- [ ] Create admin layout: `web/src/components/admin-shell.tsx`
- [ ] Create admin route guard: `web/src/routes/admin-route.tsx`
- [ ] Create admin pages:
  - [ ] `web/src/pages/admin/admin-dashboard.tsx` — KPI cards, charts
  - [ ] `web/src/pages/admin/accounts-list.tsx` — searchable account table
  - [ ] `web/src/pages/admin/account-detail.tsx` — account info, users, actions
  - [ ] `web/src/pages/admin/users-list.tsx` — searchable user table
  - [ ] `web/src/pages/admin/audit-logs.tsx` — filterable audit log viewer
- [ ] Create admin API client: `web/src/lib/admin-api.ts`
- [ ] Add admin routes to `web/src/main.tsx` router
- [ ] Add admin nav link to AppShell (visible only to platform admins)
- [ ] Create admin hooks: `web/src/hooks/use-admin.ts`

## Phase 6: Frontend Admin Tests

- [ ] Add Vitest tests for admin pages
- [ ] Add Vitest tests for admin API client
- [ ] Add Vitest tests for admin route guard

## Phase 7: Documentation & Cleanup

- [ ] Update `docs/api-guide.md` with admin API section
- [ ] Update `docs/openapi.yaml` with admin endpoints
- [ ] Verify all tests pass and coverage >= 90%
