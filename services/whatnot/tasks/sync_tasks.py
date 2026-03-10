"""Background sync tasks for Whatnot data synchronization."""

import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from services.shared.logging import get_logger
from services.whatnot.graphql.client import WhatnotClient
from services.whatnot.models import WhatnotCredential
from services.whatnot.services.livestream_service import LivestreamService
from services.whatnot.services.oauth_service import OAuthService
from services.whatnot.services.order_service import OrderSyncService
from services.whatnot.services.product_service import ProductService
from services.whatnot.tasks.celery_app import celery_app

logger = get_logger("whatnot.sync_tasks")


def _get_db_session():
    """Create a standalone database session for Celery tasks."""
    db_url = os.environ.get("DATABASE_URL", "postgresql://whattools:whattools@localhost:5432/whattools")
    engine = create_engine(db_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return session_factory(), engine


def _get_active_accounts(db):
    """Get all accounts with active Whatnot connections."""
    query = (
        select(WhatnotCredential)
        .where(WhatnotCredential.is_active.is_(True))
        .where(WhatnotCredential.deleted_at.is_(None))
    )
    return list(db.execute(query).scalars().all())


def _get_client_for_account(db, account_id: uuid.UUID) -> WhatnotClient:
    """Get a WhatnotClient with a valid access token for an account."""
    oauth_svc = OAuthService(db)
    access_token = oauth_svc.get_access_token(account_id)
    return WhatnotClient(access_token)


@celery_app.task(bind=True, name="services.whatnot.tasks.sync_tasks.periodic_order_sync")
def periodic_order_sync(self) -> dict:
    """Sync orders for all connected accounts (runs every 15 minutes)."""
    db, engine = _get_db_session()
    results = {}

    try:
        credentials = _get_active_accounts(db)
        for cred in credentials:
            account_id = cred.account_id
            try:
                client = _get_client_for_account(db, account_id)
                svc = OrderSyncService(db, account_id, client)
                result = svc.pull_orders()
                results[str(account_id)] = result

                # Update last_sync_at
                cred.last_sync_at = datetime.now(timezone.utc)
                db.commit()

            except Exception as exc:
                db.rollback()
                logger.error("periodic_order_sync_error", account_id=str(account_id), error=str(exc))
                results[str(account_id)] = {"error": str(exc)}
    finally:
        db.close()
        engine.dispose()

    return results


@celery_app.task(bind=True, name="services.whatnot.tasks.sync_tasks.periodic_product_sync")
def periodic_product_sync(self) -> dict:
    """Sync products for all connected accounts (runs every hour)."""
    db, engine = _get_db_session()
    results = {}

    try:
        credentials = _get_active_accounts(db)
        for cred in credentials:
            account_id = cred.account_id
            try:
                client = _get_client_for_account(db, account_id)
                svc = ProductService(db, account_id, client)
                result = svc.pull_products()
                results[str(account_id)] = result
            except Exception as exc:
                db.rollback()
                logger.error("periodic_product_sync_error", account_id=str(account_id), error=str(exc))
                results[str(account_id)] = {"error": str(exc)}
    finally:
        db.close()
        engine.dispose()

    return results


@celery_app.task(bind=True, name="services.whatnot.tasks.sync_tasks.periodic_livestream_sync")
def periodic_livestream_sync(self) -> dict:
    """Sync livestreams for all connected accounts (runs every hour)."""
    db, engine = _get_db_session()
    results = {}

    try:
        credentials = _get_active_accounts(db)
        for cred in credentials:
            account_id = cred.account_id
            try:
                client = _get_client_for_account(db, account_id)
                svc = LivestreamService(db, account_id, client)
                result = svc.pull_livestreams()
                results[str(account_id)] = result
            except Exception as exc:
                db.rollback()
                logger.error("periodic_livestream_sync_error", account_id=str(account_id), error=str(exc))
                results[str(account_id)] = {"error": str(exc)}
    finally:
        db.close()
        engine.dispose()

    return results


@celery_app.task(bind=True, name="services.whatnot.tasks.sync_tasks.full_sync")
def full_sync(self, account_id: str) -> dict:
    """Run a full sync for a specific account (products, orders, livestreams)."""
    db, engine = _get_db_session()
    aid = uuid.UUID(account_id)
    results = {}

    try:
        client = _get_client_for_account(db, aid)

        try:
            product_svc = ProductService(db, aid, client)
            results["products"] = product_svc.pull_products()
        except Exception as exc:
            db.rollback()
            results["products"] = {"error": str(exc)}

        try:
            order_svc = OrderSyncService(db, aid, client)
            results["orders"] = order_svc.pull_orders()
        except Exception as exc:
            db.rollback()
            results["orders"] = {"error": str(exc)}

        try:
            livestream_svc = LivestreamService(db, aid, client)
            results["livestreams"] = livestream_svc.pull_livestreams()
        except Exception as exc:
            db.rollback()
            results["livestreams"] = {"error": str(exc)}

        # Update last_sync_at on credential
        query = (
            select(WhatnotCredential)
            .where(WhatnotCredential.account_id == aid)
            .where(WhatnotCredential.is_active.is_(True))
        )
        cred = db.execute(query).scalar_one_or_none()
        if cred:
            cred.last_sync_at = datetime.now(timezone.utc)
            db.commit()

    except Exception as exc:
        db.rollback()
        logger.error("full_sync_error", account_id=account_id, error=str(exc))
        results["error"] = str(exc)
    finally:
        db.close()
        engine.dispose()

    return results
