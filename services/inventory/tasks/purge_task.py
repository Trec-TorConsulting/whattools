"""Celery task for purging soft-deleted records older than 30 days."""

from services.inventory.repositories.inventory_repository import CategoryRepository, ItemRepository
from services.shared.logging import get_logger

logger = get_logger("purge_task")


def run_purge(db_session_factory) -> dict[str, int]:  # type: ignore[no-untyped-def]
    """Purge expired soft-deleted items and categories.

    Designed to be called from a Celery beat task or a CLI command.

    Args:
        db_session_factory: A callable that returns a SQLAlchemy Session.

    Returns:
        Dict with counts of purged items and categories.
    """
    session = db_session_factory()
    try:
        items_purged = ItemRepository.purge_expired(session)
        categories_purged = CategoryRepository.purge_expired(session)
        session.commit()

        logger.info(
            "purge_completed",
            items_purged=items_purged,
            categories_purged=categories_purged,
        )

        return {
            "items_purged": items_purged,
            "categories_purged": categories_purged,
        }
    except Exception:
        session.rollback()
        logger.exception("purge_failed")
        raise
    finally:
        session.close()
