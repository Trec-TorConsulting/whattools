"""Tests for OAuth service."""

import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from services.whatnot.services.oauth_service import OAuthService, OAuthServiceError

TEST_ENCRYPTION_KEY = "I2z4QxvoJ-V-xCVM8R0gF8e0LJvQa6dKAnBUJbcvfwo="


@pytest.fixture(autouse=True)
def _set_encryption_key(monkeypatch):
    monkeypatch.setenv("WHATNOT_ENCRYPTION_KEY", TEST_ENCRYPTION_KEY)


class TestOAuthService:
    def test_get_authorize_url(self, db_session, sample_account, monkeypatch):
        monkeypatch.setenv("WHATNOT_CLIENT_ID", "test_client_id")
        monkeypatch.setenv("WHATNOT_CLIENT_SECRET", "test_client_secret")

        svc = OAuthService(db_session)
        result = svc.get_authorize_url(
            sample_account.id, "http://localhost:3000/whatnot/callback"
        )

        assert "url" in result
        assert "state" in result
        assert "test_client_id" in result["url"]

    def test_get_status_not_connected(self, db_session, sample_account):
        svc = OAuthService(db_session)
        result = svc.get_status(sample_account.id)

        assert result["connected"] is False

    def test_get_status_connected(self, db_session, sample_account, sample_credential):
        svc = OAuthService(db_session)
        result = svc.get_status(sample_account.id)

        assert result["connected"] is True
        assert result["whatnot_username"] == "testuser"

    def test_disconnect(self, db_session, sample_account, sample_credential):
        svc = OAuthService(db_session)
        svc.disconnect(sample_account.id)
        db_session.flush()

        result = svc.get_status(sample_account.id)
        assert result["connected"] is False

    def test_disconnect_not_connected(self, db_session, sample_account):
        svc = OAuthService(db_session)
        # disconnect is a no-op when not connected (no error raised)
        svc.disconnect(sample_account.id)
