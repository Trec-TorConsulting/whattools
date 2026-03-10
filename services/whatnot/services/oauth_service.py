"""OAuth 2.0 service for Whatnot integration — token exchange, refresh, encryption."""

import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from services.shared.logging import get_logger
from services.whatnot.models import WhatnotCredential
from services.whatnot.repositories.whatnot_repository import WhatnotCredentialRepository

logger = get_logger("whatnot.oauth")

WHATNOT_AUTH_BASE = os.environ.get(
    "WHATNOT_AUTH_BASE", "https://api.whatnot.com"
)
WHATNOT_AUTHORIZE_PATH = "/seller-api/rest/oauth/authorize"
WHATNOT_TOKEN_PATH = "/seller-api/rest/oauth/token"

DEFAULT_SCOPES = "read:inventory write:inventory read:orders write:orders read:customers"


def _get_fernet() -> Fernet:
    """Get a Fernet instance using the configured encryption key."""
    key = os.environ.get("WHATNOT_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("WHATNOT_ENCRYPTION_KEY environment variable is required")
    return Fernet(key.encode())


class OAuthServiceError(Exception):
    """Error during OAuth operations."""

    def __init__(self, message: str, code: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class OAuthService:
    """Manages Whatnot OAuth 2.0 Authorization Code flow."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self._fernet = _get_fernet()

    def get_authorize_url(self, account_id: uuid.UUID, redirect_uri: str) -> dict[str, str]:
        """Build the Whatnot OAuth authorization URL.

        Args:
            account_id: The WhatTools account initiating the connection.
            redirect_uri: The callback URL after authorization.

        Returns:
            Dict with 'url' and 'state' for CSRF validation.
        """
        client_id = os.environ.get("WHATNOT_CLIENT_ID", "")
        if not client_id:
            raise OAuthServiceError("Whatnot client ID not configured", "configuration_error", 500)

        state = secrets.token_urlsafe(32)
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state,
            "scope": DEFAULT_SCOPES,
        }
        url = f"{WHATNOT_AUTH_BASE}{WHATNOT_AUTHORIZE_PATH}?{urlencode(params)}"
        return {"url": url, "state": state}

    def exchange_code(
        self,
        code: str,
        redirect_uri: str,
        account_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Exchange an authorization code for access and refresh tokens.

        Args:
            code: The authorization code from the callback.
            redirect_uri: The same redirect URI used in the authorize request.
            account_id: The WhatTools account to associate credentials with.

        Returns:
            Dict with connection status info.

        Raises:
            OAuthServiceError: On token exchange failure.
        """
        client_id = os.environ.get("WHATNOT_CLIENT_ID", "")
        client_secret = os.environ.get("WHATNOT_CLIENT_SECRET", "")

        token_url = f"{WHATNOT_AUTH_BASE}{WHATNOT_TOKEN_PATH}"

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    token_url,
                    headers={"Authorization": f"Bearer {client_secret}"},
                    json={
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": redirect_uri,
                        "client_id": client_id,
                    },
                )
        except httpx.HTTPError as exc:
            logger.error("oauth_token_exchange_error", error=str(exc))
            raise OAuthServiceError(
                "Failed to connect to Whatnot", "oauth_error", 502
            ) from exc

        if response.status_code != 200:
            logger.warning(
                "oauth_token_exchange_failed",
                status=response.status_code,
                body=response.text[:500],
            )
            raise OAuthServiceError(
                "Failed to exchange authorization code", "oauth_error", 400
            )

        token_data = response.json()
        access_token = token_data["access_token"]
        refresh_token = token_data["refresh_token"]
        expires_in = token_data.get("expires_in", 86400)

        # Fetch user info from Whatnot
        from services.whatnot.graphql.client import WhatnotClient
        from services.whatnot.graphql.queries import ME_QUERY

        whatnot_client = WhatnotClient(access_token)
        me_data = whatnot_client.execute(ME_QUERY)
        me = me_data.get("me", {})

        # Encrypt and store tokens
        repo = WhatnotCredentialRepository(self.db, account_id)
        existing = repo.get_credential()

        encrypted_access = self._fernet.encrypt(access_token.encode()).decode()
        encrypted_refresh = self._fernet.encrypt(refresh_token.encode()).decode()
        token_expires = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        webhook_secret = secrets.token_urlsafe(32)

        if existing:
            existing.encrypted_access_token = encrypted_access
            existing.encrypted_refresh_token = encrypted_refresh
            existing.token_expires_at = token_expires
            existing.whatnot_user_id = me.get("id", "")
            existing.whatnot_username = me.get("username", "")
            existing.scopes = DEFAULT_SCOPES
            existing.is_active = True
            existing.webhook_secret = webhook_secret
            existing.updated_at = datetime.now(timezone.utc)
            self.db.flush()
        else:
            credential = WhatnotCredential(
                account_id=account_id,
                whatnot_user_id=me.get("id", ""),
                whatnot_username=me.get("username", ""),
                encrypted_access_token=encrypted_access,
                encrypted_refresh_token=encrypted_refresh,
                token_expires_at=token_expires,
                scopes=DEFAULT_SCOPES,
                is_active=True,
                webhook_secret=webhook_secret,
            )
            self.db.add(credential)
            self.db.flush()

        self.db.commit()

        return {
            "connected": True,
            "whatnot_username": me.get("username", ""),
            "whatnot_user_id": me.get("id", ""),
            "scopes": DEFAULT_SCOPES.split(" "),
        }

    def refresh_tokens(self, account_id: uuid.UUID) -> str:
        """Refresh the access token using the stored refresh token.

        Args:
            account_id: The WhatTools account whose tokens to refresh.

        Returns:
            The new decrypted access token.

        Raises:
            OAuthServiceError: If no credentials exist or refresh fails.
        """
        repo = WhatnotCredentialRepository(self.db, account_id)
        credential = repo.get_credential()
        if not credential or not credential.is_active:
            raise OAuthServiceError(
                "Whatnot account not connected", "not_connected", 400
            )

        refresh_token = self._fernet.decrypt(
            credential.encrypted_refresh_token.encode()
        ).decode()
        client_secret = os.environ.get("WHATNOT_CLIENT_SECRET", "")

        token_url = f"{WHATNOT_AUTH_BASE}{WHATNOT_TOKEN_PATH}"

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    token_url,
                    headers={"Authorization": f"Bearer {client_secret}"},
                    json={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                    },
                )
        except httpx.HTTPError as exc:
            logger.error("oauth_refresh_error", error=str(exc))
            raise OAuthServiceError(
                "Failed to refresh Whatnot tokens", "oauth_error", 502
            ) from exc

        if response.status_code != 200:
            # Refresh token may be expired — disconnect
            credential.is_active = False
            credential.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            raise OAuthServiceError(
                "Whatnot refresh token expired. Please reconnect.", "token_expired", 401
            )

        token_data = response.json()
        new_access = token_data["access_token"]
        new_refresh = token_data.get("refresh_token", refresh_token)
        expires_in = token_data.get("expires_in", 86400)

        credential.encrypted_access_token = self._fernet.encrypt(new_access.encode()).decode()
        credential.encrypted_refresh_token = self._fernet.encrypt(new_refresh.encode()).decode()
        credential.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        credential.updated_at = datetime.now(timezone.utc)
        self.db.commit()

        return new_access

    def get_access_token(self, account_id: uuid.UUID) -> str:
        """Get a valid access token, refreshing if needed.

        Args:
            account_id: The WhatTools account.

        Returns:
            Decrypted access token string.
        """
        repo = WhatnotCredentialRepository(self.db, account_id)
        credential = repo.get_credential()
        if not credential or not credential.is_active:
            raise OAuthServiceError(
                "Whatnot account not connected", "not_connected", 400
            )

        # Check if token needs refresh (refresh 5 minutes early)
        if credential.token_expires_at:
            if datetime.now(timezone.utc) >= credential.token_expires_at - timedelta(minutes=5):
                return self.refresh_tokens(account_id)

        return self._fernet.decrypt(
            credential.encrypted_access_token.encode()
        ).decode()

    def get_status(self, account_id: uuid.UUID) -> dict[str, Any]:
        """Get the current Whatnot connection status.

        Args:
            account_id: The WhatTools account.

        Returns:
            Dict with connection status, username, scopes, last sync time.
        """
        repo = WhatnotCredentialRepository(self.db, account_id)
        credential = repo.get_credential()

        if not credential or not credential.is_active:
            return {"connected": False}

        return {
            "connected": True,
            "whatnot_username": credential.whatnot_username,
            "whatnot_user_id": credential.whatnot_user_id,
            "scopes": credential.scopes.split(" ") if credential.scopes else [],
            "last_sync_at": credential.last_sync_at.isoformat() if credential.last_sync_at else None,
        }

    def disconnect(self, account_id: uuid.UUID) -> None:
        """Disconnect the Whatnot account by deactivating and clearing tokens.

        Args:
            account_id: The WhatTools account to disconnect.
        """
        repo = WhatnotCredentialRepository(self.db, account_id)
        credential = repo.get_credential()
        if not credential:
            return

        credential.is_active = False
        credential.encrypted_access_token = ""
        credential.encrypted_refresh_token = ""
        credential.token_expires_at = None
        credential.updated_at = datetime.now(timezone.utc)
        self.db.commit()
