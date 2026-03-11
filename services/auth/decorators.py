"""Platform admin authorization decorator."""

from functools import wraps
from typing import Any

from flask import request
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request

from services.shared.errors import error_response


def require_platform_admin(fn: Any) -> Any:
    """Require the current user to be a platform admin.

    Checks the JWT claim `is_platform_admin` and rejects with 403 if not set.
    Must be used on routes that already require JWT auth.
    """

    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        verify_jwt_in_request()
        claims = get_jwt()
        if not claims.get("is_platform_admin"):
            return error_response("forbidden", "Platform admin access required.", status_code=403)
        return fn(*args, **kwargs)

    return wrapper
