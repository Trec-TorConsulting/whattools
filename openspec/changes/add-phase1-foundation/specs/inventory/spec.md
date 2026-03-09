## ADDED Requirements

### Requirement: Inventory Item CRUD
The system SHALL provide full Create, Read, Update, Delete operations for inventory items, scoped to the authenticated user's account.

#### Scenario: Create item
- **WHEN** an authenticated user submits a valid item (name, category, COGS, quantity, status)
- **THEN** the system creates the item under the user's account
- **AND** returns a 201 response with the created item
- **AND** logs an audit entry

#### Scenario: Create item exceeds free tier
- **WHEN** a free-tier account with 50 items attempts to create another item
- **THEN** the system returns a 403 Forbidden error indicating the plan limit is reached

#### Scenario: Read item
- **WHEN** an authenticated user requests an item by ID
- **THEN** the system returns the item if it belongs to the user's account
- **AND** returns 404 if the item does not exist or belongs to another account

#### Scenario: List items with pagination
- **WHEN** an authenticated user requests their item list
- **THEN** the system returns a paginated list (cursor-based) of non-deleted items for their account
- **AND** includes pagination metadata (next cursor, total count)

#### Scenario: Update item
- **WHEN** an authenticated user updates an item they own
- **THEN** the system updates the item, sets updated_at timestamp
- **AND** logs an audit entry with old and new values

#### Scenario: Delete item (soft)
- **WHEN** an authenticated user deletes an item
- **THEN** the system sets deleted_at timestamp (soft delete)
- **AND** the item no longer appears in default listings
- **AND** logs an audit entry

#### Scenario: Cross-account access denied
- **WHEN** a user attempts to read, update, or delete an item belonging to another account
- **THEN** the system returns a 404 Not Found (not 403, to prevent ID enumeration)

### Requirement: Category CRUD
The system SHALL provide full CRUD for item categories, scoped to the authenticated user's account.

#### Scenario: Create category
- **WHEN** an authenticated user submits a valid category name
- **THEN** the system creates the category under the user's account
- **AND** returns a 201 response

#### Scenario: Duplicate category name
- **WHEN** a user creates a category with a name that already exists in their account
- **THEN** the system returns a 409 Conflict error

#### Scenario: List categories
- **WHEN** an authenticated user requests their categories
- **THEN** the system returns all non-deleted categories for their account

#### Scenario: Update category
- **WHEN** an authenticated user updates a category name
- **THEN** the system updates the category and logs an audit entry

#### Scenario: Delete category
- **WHEN** an authenticated user deletes a category
- **THEN** the system soft-deletes the category
- **AND** items in that category retain their category reference but the category is marked deleted

### Requirement: Inventory Search and Filtering
The system SHALL allow searching and filtering inventory items by multiple criteria.

#### Scenario: Search by name
- **WHEN** a user searches items with a text query
- **THEN** the system returns items where the name contains the query (case-insensitive)

#### Scenario: Filter by category
- **WHEN** a user filters items by category ID
- **THEN** the system returns only items in that category

#### Scenario: Filter by status
- **WHEN** a user filters items by status (e.g., available, sold, reserved)
- **THEN** the system returns only items with that status

#### Scenario: Filter by price range
- **WHEN** a user filters items by min and/or max COGS
- **THEN** the system returns only items within the specified price range

#### Scenario: Combined filters with pagination
- **WHEN** a user applies multiple filters simultaneously
- **THEN** the system applies all filters with AND logic and returns paginated results

### Requirement: Soft Delete and Restore
The system SHALL support viewing and restoring soft-deleted inventory items within a 30-day window.

#### Scenario: List deleted items
- **WHEN** an authenticated user requests deleted items
- **THEN** the system returns all soft-deleted items for their account that are within the 30-day retention period

#### Scenario: Restore deleted item
- **WHEN** an authenticated user restores a soft-deleted item
- **THEN** the system clears the deleted_at timestamp
- **AND** the item reappears in normal listings
- **AND** logs an audit entry

#### Scenario: Restore respects tier limits
- **WHEN** a free-tier user with 50 items attempts to restore a deleted item
- **THEN** the system returns a 403 Forbidden error indicating the plan limit is reached

### Requirement: 30-Day Purge
The system SHALL permanently delete soft-deleted records after 30 days via an automated scheduled job.

#### Scenario: Purge expired records
- **WHEN** the daily purge job runs
- **THEN** the system permanently deletes all records where deleted_at is more than 30 days ago
- **AND** logs the count of purged records

### Requirement: CSV Import
The system SHALL allow users to import inventory items from CSV files with user-driven column mapping.

#### Scenario: Upload CSV
- **WHEN** an authenticated user uploads a CSV file
- **THEN** the system parses the headers and first 5 rows as a preview
- **AND** returns detected columns and sample data for the user to create a mapping
- **AND** creates a CSVImportJob record with status "pending_mapping"

#### Scenario: Submit column mapping
- **WHEN** a user submits a column mapping (source column → WhatTools field) for a pending import job
- **THEN** the system validates the mapping (required fields: name; optional: category, cogs, quantity, status, description)
- **AND** begins importing rows asynchronously (Celery task)
- **AND** returns the job ID for status polling

#### Scenario: Import success
- **WHEN** all rows in the CSV are valid
- **THEN** the system creates all items under the user's account
- **AND** updates the job status to "completed" with total count

#### Scenario: Import with partial errors
- **WHEN** some rows have validation errors (missing required fields, invalid data types)
- **THEN** the system imports valid rows and skips invalid ones
- **AND** updates the job status to "completed_with_errors"
- **AND** stores per-row error details on the job for the user to review

#### Scenario: Import exceeds tier limit
- **WHEN** importing rows would exceed the free tier's 50-item limit
- **THEN** the system imports up to the limit and marks remaining rows as skipped with reason "tier_limit_exceeded"

#### Scenario: File size and row limits
- **WHEN** a CSV exceeds 10,000 rows or 10MB file size
- **THEN** the system returns a 413 Payload Too Large error

### Requirement: Inventory Event Publishing
The system SHALL publish events to Redis Pub/Sub for all inventory mutations.

#### Scenario: Item lifecycle events
- **WHEN** an item is created, updated, deleted, or restored
- **THEN** the system publishes an event (e.g., inventory.item.created, inventory.item.updated) to Redis Pub/Sub
- **AND** the event payload includes item_id, account_id, action, and timestamp

#### Scenario: CSV import events
- **WHEN** a CSV import job completes
- **THEN** the system publishes an inventory.import.completed event with job_id, account_id, success_count, and error_count
