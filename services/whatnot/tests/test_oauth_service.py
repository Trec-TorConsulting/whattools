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

    @patch("services.whatnot.services.oauth_service.httpx.Client")
    def test_exchange_code_success(self, mock_client_class, db_session, sample_account, monkeypatch):
        monkeypatch.setenv("WHATNOT_CLIENT_ID", "test_client_id")
        monkeypatch.setenv("WHATNOT_CLIENT_SECRET", "test_client_secret")

        # Mock token response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 86400,
        }
        mock_http = MagicMock()
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)
        mock_http.post.return_value = mock_response
        mock_client_class.return_value = mock_http

        # Mock WhatnotClient.execute for ME_QUERY
        with patch("services.whatnot.graphql.client.WhatnotClient") as MockWnClient:
            mock_wn = MagicMock()
            mock_wn.execute.return_value = {"me": {"id": "wn_123", "username": "seller1"}}
            MockWnClient.return_value = mock_wn

            svc = OAuthService(db_session)
            result = svc.exchange_code("auth_code_123", "http://localhost:3000/callback", sample_account.id)

        assert result["connected"] is True
        assert result["whatnot_username"] == "seller1"
        assert result["whatnot_user_id"] == "wn_123"

    @patch("services.whatnot.services.oauth_service.httpx.Client")
    def test_exchange_code_http_error(self, mock_client_class, db_session, sample_account, monkeypatch):
        """Token exchange fails with HTTP error."""
        import httpx as real_httpx

        monkeypatch.setenv("WHATNOT_CLIENT_ID", "test_client_id")
        monkeypatch.setenv("WHATNOT_CLIENT_SECRET", "test_client_secret")

        mock_http = MagicMock()
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)
        mock_http.post.side_effect = real_httpx.ConnectError("connection refused")
        mock_client_class.return_value = mock_http

        svc = OAuthService(db_session)
        with pytest.raises(OAuthServiceError, match="Failed to connect"):
            svc.exchange_code("auth_code", "http://localhost:3000/callback", sample_account.id)

    @patch("services.whatnot.services.oauth_service.httpx.Client")
    def test_exchange_code_non_200(self, mock_client_class, db_session, sample_account, monkeypatch):
        """Token exchange returns non-200 status."""
        monkeypatch.setenv("WHATNOT_CLIENT_ID", "test_client_id")
        monkeypatch.setenv("WHATNOT_CLIENT_SECRET", "test_client_secret")

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"

        mock_http = MagicMock()
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)
        mock_http.post.return_value = mock_response
        mock_client_class.return_value = mock_http

        svc = OAuthService(db_session)
        with pytest.raises(OAuthServiceError, match="Failed to exchange"):
            svc.exchange_code("bad_code", "http://localhost:3000/callback", sample_account.id)

    @patch("services.whatnot.services.oauth_service.httpx.Client")
    def test_refresh_tokens_success(self, mock_client_class, db_session, sample_account, sample_credential):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "refreshed_access",
            "refresh_token": "refreshed_refresh",
            "expires_in": 86400,
        }
        mock_http = MagicMock()
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)
        mock_http.post.return_value = mock_response
        mock_client_class.return_value = mock_http

        svc = OAuthService(db_session)
        # Need real encrypted tokens for decryption to work
        from cryptography.fernet import Fernet

        fernet = Fernet(TEST_ENCRYPTION_KEY.encode())
        sample_credential.encrypted_refresh_token = fernet.encrypt(b"old_refresh").decode()
        db_session.flush()

        result = svc.refresh_tokens(sample_account.id)
        assert result == "refreshed_access"

    @patch("services.whatnot.services.oauth_service.httpx.Client")
    def test_refresh_tokens_expired_deactivates(self, mock_client_class, db_session, sample_account, sample_credential):
        """Refresh failure deactivates the credential."""
        mock_response = MagicMock()
        mock_response.status_code = 401

        mock_http = MagicMock()
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)
        mock_http.post.return_value = mock_response
        mock_client_class.return_value = mock_http

        from cryptography.fernet import Fernet

        fernet = Fernet(TEST_ENCRYPTION_KEY.encode())
        sample_credential.encrypted_refresh_token = fernet.encrypt(b"old_refresh").decode()
        db_session.flush()

        svc = OAuthService(db_session)
        with pytest.raises(OAuthServiceError, match="expired"):
            svc.refresh_tokens(sample_account.id)

        # Credential should now be deactivated
        assert sample_credential.is_active is False

    def test_refresh_tokens_not_connected(self, db_session, sample_account):
        svc = OAuthService(db_session)
        with pytest.raises(OAuthServiceError, match="not connected"):
            svc.refresh_tokens(sample_account.id)

    def test_get_access_token_valid(self, db_session, sample_account, sample_credential):
        """Token is still valid — return decrypted without refresh."""
        from cryptography.fernet import Fernet
        from datetime import timedelta

        fernet = Fernet(TEST_ENCRYPTION_KEY.encode())
        sample_credential.encrypted_access_token = fernet.encrypt(b"my_access_token").decode()
        sample_credential.token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        db_session.flush()

        svc = OAuthService(db_session)
        result = svc.get_access_token(sample_account.id)
        assert result == "my_access_token"

    @patch("services.whatnot.services.oauth_service.httpx.Client")
    def test_get_access_token_near_expiry_refreshes(self, mock_client_class, db_session, sample_account, sample_credential):
        """Token expires in < 5 minutes — should trigger refresh."""
        from cryptography.fernet import Fernet

        fernet = Fernet(TEST_ENCRYPTION_KEY.encode())
        sample_credential.encrypted_access_token = fernet.encrypt(b"old_token").decode()
        sample_credential.encrypted_refresh_token = fernet.encrypt(b"old_refresh").decode()
        sample_credential.token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=2)
        db_session.flush()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_refreshed_token",
            "expires_in": 86400,
        }
        mock_http = MagicMock()
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)
        mock_http.post.return_value = mock_response
        mock_client_class.return_value = mock_http

        svc = OAuthService(db_session)
        result = svc.get_access_token(sample_account.id)
        assert result == "new_refreshed_token"

    def test_get_access_token_not_connected(self, db_session, sample_account):
        svc = OAuthService(db_session)
        with pytest.raises(OAuthServiceError, match="not connected"):
            svc.get_access_token(sample_account.id)
