## Context

WhatTools is a B2B SaaS for Whatnot live-selling sellers. The backend is complete (auth, inventory, sales, analytics, shipping, exports, monitoring — 622 tests). Phase 5 adds the Web UI as a React SPA that consumes the existing REST API through the gateway.

**Primary constraint**: Usability is #1. Every screen is designed for Whatnot sellers' actual workflows — not generic CRUD. Sellers manage inventory before shows, run live shows with real-time order tracking, ship orders in bulk after shows, and analyze performance to optimize their business.

**Target users**: Solo sellers and small teams (2-10 people) on the Whatnot live-selling platform. They work across desktop (primary) and occasionally mobile. Evening shows mean dark mode matters.

## Goals / Non-Goals

### Goals
- Pixel-perfect, accessible UI built with shadcn/ui (Radix primitives) — WCAG 2.1 AA
- Role-based portal experience: Owner / Admin / Member see appropriate features
- Responsive (desktop-first, mobile-functional)
- Dark mode with system preference detection + manual toggle
- Optimistic UI updates for common actions (status transitions, creates)
- Offline-aware (graceful degradation, not offline-first)
- Sub-second perceived page transitions (skeleton loaders + TanStack Query cache)

### Non-Goals
- Server-side rendering (SPA is fine — no SEO requirements for an authenticated app)
- Real-time WebSocket updates (polling via TanStack Query refetch intervals is sufficient for MVP)
- Mobile native app
- Whatnot API integration (Phase 6)
- Billing/Stripe integration (Phase 6)
- i18n / localization (English only at MVP)

## Decisions

### 1. Project Structure — Feature-Based Modules

```
web/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.ts
├── components.json              # shadcn/ui config
├── public/
│   └── favicon.svg
├── src/
│   ├── main.tsx                 # App entry point
│   ├── app.tsx                  # Router + providers
│   ├── globals.css              # Tailwind imports + CSS variables
│   │
│   ├── components/              # Shared UI components
│   │   ├── ui/                  # shadcn/ui primitives (button, input, dialog, etc.)
│   │   ├── app-shell.tsx        # Sidebar + header + main layout
│   │   ├── data-table.tsx       # Reusable sortable/filterable table
│   │   ├── stat-card.tsx        # Metric display card
│   │   ├── status-badge.tsx     # Color-coded status pills
│   │   ├── role-guard.tsx       # Role-based visibility wrapper
│   │   ├── empty-state.tsx      # Empty list placeholder
│   │   ├── confirm-dialog.tsx   # Destructive action confirmation
│   │   ├── loading-skeleton.tsx # Shimmer placeholders
│   │   └── page-header.tsx      # Consistent page title + breadcrumb + actions
│   │
│   ├── lib/                     # Utilities
│   │   ├── api-client.ts        # Fetch wrapper with auth, refresh, error handling
│   │   ├── auth.tsx             # AuthProvider context (tokens, user, login/logout)
│   │   ├── role-utils.ts        # Role hierarchy helpers (canAccess, isOwner, etc.)
│   │   ├── query-keys.ts        # TanStack Query key factory
│   │   ├── utils.ts             # cn() helper, formatters, etc.
│   │   └── schemas.ts           # Shared Zod schemas (API response envelope)
│   │
│   ├── hooks/                   # Shared hooks
│   │   ├── use-auth.ts          # useAuth() hook — shortcut to AuthContext
│   │   ├── use-pagination.ts    # Cursor-based pagination state
│   │   └── use-theme.ts         # Dark/light mode toggle
│   │
│   ├── features/                # Feature modules (one per domain)
│   │   ├── auth/                # Login, register, password reset, verify, invite
│   │   │   ├── pages/
│   │   │   ├── components/
│   │   │   └── api.ts           # Auth API calls + TanStack mutations
│   │   │
│   │   ├── dashboard/
│   │   │   ├── pages/
│   │   │   └── components/      # Role-specific dashboard widgets
│   │   │
│   │   ├── inventory/
│   │   │   ├── pages/           # Items list, detail, CSV import, categories, deleted
│   │   │   ├── components/      # Item form, CSV wizard steps, category inline editor
│   │   │   └── api.ts
│   │   │
│   │   ├── sales/
│   │   │   ├── pages/           # Shows list, show detail, orders list, order detail
│   │   │   ├── components/      # Show card, order table, profit breakdown
│   │   │   └── api.ts
│   │   │
│   │   ├── shipping/
│   │   │   ├── pages/           # Shipments list, detail, packing list
│   │   │   ├── components/      # Shipment status stepper, bulk ship dialog
│   │   │   └── api.ts
│   │   │
│   │   ├── analytics/
│   │   │   ├── pages/           # Analytics dashboard, exports
│   │   │   ├── components/      # Charts, suggestion cards, export create form
│   │   │   └── api.ts
│   │   │
│   │   └── settings/
│   │       ├── pages/           # Settings (tabbed: profile, team, account)
│   │       ├── components/      # Profile form, team table, invite dialog
│   │       └── api.ts
│   │
│   └── routes/                  # Route definitions
│       ├── index.tsx            # Route tree (React Router v7)
│       ├── protected-route.tsx  # Auth gate (redirects to /login if no token)
│       └── role-route.tsx       # Role gate (redirects to /dashboard if insufficient role)
│
├── Dockerfile                   # Multi-stage: node build → nginx serve
└── nginx.conf                   # SPA fallback + /api proxy
```

### 2. Authentication Flow — Token Management

