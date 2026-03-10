"""Webhook routes — Whatnot webhook ingestion endpoint."""

from flask import Blueprint, request

from services.shared.database import get_db
from services.shared.errors import error_response, success_response
from services.whatnot.services.webhook_handler import WebhookHandler, WebhookServiceError

webhook_bp = Blueprint("whatnot_webhooks", __name__)


@webhook_bp.route("", methods=["POST"])
def receive_webhook():  # type: ignore[no-untyped-def]
    """Receive and process Whatnot webhook events.

    No JWT required — authenticated via HMAC signature.
    """
    signature = request.headers.get("X-Whatnot-Webhook-Signature", "")
    seller_id = request.headers.get("X-Whatnot-Seller-Id", "")

    if not signature or not seller_id:
        return error_response(
            "webhook_auth_failed",
            "Missing required webhook headers",
            status_code=401,
        )

    payload_bytes = request.get_data()
    payload = request.get_json(force=True)

    db = get_db()
    handler = WebhookHandler(db)

    # Validate HMAC signature and get account_id
    try:
        account_id = handler.validate_signature(payload_bytes, signature, seller_id)
    except WebhookServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    # Generate event ID for idempotency (from headers or payload)
    event_id = request.headers.get("X-Whatnot-Webhook-Id") or f"{seller_id}:{hash(payload_bytes)}"
    topic = request.headers.get("X-Whatnot-Webhook-Topic", payload.get("topic", "unknown"))

    result = handler.handle_event(account_id, event_id, topic, payload)
    return success_response(result)
