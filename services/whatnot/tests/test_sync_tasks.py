"""Tests for Celery sync tasks."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

TEST_ENCRYPTION_KEY = "I2z4QxvoJ-V-xCVM8R0gF8e0LJvQa6dKAnBUJbcvfwo="


@pytest.fixture(autouse=True)
def _set_env(monkeypatch):
    monkeypatch.setenv("WHATNOT_ENCRYPTION_KEY", TEST_ENCRYPTION_KEY)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")


def _make_mock_credential(account_id=None):
    cred = MagicMock()
    cred.account_id = account_id or uuid.UUID("00000000-0000-0000-0000-000000000001")
    cred.is_active = True
    cred.last_sync_at = None
    return cred


class TestPeriodicOrderSync:
    @patch("services.whatnot.tasks.sync_tasks._get_client_for_account")
    @patch("services.whatnot.tasks.sync_tasks._get_active_accounts")
    @patch("services.whatnot.tasks.sync_tasks._get_db_session")
    def test_success_one_account(self, mock_db, mock_accounts, mock_client):
        from services.whatnot.tasks.sync_tasks import periodic_order_sync

        mock_session = MagicMock()
        mock_engine = MagicMock()
        mock_db.return_value = (mock_session, mock_engine)

        cred = _make_mock_credential()
        mock_accounts.return_value = [cred]
        mock_client.return_value = MagicMock()

        with patch("services.whatnot.tasks.sync_tasks.OrderSyncService") as MockSvc:
            mock_svc = MagicMock()
            mock_svc.pull_orders.return_value = {"synced": 5}
            MockSvc.return_value = mock_svc

            result = periodic_order_sync()

        assert str(cred.account_id) in result
        assert result[str(cred.account_id)] == {"synced": 5}
        mock_session.close.assert_called_once()
        mock_engine.dispose.assert_called_once()

    @patch("services.whatnot.tasks.sync_tasks._get_active_accounts")
    @patch("services.whatnot.tasks.sync_tasks._get_db_session")
    def test_no_active_accounts(self, mock_db, mock_accounts):
        from services.whatnot.tasks.sync_tasks import periodic_order_sync

        mock_db.return_value = (MagicMock(), MagicMock())
        mock_accounts.return_value = []

        result = periodic_order_sync()
        assert result == {}

    @patch("services.whatnot.tasks.sync_tasks._get_client_for_account")
    @patch("services.whatnot.tasks.sync_tasks._get_active_accounts")
    @patch("services.whatnot.tasks.sync_tasks._get_db_session")
    def test_account_error_continues(self, mock_db, mock_accounts, mock_client):
        from services.whatnot.tasks.sync_tasks import periodic_order_sync

        mock_session = MagicMock()
        mock_db.return_value = (mock_session, MagicMock())

        cred1 = _make_mock_credential(uuid.UUID("00000000-0000-0000-0000-000000000001"))
        cred2 = _make_mock_credential(uuid.UUID("00000000-0000-0000-0000-000000000002"))
        mock_accounts.return_value = [cred1, cred2]
        mock_client.return_value = MagicMock()

        with patch("services.whatnot.tasks.sync_tasks.OrderSyncService") as MockSvc:
            mock_svc1 = MagicMock()
            mock_svc1.pull_orders.side_effect = Exception("network error")
            mock_svc2 = MagicMock()
            mock_svc2.pull_orders.return_value = {"synced": 2}
            MockSvc.side_effect = [mock_svc1, mock_svc2]

            result = periodic_order_sync()

        assert "error" in result[str(cred1.account_id)]
        assert result[str(cred2.account_id)] == {"synced": 2}


class TestPeriodicProductSync:
    @patch("services.whatnot.tasks.sync_tasks._get_client_for_account")
    @patch("services.whatnot.tasks.sync_tasks._get_active_accounts")
    @patch("services.whatnot.tasks.sync_tasks._get_db_session")
    def test_success(self, mock_db, mock_accounts, mock_client):
        from services.whatnot.tasks.sync_tasks import periodic_product_sync

        mock_db.return_value = (MagicMock(), MagicMock())
        cred = _make_mock_credential()
        mock_accounts.return_value = [cred]
        mock_client.return_value = MagicMock()

        with patch("services.whatnot.tasks.sync_tasks.ProductService") as MockSvc:
            mock_svc = MagicMock()
            mock_svc.pull_products.return_value = {"created": 3, "updated": 1, "total": 4}
            MockSvc.return_value = mock_svc

            result = periodic_product_sync()

        assert result[str(cred.account_id)]["total"] == 4


class TestPeriodicLivestreamSync:
    @patch("services.whatnot.tasks.sync_tasks._get_client_for_account")
    @patch("services.whatnot.tasks.sync_tasks._get_active_accounts")
    @patch("services.whatnot.tasks.sync_tasks._get_db_session")
    def test_success(self, mock_db, mock_accounts, mock_client):
        from services.whatnot.tasks.sync_tasks import periodic_livestream_sync

        mock_db.return_value = (MagicMock(), MagicMock())
        cred = _make_mock_credential()
        mock_accounts.return_value = [cred]
        mock_client.return_value = MagicMock()

        with patch("services.whatnot.tasks.sync_tasks.LivestreamService") as MockSvc:
            mock_svc = MagicMock()
            mock_svc.pull_livestreams.return_value = {"synced": 2}
            MockSvc.return_value = mock_svc

            result = periodic_livestream_sync()

        assert result[str(cred.account_id)] == {"synced": 2}


class TestFullSync:
    @patch("services.whatnot.tasks.sync_tasks._get_client_for_account")
    @patch("services.whatnot.tasks.sync_tasks._get_db_session")
    def test_success(self, mock_db, mock_client):
        from services.whatnot.tasks.sync_tasks import full_sync

        mock_session = MagicMock()
        mock_engine = MagicMock()
        mock_db.return_value = (mock_session, mock_engine)
        mock_client.return_value = MagicMock()

        # Mock credential lookup for last_sync_at update
        mock_cred = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_cred

        with (
            patch("services.whatnot.tasks.sync_tasks.ProductService") as MockProduct,
            patch("services.whatnot.tasks.sync_tasks.OrderSyncService") as MockOrder,
            patch("services.whatnot.tasks.sync_tasks.LivestreamService") as MockLive,
        ):
            MockProduct.return_value.pull_products.return_value = {"total": 5}
            MockOrder.return_value.pull_orders.return_value = {"synced": 3}
            MockLive.return_value.pull_livestreams.return_value = {"synced": 1}

            aid = "00000000-0000-0000-0000-000000000001"
            result = full_sync(aid)

        assert result["products"]["total"] == 5
        assert result["orders"]["synced"] == 3
        assert result["livestreams"]["synced"] == 1
        mock_session.commit.assert_called()

    @patch("services.whatnot.tasks.sync_tasks._get_client_for_account")
    @patch("services.whatnot.tasks.sync_tasks._get_db_session")
    def test_partial_failure(self, mock_db, mock_client):
        from services.whatnot.tasks.sync_tasks import full_sync

        mock_session = MagicMock()
        mock_db.return_value = (mock_session, MagicMock())
        mock_client.return_value = MagicMock()

        mock_session.execute.return_value.scalar_one_or_none.return_value = MagicMock()

        with (
            patch("services.whatnot.tasks.sync_tasks.ProductService") as MockProduct,
            patch("services.whatnot.tasks.sync_tasks.OrderSyncService") as MockOrder,
            patch("services.whatnot.tasks.sync_tasks.LivestreamService") as MockLive,
        ):
            MockProduct.return_value.pull_products.side_effect = Exception("product fail")
            MockOrder.return_value.pull_orders.return_value = {"synced": 3}
            MockLive.return_value.pull_livestreams.return_value = {"synced": 1}

            aid = "00000000-0000-0000-0000-000000000001"
            result = full_sync(aid)

        assert "error" in result["products"]
        assert result["orders"]["synced"] == 3
        assert result["livestreams"]["synced"] == 1
