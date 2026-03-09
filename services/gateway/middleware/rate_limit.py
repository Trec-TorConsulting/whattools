"""Rate limiting middleware — per-IP and per-user limits via Flask-Limiter."""

import os

from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


def init_rate_limiting(app: Flask) -> Limiter:
    """Configure and attach Flask-Limiter to the app.

    Default limits:
    - Per-IP: 60/minute (unauthenticated)
    - Per-user: 120/minute (authenticated)

    Rate limit storage uses in-memory for dev/testing and Redis for production.
    """
    storage_uri = "memory://"
    if not app.config.get("TESTING"):
        storage_uri = app.config.get("REDIS_URL", os.environ.get("REDIS_URL", "redis://localhost:6379/0"))

    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=[
            os.environ.get("RATE_LIMIT_PER_IP", "60/minute"),
        ],
        storage_uri=storage_uri,
        strategy="fixed-window",
    )
    return limiter
