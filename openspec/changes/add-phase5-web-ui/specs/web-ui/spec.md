## ADDED Requirements

### Requirement: Web Application Shell
The system SHALL provide a single-page web application served at the root URL that wraps all authenticated pages in a consistent layout with sidebar navigation, top header bar, and main content area.

#### Scenario: Authenticated user sees app shell
- **WHEN** an authenticated user navigates to any protected route
- **THEN** the page renders with a sidebar containing navigation links, a top header with user avatar and theme toggle, and a main content area displaying the current page

#### Scenario: Sidebar reflects user role
- **WHEN** a user with role "member" views the sidebar
- **THEN** only Dashboard, Inventory, and Settings navigation items are visible
- **WHEN** a user with role "admin" views the sidebar
- **THEN** Dashboard, Inventory, Shows, Orders, Shipments, Analytics, and Settings items are visible
- **WHEN** a user with role "owner" views the sidebar
- **THEN** all navigation items are visible including team management

#### Scenario: Mobile responsive layout
- **WHEN** the viewport width is below 768px
- **THEN** the sidebar collapses to a hamburger menu accessible from the header

### Requirement: Dark Mode
The system SHALL support a dark mode theme toggle that persists the user's preference.

#### Scenario: Theme toggle
- **WHEN** the user clicks the theme toggle in the header
- **THEN** the application switches between light and dark color schemes
- **AND** the preference is saved to localStorage

#### Scenario: System preference detection
- **WHEN** the user has not set a manual preference
- **THEN** the application defaults to the operating system's color scheme preference

### Requirement: User Authentication Flow
The system SHALL provide public pages for login, registration, password reset, email verification, and team invite acceptance.

#### Scenario: Login
- **WHEN** a user submits valid email and password on the login page
- **THEN** the system calls POST /api/v1/auth/login and stores the returned access and refresh tokens
- **AND** redirects the user to the dashboard

#### Scenario: Login failure
- **WHEN** a user submits invalid credentials
- **THEN** the system displays the error message from the API without revealing whether the email exists

#### Scenario: Registration
- **WHEN** a user fills in name, email, password, and account name on the register page
- **THEN** the system calls POST /api/v1/auth/register and shows a success message directing the user to check their email for verification

#### Scenario: Password reset request
- **WHEN** a user submits their email on the forgot password page
- **THEN** the system calls POST /api/v1/auth/password-reset and shows a generic "check your email" confirmation regardless of whether the email exists

#### Scenario: Password reset completion
- **WHEN** a user navigates to the reset password page with a valid token in the URL and submits a new password
- **THEN** the system calls POST /api/v1/auth/password-reset/confirm and redirects to the login page on success

#### Scenario: Email verification
- **WHEN** a user navigates to the verify email page with a token in the URL
- **THEN** the system automatically calls POST /api/v1/auth/verify-email and displays success or error

#### Scenario: Accept team invite
- **WHEN** a user navigates to the invite acceptance page with a valid token
- **THEN** the system displays a registration form (name, password) and on submission creates the user under the inviting account

### Requirement: Automatic Token Refresh
The system SHALL automatically refresh expired access tokens using the stored refresh token without user interaction.

#### Scenario: Transparent refresh on 401
- **WHEN** an API request returns 401 (token expired)
- **THEN** the system calls POST /api/v1/auth/refresh with the stored refresh token
- **AND** retries the original request with the new access token

#### Scenario: Session expiry
- **WHEN** the refresh token is also expired or revoked
- **THEN** the system clears all stored tokens, shows a session expired message, and redirects to the login page

#### Scenario: Concurrent refresh prevention
- **WHEN** multiple API requests fail with 401 simultaneously
- **THEN** only one refresh request is made and all pending requests wait for and use the new token

### Requirement: Role-Based Route Protection
The system SHALL enforce role-based access at the route level, preventing users from accessing pages beyond their role's permissions.

#### Scenario: Unauthenticated access
- **WHEN** an unauthenticated user navigates to any protected route
- **THEN** the system redirects to the login page and preserves the intended destination for post-login redirect

#### Scenario: Insufficient role
- **WHEN** a user with role "member" navigates to /shows, /orders, /shipments, or /analytics
- **THEN** the system redirects to /dashboard

#### Scenario: Role-appropriate access
- **WHEN** a user with role "admin" navigates to /shows
- **THEN** the page loads normally

