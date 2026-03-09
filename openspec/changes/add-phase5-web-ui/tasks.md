## 1. Project Scaffolding & Foundation
- [ ] 1.1 Initialize Vite + React + TypeScript project in `web/`
- [ ] 1.2 Install and configure Tailwind CSS 4
- [ ] 1.3 Initialize shadcn/ui with WhatTools theme (navy/purple palette + dark mode)
- [ ] 1.4 Install core shadcn/ui primitives (button, input, label, card, dialog, dropdown-menu, sheet, separator, skeleton, toast, badge, avatar, tabs, tooltip, select, checkbox, table, form, popover, command)
- [ ] 1.5 Install dependencies: react-router v7, @tanstack/react-query, recharts, zod, react-hook-form, @hookform/resolvers, lucide-react, clsx, tailwind-merge, date-fns
- [ ] 1.6 Set up project structure (features/, components/, lib/, hooks/, routes/)
- [ ] 1.7 Configure path aliases (`@/` → `src/`)
- [ ] 1.8 Create Dockerfile (multi-stage: node build → nginx serve) + nginx.conf

## 2. Core Library Layer
- [ ] 2.1 Create `api-client.ts` — fetch wrapper with auth headers, 401 refresh interceptor, request queuing, error normalization
- [ ] 2.2 Create `auth.tsx` — AuthProvider context (login, logout, register, refresh, user state, token storage)
- [ ] 2.3 Create `role-utils.ts` — role hierarchy helpers (canAccess, isAtLeast, ROLE_HIERARCHY)
- [ ] 2.4 Create `query-keys.ts` — TanStack Query key factory for all domains
- [ ] 2.5 Create `schemas.ts` — Zod schemas for API response envelope + shared types
- [ ] 2.6 Create `utils.ts` — cn() helper, currency/date/number formatters
- [ ] 2.7 Create `use-auth.ts` hook — shortcut to AuthContext
- [ ] 2.8 Create `use-pagination.ts` hook — cursor-based pagination state manager
- [ ] 2.9 Create `use-theme.ts` hook — dark/light mode with localStorage + system preference

## 3. Shared Components
- [ ] 3.1 Build `AppShell` — sidebar navigation + top header + main content area + mobile hamburger menu
- [ ] 3.2 Build sidebar navigation with role-based menu filtering
- [ ] 3.3 Build `DataTable` — reusable sortable, filterable, row-selectable table (wraps shadcn Table + uses TanStack Table headless)
- [ ] 3.4 Build `StatCard` — metric card (icon, label, value, optional trend %, optional sparkline)
- [ ] 3.5 Build `StatusBadge` — color-coded pills for all status types (show, order, shipment, export statuses)
- [ ] 3.6 Build `RoleGuard` — component-level role visibility wrapper
- [ ] 3.7 Build `EmptyState` — illustrated placeholder with title, description, optional CTA button
- [ ] 3.8 Build `ConfirmDialog` — destructive action confirmation with customizable title/description
- [ ] 3.9 Build `LoadingSkeleton` — page-level shimmer placeholder variants (table, cards, form)
- [ ] 3.10 Build `PageHeader` — consistent page title + optional breadcrumbs + action buttons area

## 4. Routing & Auth Guards
- [ ] 4.1 Create route tree in `routes/index.tsx` with React Router v7
- [ ] 4.2 Create `ProtectedRoute` — redirects to /login if not authenticated
- [ ] 4.3 Create `RoleRoute` — redirects to /dashboard if role insufficient
- [ ] 4.4 Set up `app.tsx` with QueryClientProvider, AuthProvider, RouterProvider, ThemeProvider
- [ ] 4.5 Implement code-splitting with React.lazy() per feature module

## 5. Auth Pages (Public)
- [ ] 5.1 Create auth API layer (`features/auth/api.ts`) with login, register, refresh, logout, password-reset, verify-email mutations
- [ ] 5.2 Build Login page — email/password form, error display, "Forgot password?" link, "Create account" link
- [ ] 5.3 Build Register page — name, email, password, confirm password, account name, validation, success → "check email"
- [ ] 5.4 Build Forgot Password page — email input, success confirmation
- [ ] 5.5 Build Reset Password page — token extraction from URL, new password + confirm, success → redirect login
- [ ] 5.6 Build Verify Email page — token extraction, auto-verification on load, success/error states
- [ ] 5.7 Build Accept Invite page — token extraction, registration form (name, password), join existing team

## 6. Dashboard
- [ ] 6.1 Create dashboard API layer
- [ ] 6.2 Build Dashboard page — role-aware widget grid
- [ ] 6.3 Build Member dashboard widgets: inventory stats (total items, by status), recent item activity
- [ ] 6.4 Build Admin dashboard widgets: sales summary (revenue, profit, orders), recent orders list, overdue shipments alert, quick actions
- [ ] 6.5 Build Owner dashboard widgets: team overview (member count, roles), account plan usage bar, everything admin sees

