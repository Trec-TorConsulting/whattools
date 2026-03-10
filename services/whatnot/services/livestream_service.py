"""Livestream sync service — pull livestreams from Whatnot, map to shows."""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.sales.models.models import Show, ShowStatus
from services.shared.logging import get_logger
from services.whatnot.graphql.client import WhatnotClient, WhatnotApiError
from services.whatnot.graphql.queries import LIVESTREAMS_QUERY
from services.whatnot.models import SyncType
from services.whatnot.repositories.whatnot_repository import SyncLogRepository

logger = get_logger("whatnot.livestream_service")


class LivestreamServiceError(Exception):
    """Error during livestream sync operations."""

    def __init__(self, message: str, code: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class LivestreamService:
    """Syncs livestreams between Whatnot and WhatTools shows."""

    def __init__(self, db: Session, account_id: uuid.UUID, client: WhatnotClient) -> None:
        self.db = db
        self.account_id = account_id
        self.client = client
        self.sync_log_repo = SyncLogRepository(db, account_id)

    def pull_livestreams(self) -> dict[str, Any]:
        """Pull livestreams from Whatnot and upsert as local shows.

        Returns:
            Dict with sync stats.
        """
        sync_log = self.sync_log_repo.create(SyncType.LIVESTREAMS)
        sync_log.status = "running"
        self.db.flush()

        created = 0
        updated = 0
        failed = 0
        cursor = None

        try:
            while True:
                variables: dict[str, Any] = {"first": 50}
                if cursor:
                    variables["after"] = cursor

                data = self.client.execute(LIVESTREAMS_QUERY, variables)
                conn = data.get("livestreams", {})
                edges = conn.get("edges", [])

                for edge in edges:
                    node = edge.get("node", {})
                    try:
                        was_created = self._upsert_livestream(node)
                        if was_created:
                            created += 1
                        else:
                            updated += 1
                    except Exception as exc:
                        logger.warning("livestream_pull_error", whatnot_id=node.get("id"), error=str(exc))
                        failed += 1

                page_info = conn.get("pageInfo", {})
                if not page_info.get("hasNextPage"):
                    break
                cursor = page_info.get("endCursor")

            self.db.commit()
            self.sync_log_repo.complete(
                sync_log,
                items_synced=created + updated,
                items_created=created,
                items_updated=updated,
                items_failed=failed,
            )
            self.db.commit()

        except WhatnotApiError as exc:
            self.db.rollback()
            self.sync_log_repo.fail(sync_log, str(exc))
            self.db.commit()
            raise LivestreamServiceError(str(exc), "sync_error", 502) from exc

        return {
            "synced": created + updated,
            "created": created,
            "updated": updated,
            "failed": failed,
        }

    def _upsert_livestream(self, whatnot_livestream: dict[str, Any]) -> bool:
        """Create or update a local show from Whatnot livestream data.

        Returns:
            True if created, False if updated.
        """
        whatnot_id = whatnot_livestream["id"]
        title = whatnot_livestream.get("title", "Untitled Livestream")

        query = (
            select(Show)
            .where(Show.account_id == self.account_id)
            .where(Show.whatnot_livestream_id == whatnot_id)
            .where(Show.deleted_at.is_(None))
        )
        existing = self.db.execute(query).scalar_one_or_none()

        if existing:
            existing.title = title
            existing.updated_at = datetime.now(timezone.utc)
            self.db.flush()
            return False

        show = Show(
            account_id=self.account_id,
            title=title,
            platform="whatnot",
            status=ShowStatus.COMPLETED,
        )
        show.whatnot_livestream_id = whatnot_id
        self.db.add(show)
        self.db.flush()
        return True
