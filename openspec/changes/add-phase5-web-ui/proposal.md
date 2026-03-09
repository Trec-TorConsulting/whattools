# Change: Phase 5 — Web UI (React + shadcn/ui)

## Why

WhatTools has a complete API backend (auth, inventory, sales, analytics, shipping, exports, monitoring) but no user interface. Whatnot sellers currently have no way to interact with the platform. The Web UI is the most user-facing phase and the #1 priority for usability — every screen must be purpose-built for live-selling workflows, not a generic admin panel.

## What Changes

### Stack
- **React 19** + **Vite 6** + **TypeScript 5.7** — fast builds, modern React features
- **shadcn/ui** (Radix UI primitives) — accessible, copy-pasted components we own
- **Tailwind CSS 4** — utility-first styling with WhatTools branding
- **React Router v7** — file-convention routing with role-based guards
- **TanStack Query v5** — server state management, caching, optimistic updates
- **Recharts 2** — analytics visualizations (consistent with backend chart style)
- **Zod** — runtime schema validation for forms and API responses
- **React Hook Form** — performant forms with Zod resolver

### Architecture
- Single-page app served from `/` via gateway (or standalone dev server on `:3000`)
- All API calls go through gateway at `/api/v1/*`
- JWT access/refresh token management with automatic refresh
- Role-based portal: Owner / Admin / Member each see different navigation, routes, and UI elements
- Responsive design: desktop-first (sellers work on laptops during shows), mobile-friendly
- Dark mode toggle (sellers often work evening shows in low-light)

### Portal Experiences (Role-Based)

**All Roles (Member, Admin, Owner):**
- Dashboard (role-appropriate widgets)
- Inventory management (items, categories, CSV import)
- Profile settings

**Admin + Owner Only:**
- Shows (create, manage, start/complete/cancel)
- Orders (view, manage, cancel)
- Shipments (create, bulk ship, labels, packing lists)
- Analytics (summary, trends, categories, top items, show-time suggestions)
- Export reports (create, download CSV/PDF)

**Owner Only:**
- Team management (invite, role changes, remove members)
- Account settings (plan, billing placeholder)

### Pages (22 screens)

#### Auth (public)
1. **Login** — Email/password, "forgot password" link, link to register
2. **Register** — Name, email, password, account name creation
3. **Forgot Password** — Email input → reset flow
4. **Reset Password** — Token-validated new password form
5. **Verify Email** — Token confirmation screen
6. **Accept Invite** — Join existing team via invite token

#### Dashboard (authenticated)
7. **Dashboard** — Role-appropriate overview widgets:
   - Member: inventory stats (total items, items by status, recent activity)
   - Admin: inventory + sales summary + recent orders + shipping alerts (overdue)
   - Owner: everything + team overview + account plan usage

#### Inventory
8. **Items List** — Searchable/filterable table with status badges, bulk actions, cursor pagination
9. **Item Detail / Edit** — Full item form (name, SKU, COGS, price, status, category, notes)
10. **CSV Import** — Three-step wizard: upload → column mapping → progress/results
11. **Categories** — List + inline create/edit, item counts per category
12. **Deleted Items** — Soft-deleted items with restore capability (30-day window)

#### Sales (Admin + Owner)
13. **Shows List** — Filterable by status, show cards with key metrics (revenue, orders, profit)
14. **Show Detail** — Show info + orders table + revenue summary + quick actions (start/complete/cancel)
15. **Orders List** — Filterable/searchable table, status badges, profit column
16. **Order Detail** — Order info, item details, profit breakdown, cancel action

#### Shipping (Admin + Owner)
17. **Shipments List** — Status filters, overdue badge, bulk actions
18. **Shipment Detail** — Tracking info, status transitions (label → ship → deliver), cancel
19. **Packing List** — Per-show grouped-by-buyer packing list with print layout

#### Analytics (Admin + Owner)
20. **Analytics Dashboard** — Summary cards (revenue, profit, orders, shows) + trend chart + category breakdown + top items + show-time suggestions panel
21. **Export Reports** — Create export (type + format picker), job list with status badges, download links

#### Settings
22. **Settings** — Tabbed layout:
    - **Profile** tab (all roles): Name, email, password change
    - **Team** tab (Owner + Admin): Member list, invite form, role management
    - **Account** tab (Owner only): Account name, plan info, usage stats

### Component Library (shadcn/ui based)
- AppShell (sidebar + header + main content area)
- DataTable (sortable, filterable, selectable, paginated — reused everywhere)
- StatusBadge (color-coded status pills for shows, orders, shipments, exports)
- StatCard (metric card with label, value, trend indicator)
- RoleGuard (wraps routes/components, checks JWT role claim)
- EmptyState (illustrated placeholder for empty lists)
- ConfirmDialog (destructive action confirmation)
- LoadingSkeleton (shimmer placeholders during data fetching)

## Impact
- Affected specs: new `web-ui` capability
- Affected code: new `web/` directory at project root, gateway CORS config, docker-compose.yml, K8S manifests
- No backend API changes required — all endpoints already exist
- Gateway already configured with `CORS_ORIGINS=http://localhost:3000`
