"""Whatnot Seller API GraphQL client with rate limiting and error handling."""

import os
import time
import threading
from typing import Any

import httpx

from services.shared.logging import get_logger

logger = get_logger("whatnot.graphql")

WHATNOT_API_URL = os.environ.get(
    "WHATNOT_API_URL", "https://api.whatnot.com/seller-api/graphql"
)
WHATNOT_STAGING_API_URL = "https://api.stage.whatnot.com/seller-api/graphql"

# Rate limit: 10 requests per second
RATE_LIMIT = 10
RATE_WINDOW = 1.0  # seconds


class WhatnotApiError(Exception):
    """Error from the Whatnot GraphQL API."""

    def __init__(self, message: str, errors: list[dict[str, Any]] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.errors = errors or []


class WhatnotUserError(Exception):
    """Business logic error returned in userErrors from a Whatnot mutation."""

    def __init__(self, message: str, field: str | None = None, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.field = field
        self.code = code


class RateLimiter:
    """Thread-safe token bucket rate limiter."""

    def __init__(self, max_requests: int = RATE_LIMIT, window: float = RATE_WINDOW) -> None:
        self._max = max_requests
        self._window = window
        self._timestamps: list[float] = []
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """Block until a request slot is available."""
        while True:
            with self._lock:
                now = time.monotonic()
                # Remove timestamps outside the window
                self._timestamps = [t for t in self._timestamps if now - t < self._window]
                if len(self._timestamps) < self._max:
                    self._timestamps.append(now)
                    return
                # Calculate wait time
                earliest = self._timestamps[0]
                wait = self._window - (now - earliest)
            if wait > 0:
                time.sleep(wait)


class WhatnotClient:
    """HTTP client for the Whatnot Seller GraphQL API.

    Handles authentication, rate limiting, and error extraction.
    """

    def __init__(self, access_token: str, *, staging: bool = False) -> None:
        self._access_token = access_token
        self._base_url = WHATNOT_STAGING_API_URL if staging else WHATNOT_API_URL
        self._rate_limiter = RateLimiter()

    def execute(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        *,
        files: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a GraphQL query or mutation.

        Args:
            query: GraphQL query/mutation string.
            variables: GraphQL variables dict.
            files: File uploads for multipart requests.

        Returns:
            The 'data' portion of the GraphQL response.

        Raises:
            WhatnotApiError: On transport or GraphQL errors.
            WhatnotUserError: On business logic userErrors.
        """
        self._rate_limiter.acquire()

        headers = {
            "Authorization": f"Bearer {self._access_token}",
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                if files:
                    # Multipart upload (for media)
                    operations = {"query": query}
                    if variables:
                        operations["variables"] = variables
                    response = client.post(
                        self._base_url,
                        headers=headers,
                        data={"operations": _json_dumps(operations)},
                        files=files,
                    )
                else:
                    payload: dict[str, Any] = {"query": query}
                    if variables:
                        payload["variables"] = variables
                    response = client.post(
                        self._base_url,
                        headers=headers,
                        json=payload,
                    )

            if response.status_code == 429:
                raise WhatnotApiError("Rate limited by Whatnot API")
            if response.status_code >= 500:
                raise WhatnotApiError(f"Whatnot API server error: {response.status_code}")

            body = response.json()

        except httpx.HTTPError as exc:
            logger.error("whatnot_api_transport_error", error=str(exc))
            raise WhatnotApiError(f"Transport error: {exc}") from exc

        # Check for GraphQL-level errors
        if "errors" in body and body["errors"]:
            error_messages = [e.get("message", "Unknown error") for e in body["errors"]]
            logger.warning("whatnot_graphql_errors", errors=error_messages)
            raise WhatnotApiError(
                "; ".join(error_messages), errors=body["errors"]
            )

        data = body.get("data")
        if data is None:
            raise WhatnotApiError("No data in GraphQL response")

        return data

    def execute_mutation(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        *,
        mutation_name: str,
        files: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a GraphQL mutation and check for userErrors.

        Args:
            query: GraphQL mutation string.
            variables: GraphQL variables dict.
            mutation_name: Key in the response data containing the mutation result.
            files: File uploads for multipart requests.

        Returns:
            The mutation result dict.

        Raises:
            WhatnotUserError: If userErrors are present.
            WhatnotApiError: On transport or GraphQL errors.
        """
        data = self.execute(query, variables, files=files)
        result = data.get(mutation_name, {})

        user_errors = result.get("userErrors", [])
        if user_errors:
            first = user_errors[0]
            raise WhatnotUserError(
                message=first.get("message", "Unknown error"),
                field=first.get("field"),
                code=first.get("code"),
            )

        return result


def _json_dumps(obj: Any) -> str:
    """JSON serialize for multipart form data."""
    import json
    return json.dumps(obj, default=str)
