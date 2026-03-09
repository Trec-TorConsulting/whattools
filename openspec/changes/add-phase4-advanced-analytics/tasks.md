## 1. Show Time Optimization
- [ ] 1.1 Add `get_show_time_suggestions()` method to AnalyticsService
- [ ] 1.2 Add `/show-time-suggestions` route to analytics routes
- [ ] 1.3 Write service-layer tests for show time optimization
- [ ] 1.4 Write route tests for show time optimization endpoint

## 2. Export Infrastructure
- [ ] 2.1 Create ExportJob model (`export_jobs` table)
- [ ] 2.2 Create ExportJobSchema (create, response, list)
- [ ] 2.3 Create ExportRepository (CRUD for export jobs)
- [ ] 2.4 Create Alembic migration for `export_jobs` table
- [ ] 2.5 Add `reportlab` and `matplotlib` to pyproject.toml dependencies

## 3. Celery Worker
- [ ] 3.1 Create `services/analytics/tasks/celery_app.py` (Celery app config)
- [ ] 3.2 Create `services/analytics/tasks/export_tasks.py` (generate_export + cleanup tasks)
- [ ] 3.3 Create analytics worker Dockerfile
- [ ] 3.4 Add `analytics-worker` to docker-compose.yml
- [ ] 3.5 Create K8S deployment for analytics worker

## 4. CSV Export Generator
- [ ] 4.1 Create `services/analytics/exporters/csv_exporter.py`
- [ ] 4.2 Support single-report CSV and full-report ZIP
- [ ] 4.3 Write CSV exporter tests

## 5. PDF Export Generator
- [ ] 5.1 Create `services/analytics/exporters/pdf_exporter.py`
- [ ] 5.2 Create chart generator (`services/analytics/exporters/charts.py`) using matplotlib
- [ ] 5.3 Build PDF layout with ReportLab (header, tables, embedded charts, footer)
- [ ] 5.4 Write PDF exporter tests
- [ ] 5.5 Write chart generator tests

## 6. Export Routes & Service
- [ ] 6.1 Add export methods to AnalyticsService (or create ExportService)
- [ ] 6.2 Create export routes: POST create, GET list, GET status, GET download
- [ ] 6.3 Write export route tests
- [ ] 6.4 Write export service tests

## 7. Gateway Integration
- [ ] 7.1 Verify gateway already routes `/api/v1/analytics/*` (no changes expected)

## 8. Grafana Loki Deployment
- [ ] 8.1 Create `k8s/prod/loki.yaml` (StatefulSet + Service + ConfigMap)
- [ ] 8.2 Create `k8s/prod/promtail.yaml` (DaemonSet + ConfigMap + RBAC)
- [ ] 8.3 Create `k8s/prod/grafana.yaml` (Deployment + Service + ConfigMap)
- [ ] 8.4 Create pre-built dashboard JSON ConfigMaps
- [ ] 8.5 Add Grafana ingress rule to `k8s/prod/ingress.yaml`

## 9. Infrastructure Updates
- [ ] 9.1 Update docker-compose.yml with export volume mount for analytics
- [ ] 9.2 Update pyproject.toml coverage omits if needed
- [ ] 9.3 Create data/exports directory and .gitkeep

## 10. Documentation
- [ ] 10.1 Update docs/architecture.md with export pipeline and Grafana stack
- [ ] 10.2 Update docs/api-guide.md with show-time-suggestions and export endpoints
- [ ] 10.3 Update docs/deployment.md with Grafana/Loki deployment steps

## 11. Final Validation
- [ ] 11.1 Run full test suite — all services must pass with ≥90% coverage
- [ ] 11.2 Git commit Phase 4