### Requirement: Dashboard
The system SHALL display a role-appropriate dashboard as the landing page after login, showing relevant metrics and quick actions.

#### Scenario: Member dashboard
- **WHEN** a member views the dashboard
- **THEN** inventory statistics are displayed: total items, items by status breakdown, and recent item activity

#### Scenario: Admin dashboard
- **WHEN** an admin views the dashboard
- **THEN** sales summary (total revenue, profit, order count for the last 30 days), recent orders, overdue shipment alerts, and inventory stats are displayed

#### Scenario: Owner dashboard
- **WHEN** an owner views the dashboard
- **THEN** everything the admin sees plus team overview (member count, role breakdown) and account plan usage (items used vs limit, members vs limit) are displayed

### Requirement: Inventory Management
The system SHALL provide inventory item CRUD, category management, CSV import, and deleted item recovery through the web interface.

#### Scenario: Items list with search and filters
- **WHEN** a user navigates to the items list page
- **THEN** a searchable, filterable data table is displayed with columns: name, SKU, status, category, COGS, quantity, and updated date
- **AND** the user can filter by status and category, search by name/SKU, and paginate with cursor-based pagination

#### Scenario: Create item
- **WHEN** a user fills in the item creation form with valid data and submits
- **THEN** the system calls POST /api/v1/items and adds the new item to the list with an optimistic update

#### Scenario: Edit item
- **WHEN** a user modifies an existing item's fields and saves
- **THEN** the system calls PUT /api/v1/items/{id} and updates the displayed data

#### Scenario: Delete item
- **WHEN** a user clicks delete on an item and confirms in the confirmation dialog
- **THEN** the system calls DELETE /api/v1/items/{id} (soft delete) and removes it from the active list

#### Scenario: CSV import wizard
- **WHEN** a user initiates a CSV import
- **THEN** a three-step wizard guides them through: (1) file upload with preview of detected columns, (2) column mapping with dropdowns for each required field, (3) import progress and results summary

#### Scenario: Categories management
- **WHEN** a user views the categories page
- **THEN** all categories are listed with item counts, and the user can create new categories inline, edit names, and delete categories with confirmation

#### Scenario: Restore deleted items
- **WHEN** a user views the deleted items page
- **THEN** soft-deleted items are shown with their deletion date and remaining retention time, and the user can restore items back to active status

### Requirement: Shows Management
The system SHALL provide show lifecycle management for admin and owner roles, including creation, status transitions, and order viewing.

#### Scenario: Shows list
- **WHEN** an admin or owner navigates to the shows page
- **THEN** shows are displayed in a filterable list/table with status badges, scheduled time, and key metrics (revenue, orders, profit per completed show)

#### Scenario: Show detail with orders
- **WHEN** a user views a show's detail page
- **THEN** the show information is displayed along with its orders table, revenue/profit summary, and status transition action buttons

#### Scenario: Show status transitions
- **WHEN** a user clicks "Start Show" on a planned show
- **THEN** a confirmation dialog appears, and on confirmation the system calls POST /api/v1/shows/{id}/start
- **WHEN** a user clicks "Complete Show" on a live show
- **THEN** the system calls POST /api/v1/shows/{id}/complete and updates the UI
- **WHEN** a user clicks "Cancel Show" on a planned or live show
- **THEN** a destructive confirmation dialog warns about cascading order cancellations before proceeding

### Requirement: Orders Management
The system SHALL provide order viewing and management for admin and owner roles with profit visibility.

#### Scenario: Orders list
- **WHEN** an admin or owner navigates to the orders page
- **THEN** orders are displayed in a data table with columns: buyer, item, sale price, profit, status, show, and date

#### Scenario: Order detail with profit breakdown
- **WHEN** a user views an order's detail page
- **THEN** the full profit breakdown is visible: sale price - platform fees - shipping cost - COGS = profit

#### Scenario: Cancel order
- **WHEN** a user cancels a pending order
- **THEN** the system calls POST /api/v1/orders/{id}/cancel, inventory is restored automatically by the backend, and the UI updates

### Requirement: Shipments Management
The system SHALL provide shipment tracking, status management, bulk operations, and packing list generation.

#### Scenario: Shipments list with overdue alerts
- **WHEN** a user views the shipments page
- **THEN** shipments are listed with status badges, and overdue shipments (past ship-by date) are highlighted with a warning indicator

