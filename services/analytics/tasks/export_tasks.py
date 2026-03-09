"""Celery tasks for async export generation and cleanup."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

from services.analytics.tasks.celery_app import celery_app
from services.shared.logging import get_logger

logger = get_logger("export_tasks")

EXPORTS_DIR = os.environ.get("EXPORTS_DIR", "/data/exports")


@celery_app.task(bind=True, name="services.analytics.tasks.export_tasks.generate_export")
def generate_export(self, job_id: str, account_id: str, report_type: str, fmt: str, period: str) -> dict:
    """Generate an export file (CSV or PDF) for the given job."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from services.analytics.models.models import ExportJob, ExportStatus
    from services.analytics.repositories.export_repository import ExportRepository
    from services.analytics.services.analytics_service import AnalyticsService

    db_url = os.environ.get("DATABASE_URL", "sqlite:///:memory:")
    engine = create_engine(db_url)
    session_factory = sessionmaker(bind=engine)
    db = session_factory()

    try:
        repo = ExportRepository(db)
        job = repo.get_by_id(uuid.UUID(job_id), uuid.UUID(account_id))
        if job is None:
            logger.error("Export job not found", job_id=job_id)
            return {"status": "error", "message": "Job not found"}

        # Mark processing
        job.status = ExportStatus.PROCESSING
        job.updated_at = datetime.now(timezone.utc)
        repo.save(job)
        db.commit()

        # Gather data
        svc = AnalyticsService(db, uuid.UUID(account_id))
        data = _collect_report_data(svc, report_type, period)

        # Ensure export directory exists
        account_dir = os.path.join(EXPORTS_DIR, account_id)
        os.makedirs(account_dir, exist_ok=True)

        # Generate file
        if fmt == "csv":
            from services.analytics.exporters.csv_exporter import CsvExporter
            exporter = CsvExporter()
        else:
            from services.analytics.exporters.pdf_exporter import PdfExporter
            exporter = PdfExporter()

        filename = f"{report_type}_{period}_{job_id[:8]}.{_extension(fmt, report_type)}"
        file_path = os.path.join(account_dir, filename)
        exporter.export(data, report_type, period, file_path)

        file_size = os.path.getsize(file_path)

        # Mark completed
        job.status = ExportStatus.COMPLETED
        job.file_path = file_path
        job.file_size = file_size
        job.updated_at = datetime.now(timezone.utc)
        repo.save(job)
        db.commit()

        logger.info("Export completed", job_id=job_id, file_size=file_size)
        return {"status": "completed", "file_path": file_path, "file_size": file_size}

    except Exception as exc:
        db.rollback()
        # Try to mark job as failed
        try:
            job = repo.get_by_id(uuid.UUID(job_id), uuid.UUID(account_id))
            if job:
                job.status = ExportStatus.FAILED
                job.error_message = str(exc)[:1000]
                job.updated_at = datetime.now(timezone.utc)
                repo.save(job)
                db.commit()
        except Exception:
            logger.error("Failed to mark job as failed", job_id=job_id)
        logger.error("Export failed", job_id=job_id, error=str(exc))
        raise
    finally:
        db.close()
        engine.dispose()


@celery_app.task(name="services.analytics.tasks.export_tasks.cleanup_expired_exports")
def cleanup_expired_exports() -> dict:
    """Delete expired export files and mark jobs."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from services.analytics.repositories.export_repository import ExportRepository

    db_url = os.environ.get("DATABASE_URL", "sqlite:///:memory:")
    engine = create_engine(db_url)
    session_factory = sessionmaker(bind=engine)
    db = session_factory()

    try:
        repo = ExportRepository(db)
        expired = repo.get_expired()
        cleaned = 0

        for job in expired:
            # Delete file if it exists
            if job.file_path and os.path.exists(job.file_path):
                os.remove(job.file_path)
            job.deleted_at = datetime.now(timezone.utc)
            repo.save(job)
            cleaned += 1

        db.commit()
        logger.info("Cleaned up expired exports", count=cleaned)
        return {"cleaned": cleaned}
    except Exception as exc:
        db.rollback()
        logger.error("Cleanup failed", error=str(exc))
        raise
    finally:
        db.close()
        engine.dispose()


def _collect_report_data(svc: AnalyticsService, report_type: str, period: str) -> dict:
    """Collect analytics data for the specified report type."""
    if report_type == "full":
        return {
            "summary": svc.get_summary(period),
            "categories": svc.get_category_performance(period),
            "shows": svc.get_show_performance(period),
            "trends": svc.get_trends(period),
            "top_items": svc.get_top_items(period),
        }
    elif report_type == "summary":
        return {"summary": svc.get_summary(period)}
    elif report_type == "categories":
        return {"categories": svc.get_category_performance(period)}
    elif report_type == "shows":
        return {"shows": svc.get_show_performance(period)}
    elif report_type == "trends":
        return {"trends": svc.get_trends(period)}
    elif report_type == "top_items":
        return {"top_items": svc.get_top_items(period)}
    else:
        return {}


def _extension(fmt: str, report_type: str) -> str:
    """Determine file extension."""
    if fmt == "csv" and report_type == "full":
        return "zip"
    return fmt
