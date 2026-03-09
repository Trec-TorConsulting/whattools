# Phase 4 Design: Advanced Analytics & Export Reports

## Show Time Optimization

### Data Sources
- Show model: `scheduled_at`, `started_at`, `ended_at`, `status`
- Order model: `sale_price`, `profit`, `platform_fees`, joined to shows
- Only completed shows counted (cancelled/planned excluded)
- Seller's own data only — strict `account_id` isolation

### Algorithm
1. Group completed shows by day-of-week and hour-of-day (from `started_at`)
2. Calculate per-slot metrics: avg revenue, avg profit, avg order count, show count
3. Rank time slots by a composite score: `0.5 * normalized_profit + 0.3 * normalized_revenue + 0.2 * normalized_order_count`
4. Return top slots as actionable recommendations with supporting data
5. Also return category-level insights: which categories perform best at which times
6. Minimum data threshold: require ≥3 completed shows before generating suggestions

### Response Shape
```json
{
  "data": {
    "total_shows_analyzed": 42,
    "recommendations": [
      {
        "rank": 1,
        "day_of_week": "Saturday",
        "hour": 19,
        "label": "Saturday 7:00 PM",
        "score": 0.95,
        "avg_revenue": 450.00,
        "avg_profit": 180.00,
        "avg_orders": 12,
        "show_count": 8
      }
    ],
    "category_insights": [
      {
        "category": "Trading Cards",
        "best_day": "Saturday",
        "best_hour": 19,
        "avg_profit": 210.00
      }
    ],
    "avoid_slots": [
      {
        "day_of_week": "Tuesday",
        "hour": 10,
        "label": "Tuesday 10:00 AM",
        "avg_revenue": 45.00,
        "avg_profit": -5.00,
        "show_count": 3
      }
    ]
  }
}
```

## Export Reports

### Architecture
- Celery task-based async generation
- ExportJob model tracks: format, report_type, status, file_path, error_message, expires_at
- File storage: local volume mount (`/data/exports/`) — K8S PersistentVolume
- Files auto-expire after 7 days (Celery periodic task purges)
- Download endpoint streams file directly (no redirect)

### Export Types
| report_type | Description | Data Source |
|-------------|-------------|------------|
| `summary` | Revenue/profit summary | `get_summary()` |
| `categories` | Category performance | `get_category_performance()` |
| `shows` | Show performance | `get_show_performance()` |
| `trends` | Time-series trends | `get_trends()` |
| `top_items` | Top performing items | `get_top_items()` |
| `full` | Combined report (all above) | All methods |

### Formats
- **CSV**: Flat tabular data, one sheet per report type. For `full` report, generates a ZIP with multiple CSV files.
- **PDF**: Professional layout with ReportLab. Includes:
  - Header with account name, report period, generation date
  - Summary stats in table format
  - Embedded charts (matplotlib generates PNG, embedded in PDF):
    - Revenue/profit trend line chart
    - Category breakdown bar chart
    - Top items horizontal bar chart
  - Footer with page numbers

### PDF Technology Stack
- **ReportLab** (>=4.0): PDF generation, table layout, image embedding
- **matplotlib** (>=3.9): Chart generation (saved as in-memory PNG, embedded in PDF)

### API Flow
1. `POST /api/v1/analytics/exports` — Initiate export (returns job ID, status=pending)
2. Celery worker picks up job, generates file, updates status=completed
3. `GET /api/v1/analytics/exports` — List user's exports (with status)
4. `GET /api/v1/analytics/exports/<id>` — Get export status
5. `GET /api/v1/analytics/exports/<id>/download` — Stream file download

### ExportJob Model
```
export_jobs table:
  id: UUID PK
  account_id: UUID FK → accounts.id
  report_type: String(20)  # summary, categories, shows, trends, top_items, full
  format: String(10)       # csv, pdf
  period: String(10)       # 7d, 30d, 90d, 365d, all
  status: String(20)       # pending, processing, completed, failed
  file_path: String(1024)  # relative path to generated file
  file_size: Integer       # bytes
  error_message: Text      # if failed
  expires_at: DateTime     # auto-set to created_at + 7 days
  created_at, updated_at, deleted_at
```

## Grafana Loki + Grafana Deployment

### Components
- **Promtail** (DaemonSet): Collects container logs from K8S nodes, ships to Loki. Standard and most stable agent.
- **Loki** (StatefulSet): Log aggregation backend. Single-binary mode for MVP scale.
- **Grafana** (Deployment): Dashboard UI with pre-configured Loki datasource.

### K8S Manifests
```
k8s/prod/
├── loki.yaml          # Loki StatefulSet + Service + ConfigMap
├── promtail.yaml      # Promtail DaemonSet + ConfigMap + RBAC
├── grafana.yaml       # Grafana Deployment + Service + ConfigMap
└── grafana-dashboards/ # Dashboard JSON ConfigMaps
```

### Pre-Built Dashboards
1. **Service Overview**: Request counts, error rates, response times per service
2. **Error Explorer**: Filter logs by level=ERROR, search by service/request-id
3. **Health Monitor**: Service health status, pod restarts, resource usage queries

### Grafana Access
- Exposed via Traefik ingress at `grafana.whattools.trector.com`
- Default admin credentials in K8S Secret (change on first login)

## Celery Worker Infrastructure

### Analytics Worker
- New Celery app in `services/analytics/tasks/`
- Broker: Redis (same instance, different DB: `/2`)
- Result backend: Redis
- Worker Dockerfile: extends analytics base, runs `celery -A services.analytics.tasks worker`
- K8S: Separate Deployment for worker (no Service needed — no HTTP)
- Docker Compose: `analytics-worker` service

### Task Registration
- `generate_export`: Main export task (CSV or PDF generation)
- `cleanup_expired_exports`: Periodic task (runs daily, deletes files + marks jobs expired)
