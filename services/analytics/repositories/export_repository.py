"""Repository for ExportJob persistence."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.analytics.models.models import ExportJob, ExportStatus


class ExportRepository:
    """Data access for export jobs."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, job: ExportJob) -> ExportJob:
        """Persist a new export job."""
        self.db.add(job)
        self.db.flush()
        return job

    def get_by_id(self, job_id: uuid.UUID, account_id: uuid.UUID) -> ExportJob | None:
        """Get an export job by ID, scoped to account."""
        return self.db.execute(
            select(ExportJob).where(
                ExportJob.id == job_id,
                ExportJob.account_id == account_id,
                ExportJob.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

    def list_by_account(self, account_id: uuid.UUID) -> list[ExportJob]:
        """List all export jobs for an account, newest first."""
        return list(
            self.db.execute(
                select(ExportJob)
                .where(
                    ExportJob.account_id == account_id,
                    ExportJob.deleted_at.is_(None),
                )
                .order_by(ExportJob.created_at.desc())
            ).scalars().all()
        )

    def save(self, job: ExportJob) -> ExportJob:
        """Update an existing export job."""
        self.db.flush()
        return job

    def get_expired(self) -> list[ExportJob]:
        """Get all completed exports past their expiry date."""
        now = datetime.now(timezone.utc)
        return list(
            self.db.execute(
                select(ExportJob).where(
                    ExportJob.status == ExportStatus.COMPLETED,
                    ExportJob.expires_at.isnot(None),
                    ExportJob.expires_at <= now,
                    ExportJob.deleted_at.is_(None),
                )
            ).scalars().all()
        )