## 7. Inventory Feature
- [ ] 7.1 Create inventory API layer (`features/inventory/api.ts`) — items CRUD + categories CRUD + CSV import queries/mutations
- [ ] 7.2 Build Items List page — DataTable with search, status filter, category filter, cursor pagination, bulk delete
- [ ] 7.3 Build Item Create/Edit page — full form (name, SKU, COGS, sale price, quantity, status, category dropdown, notes), Zod validation
- [ ] 7.4 Build CSV Import wizard — Step 1: file upload + preview, Step 2: column mapping dropdowns, Step 3: progress bar + results summary
- [ ] 7.5 Build Categories page — list with inline create/edit, item counts, delete with confirmation
- [ ] 7.6 Build Deleted Items page — DataTable of soft-deleted items, restore action, 30-day countdown

## 8. Sales Feature (Admin + Owner)
- [ ] 8.1 Create sales API layer (`features/sales/api.ts`) — shows CRUD + state transitions + orders CRUD + state transitions
- [ ] 8.2 Build Shows List page — filterable by status, show cards or table toggle, key metrics per show
- [ ] 8.3 Build Show Detail page — show info header, status transition buttons (start/complete/cancel with confirmation), orders table, revenue/profit summary
- [ ] 8.4 Build Orders List page — DataTable with status/show filters, search by buyer, profit column, cancel action
- [ ] 8.5 Build Order Detail page — order info, item details, profit breakdown (sale - fees - shipping - COGS), status badge, cancel action

## 9. Shipping Feature (Admin + Owner)
- [ ] 9.1 Create shipping API layer (`features/shipping/api.ts`) — shipments CRUD + state transitions + bulk create + packing list
- [ ] 9.2 Build Shipments List page — DataTable with status filter, overdue badge, bulk ship dialog
- [ ] 9.3 Build Shipment Detail page — tracking info, address, status stepper (pending → label → shipped → delivered), transition buttons, cancel
- [ ] 9.4 Build Packing List page — per-show grouped-by-buyer layout, print-friendly CSS (@media print), item checklist

## 10. Analytics Feature (Admin + Owner)
- [ ] 10.1 Create analytics API layer (`features/analytics/api.ts`) — summary, categories, shows, trends, top-items, show-time-suggestions, exports CRUD
- [ ] 10.2 Build Analytics Dashboard page — summary stat cards (revenue, profit, orders, avg per show) + period selector (7d/30d/90d/365d/all)
- [ ] 10.3 Build trend chart (Recharts AreaChart — revenue + profit over time)
- [ ] 10.4 Build category breakdown (Recharts BarChart — revenue per category)
- [ ] 10.5 Build top items panel (ranked list with revenue/profit/quantity)
- [ ] 10.6 Build show-time suggestions panel — recommended time slots with confidence scores, avoid slots, category-specific insights
- [ ] 10.7 Build Export Reports page — create export form (report type radio + format radio + period select), jobs list with status badges, download button

## 11. Settings Feature
- [ ] 11.1 Create settings API layer (`features/settings/api.ts`) — profile update, team management, account info
- [ ] 11.2 Build Settings page — tabbed layout (Profile / Team / Account)
- [ ] 11.3 Build Profile tab — name, email, password change form (current + new + confirm)
- [ ] 11.4 Build Team tab (Owner + Admin) — member DataTable, invite dialog (email + role select), role change dropdown (Owner only), remove member with confirmation
- [ ] 11.5 Build Account tab (Owner only) — account name edit, plan tier display, usage stats (items used / limit, members / limit)

## 12. Infrastructure & Integration
- [ ] 12.1 Update `docker-compose.yml` — add web service (Dockerfile, port 3000, VITE_API_URL env var)
- [ ] 12.2 Create K8S manifest `k8s/prod/web.yaml` — Deployment + Service + ConfigMap
- [ ] 12.3 Update `k8s/prod/ingress.yaml` — add web app routing (/ → web service)
- [ ] 12.4 Update `docs/architecture.md` — add Web UI layer to architecture diagram
- [ ] 12.5 Update `docs/deployment.md` — add web build/deploy instructions

## 13. Testing
- [ ] 13.1 Install Vitest + React Testing Library + MSW
- [ ] 13.2 Write tests for `api-client.ts` (auth header injection, 401 refresh, error handling)
- [ ] 13.3 Write tests for `AuthProvider` (login, logout, token refresh, session expiry)
- [ ] 13.4 Write tests for `RoleGuard` and `RoleRoute` (visibility per role)
- [ ] 13.5 Write tests for auth pages (login form validation, register flow, error states)
- [ ] 13.6 Write tests for inventory pages (items list rendering, create/edit form, CSV wizard flow)
- [ ] 13.7 Write tests for sales pages (shows list, show detail actions, orders)
- [ ] 13.8 Write tests for shipping pages (shipments list, status transitions, packing list)
- [ ] 13.9 Write tests for analytics pages (dashboard rendering, chart data, exports)
- [ ] 13.10 Write tests for settings pages (profile form, team management, role guards)
- [ ] 13.11 Run full test suite, verify coverage ≥ 80%

## 14. Documentation & Commit
- [ ] 14.1 Update docs/architecture.md, docs/api-guide.md, docs/deployment.md
- [ ] 14.2 Git commit Phase 5