```
Login → Store access_token (memory) + refresh_token (httpOnly conceptual / localStorage)
  │
  ├─ Every API request: Authorization: Bearer <access_token>
  │
  ├─ 401 response → attempt silent refresh via /api/v1/auth/refresh
  │   ├─ Success → retry original request with new token
  │   └─ Failure → redirect to /login (session expired)
  │
  └─ Logout → POST /api/v1/auth/logout → clear tokens → redirect /login
```

**Implementation**: `api-client.ts` wraps `fetch()` with an interceptor pattern:
- Injects `Authorization` header on every request
- On 401, queues the request, calls refresh, replays queued requests
- Prevents multiple simultaneous refresh calls (mutex pattern)
- On refresh failure, triggers `onSessionExpired()` callback in AuthProvider

**Token storage**: `localStorage` for both tokens (acceptable for B2B SaaS where XSS is mitigated by CSP headers + no user-generated HTML). The access token is short-lived (15 min) and the refresh token is validated server-side (revocable).

### 3. Role-Based Access — Three-Tier Portal

```tsx
// Route-level protection
<Route element={<ProtectedRoute />}>           {/* Must be logged in */}
  <Route element={<AppShell />}>                {/* Sidebar + header */}
    <Route path="/dashboard" element={<Dashboard />} />
    <Route path="/inventory/*" element={<InventoryRoutes />} />
    <Route path="/settings/*" element={<SettingsRoutes />} />

    <Route element={<RoleRoute roles={["admin", "owner"]} />}>  {/* Admin+ only */}
      <Route path="/shows/*" element={<ShowRoutes />} />
      <Route path="/orders/*" element={<OrderRoutes />} />
      <Route path="/shipments/*" element={<ShipmentRoutes />} />
      <Route path="/analytics/*" element={<AnalyticsRoutes />} />
    </Route>
  </Route>
</Route>
```

**Component-level protection** for fine-grained control:
```tsx
<RoleGuard roles={["owner"]}>
  <TeamManagementTab />    {/* Only visible to owners */}
</RoleGuard>
```

**Sidebar navigation** dynamically filters items based on role — Members see 3 items (Dashboard, Inventory, Settings), Admins see 7+, Owners see everything.

### 4. Data Fetching — TanStack Query Patterns

```ts
// Query key factory — prevents key collisions, enables targeted invalidation
export const queryKeys = {
  items: {
    all: ["items"] as const,
    list: (filters: ItemFilters) => ["items", "list", filters] as const,
    detail: (id: string) => ["items", "detail", id] as const,
  },
  shows: { /* same pattern */ },
  // ...
};

// Usage in components
const { data, isLoading } = useQuery({
  queryKey: queryKeys.items.list({ status: "available", cursor }),
  queryFn: () => api.items.list({ status: "available", cursor }),
  staleTime: 30_000,  // 30s before refetch
});
```

**Optimistic updates** for status transitions (start show, ship order, restore item) — UI updates immediately, rolls back on error.

**Prefetching** on hover for detail pages — when a user hovers over a show in the list, we prefetch its details so the navigation feels instant.

### 5. Styling — Tailwind + WhatTools Branding

```css
/* CSS variables for theming */
:root {
  --primary: 234 100% 30%;     /* WhatTools navy #1a237e */
  --primary-foreground: 0 0% 100%;
  --secondary: 232 48% 36%;    /* #283593 */
  --accent: 261 80% 54%;       /* Purple accent */
  --destructive: 0 84% 60%;
  --success: 142 71% 45%;
  --warning: 38 92% 50%;
}

.dark {
  --primary: 234 100% 70%;
  --background: 222 47% 11%;
  /* ... dark overrides */
}
```

### 6. API Client — Typed & Safe

Every API call is fully typed with Zod schemas that match the backend Marshmallow schemas:
```ts
const ItemSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  sku: z.string().nullable(),
  status: z.enum(["available", "sold", "reserved", "listed"]),
  cogs: z.string(),  // Decimal as string from backend
  // ...
});

// API envelope
const ApiResponse = <T>(dataSchema: z.ZodType<T>) =>
  z.object({
    data: dataSchema,
    meta: z.object({ request_id: z.string() }),
    errors: z.array(z.object({ code: z.string(), message: z.string() })).default([]),
  });
```

### 7. Deployment — Docker + Nginx

```dockerfile
# Stage 1: Build
FROM node:22-alpine AS builder
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY . .
RUN pnpm build

# Stage 2: Serve
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

Nginx handles SPA fallback (all non-API, non-asset routes → index.html) and optional `/api` reverse proxy for production.

### 8. Testing Strategy

- **Vitest** — Unit tests for utilities, hooks, and pure logic
- **React Testing Library** — Component integration tests
- **MSW (Mock Service Worker)** — API mocking for consistent test data
- No E2E tests in Phase 5 (defer to Phase 6 with Playwright)

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| Large number of screens (22) | Feature-modular architecture — each domain is isolated. Build in priority order: auth → inventory → sales → shipping → analytics → settings |
| shadcn/ui requires more upfront component work than Ant Design | We build the DataTable and AppShell once, then reuse everywhere. Most pages are variations of the same pattern: list page → detail page |
| Token in localStorage is theoretically XSS-vulnerable | Mitigated by: CSP headers (no inline scripts), no user-generated HTML rendering, short access token lifetime (15 min), server-side refresh token revocation |
| Bundle size could grow with Recharts + many pages | Code-splitting via React.lazy() + Suspense per feature module. Members never download analytics/sales/shipping code |

## Open Questions

None — all decisions are grounded in the existing backend API contracts and the user's stated preference for Option 1 (shadcn/ui). Implementation can proceed after approval.
