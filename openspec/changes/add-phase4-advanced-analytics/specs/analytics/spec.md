# Analytics Service — Phase 4 Spec Delta

## ADDED Requirements

### Requirement: Show Time Optimization
The analytics service SHALL provide actionable show time scheduling recommendations based on the seller's own historical show performance data.

- Only completed shows (status=completed) with `started_at` set are analyzed
- Recommendations ranked by composite score: profit (50%), revenue (30%), order count (20%)
- Minimum threshold: ≥3 completed shows required before generating suggestions
- Returns top recommended slots, category-level insights, and slots to avoid
- Data scoped strictly to `account_id` — no cross-seller data

#### Scenario: Seller with enough show history gets recommendations
- **GIVEN** a seller with 10 completed shows across different days and times
- **WHEN** the seller requests `GET /api/v1/analytics/show-time-suggestions`
- **THEN** the response includes ranked time slots with avg_revenue, avg_profit, avg_orders, show_count
- **AND** category_insights showing best category-time combinations
- **AND** avoid_slots showing underperforming time slots

#### Scenario: Seller with insufficient data gets informative response
- **GIVEN** a seller with fewer than 3 completed shows
- **WHEN** the seller requests `GET /api/v1/analytics/show-time-suggestions`
- **THEN** the response returns an empty recommendations list with total_shows_analyzed reflecting actual count

### Requirement: Async Report Export
The analytics service SHALL support asynchronous export of analytics data as CSV or PDF files with embedded charts.

- Export initiated via `POST /api/v1/analytics/exports` with report_type and format
- Supported report types: summary, categories, shows, trends, top_items, full
- Supported formats: csv, pdf
- Full report in CSV format produces a ZIP with one CSV per report type
- PDF includes embedded matplotlib charts: trend line, category bar, top items bar
- Export processed asynchronously via Celery worker
- ExportJob model tracks status: pending → processing → completed / failed
- Generated files expire after 7 days; periodic task cleans up expired files
- Download via `GET /api/v1/analytics/exports/<id>/download` streams the file

#### Scenario: Seller exports a PDF summary report
- **GIVEN** a seller with sales data
- **WHEN** the seller sends `POST /api/v1/analytics/exports` with report_type=summary, format=pdf, period=30d
- **THEN** an ExportJob is created with status=pending and a job ID is returned
- **AND** a Celery task is enqueued to generate the PDF

#### Scenario: Seller exports a full CSV report
- **GIVEN** a seller with sales data
- **WHEN** the seller sends `POST /api/v1/analytics/exports` with report_type=full, format=csv, period=all
- **THEN** an ExportJob is created and a Celery task generates a ZIP with 5 CSV files

#### Scenario: Seller lists their exports
- **GIVEN** a seller with 3 previous exports
- **WHEN** the seller sends `GET /api/v1/analytics/exports`
- **THEN** all 3 exports are returned with their status, format, type, and creation time

#### Scenario: Seller downloads a completed export
- **GIVEN** a completed export job with a generated file
- **WHEN** the seller sends `GET /api/v1/analytics/exports/<id>/download`
- **THEN** the file is streamed to the client with correct content type and filename

### Requirement: ExportJob Data Model
The system SHALL persist export job records with full lifecycle tracking.

- Fields: id, account_id, report_type, format, period, status, file_path, file_size, error_message, expires_at
- Status enum: pending, processing, completed, failed
- expires_at auto-set to created_at + 7 days
- Soft delete support via BaseModel

#### Scenario: ExportJob persisted with correct defaults
- **GIVEN** an export request for report_type=trends, format=csv, period=30d
- **WHEN** the ExportJob is created
- **THEN** status defaults to pending
- **AND** expires_at is set to 7 days from creation

### Requirement: Grafana Loki Log Aggregation
The platform SHALL deploy Grafana Loki for centralized log aggregation in the K8S cluster.

- Loki runs as a StatefulSet in single-binary mode
- Promtail runs as a DaemonSet to collect container logs from all nodes
- Loki ConfigMap defines schema, storage, and retention (30 days)
- RBAC configured for Promtail to read pod logs

#### Scenario: Logs from all services are aggregated
- **GIVEN** all WhatTools services are deployed in K8S
- **WHEN** Promtail collects logs from each pod
- **THEN** all logs are queryable in Loki via LogQL by service label

### Requirement: Grafana Dashboards
The platform SHALL deploy Grafana with pre-configured Loki datasource and pre-built dashboards.

- Grafana Deployment with persistent storage for settings
- Loki datasource auto-provisioned via ConfigMap
- Pre-built dashboards: Service Overview, Error Explorer, Health Monitor
- Grafana exposed via Traefik ingress at grafana.whattools.trector.com

#### Scenario: Operator opens Grafana and sees service dashboards
- **GIVEN** Grafana is deployed with provisioned dashboards
- **WHEN** an operator navigates to grafana.whattools.trector.com
- **THEN** the Service Overview dashboard shows log-derived metrics for each WhatTools service
- **AND** the Error Explorer allows filtering error logs by service and request-id

### Requirement: Analytics Celery Worker
The analytics service SHALL include a Celery worker for async task processing.

- Separate Celery app in services/analytics/tasks/
- Redis broker (DB 2) and Redis result backend
- Worker runs in its own container with separate entrypoint
- K8S: Dedicated Deployment (no Service — no inbound HTTP)
- Docker Compose: analytics-worker service alongside analytics

#### Scenario: Export task is processed by worker
- **GIVEN** the analytics Celery worker is running
- **WHEN** an export task is enqueued
- **THEN** the worker picks up and processes the task within its Redis queue