#### Scenario: Shipment status stepper
- **WHEN** a user views a shipment detail page
- **THEN** a visual status stepper shows the current position in the lifecycle: pending → label created → shipped → delivered

#### Scenario: Bulk ship from show
- **WHEN** a user initiates bulk shipment creation for a show
- **THEN** the system calls POST /api/v1/shipments/bulk with the show_id and creates shipments for all pending orders

#### Scenario: Packing list print view
- **WHEN** a user views the packing list for a show
- **THEN** orders are grouped by buyer with item checklists, and the page has a print-optimized CSS layout activated via @media print

### Requirement: Analytics Dashboard
The system SHALL provide visual analytics with charts, metrics, and AI-powered show scheduling recommendations.

#### Scenario: Summary metrics with period selector
- **WHEN** a user views the analytics dashboard
- **THEN** summary stat cards display total revenue, total profit, order count, and average per show for the selected time period
- **AND** a period selector allows switching between 7d, 30d, 90d, 365d, and all-time views

#### Scenario: Trend visualization
- **WHEN** analytics data is loaded
- **THEN** an area chart displays revenue and profit trends over the selected time period

#### Scenario: Category performance
- **WHEN** analytics data is loaded
- **THEN** a bar chart displays revenue breakdown by category

#### Scenario: Top performing items
- **WHEN** analytics data is loaded
- **THEN** a ranked list or bar chart shows the top items sorted by revenue, profit, or quantity (user-selectable)

#### Scenario: Show time suggestions
- **WHEN** the user has at least 3 completed shows
- **THEN** recommended time slots with confidence scores, average metrics, and avoid-slots are displayed as actionable suggestion cards
- **WHEN** the user has fewer than 3 completed shows
- **THEN** a message explains more show data is needed for recommendations

### Requirement: Export Reports
The system SHALL allow users to create, monitor, and download CSV and PDF export reports.

#### Scenario: Create export
- **WHEN** a user selects a report type and format and submits the export creation form
- **THEN** the system calls POST /api/v1/analytics/exports and adds the job to the exports list with PENDING status

#### Scenario: Export status tracking
- **WHEN** a user views the exports page
- **THEN** all export jobs are listed with status badges (pending, processing, completed, failed) and the list auto-refreshes

#### Scenario: Download completed export
- **WHEN** a user clicks download on a completed export
- **THEN** the browser downloads the file via GET /api/v1/analytics/exports/{id}/download

### Requirement: Settings and Profile Management
The system SHALL provide user profile editing, team management (for authorized roles), and account settings (for owners).

#### Scenario: Profile editing
- **WHEN** any authenticated user navigates to Settings → Profile
- **THEN** they can update their name, email, and password (with current password verification)

#### Scenario: Team management
- **WHEN** an owner or admin views Settings → Team
- **THEN** a list of team members with their roles is displayed
- **AND** the user can invite new members (email + role), and owners can change member roles or remove members

#### Scenario: Account settings
- **WHEN** an owner views Settings → Account
- **THEN** the account name can be edited, plan tier is displayed, and usage statistics (items count / limit, members count / limit) are shown

### Requirement: Reusable Data Table
The system SHALL provide a reusable, accessible data table component used across all list pages with consistent behavior.

#### Scenario: Table features
- **WHEN** a data table is rendered on any list page
- **THEN** it supports column sorting, row selection with checkboxes, a search input, filter controls, and cursor-based pagination with "Load More" or "Next" controls

#### Scenario: Empty state
- **WHEN** a data table has no matching results
- **THEN** an empty state placeholder is displayed with a descriptive message and optional call-to-action button (e.g., "Create your first item")

#### Scenario: Loading state
- **WHEN** table data is being fetched
- **THEN** a skeleton loader with shimmer animation is displayed matching the table's layout

### Requirement: Deployment Packaging
The system SHALL be packaged as a Docker container serving the built SPA via nginx with proper SPA routing fallback.

#### Scenario: Docker build
- **WHEN** the Dockerfile is built
- **THEN** a multi-stage build compiles the React app and copies the output to an nginx container

#### Scenario: SPA routing
- **WHEN** a user directly navigates to a deep link (e.g., /inventory/items)
- **THEN** nginx serves index.html and React Router handles client-side routing

#### Scenario: Kubernetes deployment
- **WHEN** the web application is deployed to Kubernetes
- **THEN** a Deployment, Service, and Ingress route are configured to serve the app at the root domain
