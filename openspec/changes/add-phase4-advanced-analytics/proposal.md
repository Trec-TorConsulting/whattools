# Phase 4: Advanced Analytics & Export Reports

## Summary

Extend the analytics service with actionable show time optimization, async report export (CSV and PDF with embedded charts), and deploy Grafana Loki + Grafana for platform monitoring with pre-built dashboards.

## Motivation

Sellers need more than raw data — they need actionable recommendations to improve ROI. Optimal show time suggestions turn historical performance data into concrete scheduling advice. Export reports let sellers own their data in professional formats they can share with partners or bookkeepers. Platform monitoring via Grafana gives operators (and potential customers) confidence in system reliability.

## Scope

### In Scope
- Show time optimization endpoint (seller's own data, actionable recommendations)
- Async report export via Celery (CSV + PDF with embedded charts)
- ExportJob model and tracking (status, download URL, expiry)
- PDF generation with ReportLab + matplotlib charts
- Grafana Loki + Promtail deployment (K8S manifests)
- Grafana deployment with pre-configured Loki datasource
- Pre-built Grafana dashboards (request rates, error rates, per-service health)

### Out of Scope
- Cross-seller or Whatnot-wide data analysis
- Real-time streaming analytics
- Whatnot API integration
- S3/cloud file storage (local volume at MVP)
