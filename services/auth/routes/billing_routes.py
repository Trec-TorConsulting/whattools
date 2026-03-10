"""Billing routes — checkout, subscription management, Stripe webhooks."""

from flask import Blueprint, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from services.auth.services.billing_service import BillingService, BillingServiceError
from services.shared.database import get_db
from services.shared.errors import error_response, success_response

billing_bp = Blueprint("billing", __name__)


def _get_billing_service() -> BillingService:
    return BillingService(get_db())


@billing_bp.route("/checkout", methods=["POST"])
@jwt_required()
def create_checkout():  # type: ignore[no-untyped-def]
    """Create a Stripe Checkout session for upgrading to paid plan."""
    claims = get_jwt()
    account_id = claims.get("account_id")
    identity = get_jwt_identity()

    body = request.get_json(force=True)
    success_url = body.get("success_url")
    cancel_url = body.get("cancel_url")

    if not success_url or not cancel_url:
        return error_response("validation_error", "success_url and cancel_url are required", status_code=400)

    svc = _get_billing_service()
    try:
        result = svc.create_checkout_session(
            account_id=account_id,
            user_email=identity,
            success_url=success_url,
            cancel_url=cancel_url,
        )
    except BillingServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@billing_bp.route("/portal", methods=["POST"])
@jwt_required()
def create_portal():  # type: ignore[no-untyped-def]
    """Create a Stripe Customer Portal session."""
    claims = get_jwt()
    account_id = claims.get("account_id")

    body = request.get_json(force=True)
    return_url = body.get("return_url")
    if not return_url:
        return error_response("validation_error", "return_url is required", status_code=400)

    svc = _get_billing_service()
    try:
        result = svc.create_portal_session(account_id=account_id, return_url=return_url)
    except BillingServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@billing_bp.route("/subscription", methods=["GET"])
@jwt_required()
def get_subscription():  # type: ignore[no-untyped-def]
    """Get the current subscription status."""
    claims = get_jwt()
    account_id = claims.get("account_id")

    svc = _get_billing_service()
    try:
        result = svc.get_subscription_status(account_id=account_id)
    except BillingServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)


@billing_bp.route("/webhook", methods=["POST"])
def stripe_webhook():  # type: ignore[no-untyped-def]
    """Handle Stripe webhook events. No JWT — authenticated via Stripe signature."""
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")

    svc = _get_billing_service()
    try:
        result = svc.handle_webhook(payload=payload, sig_header=sig_header)
    except BillingServiceError as e:
        return error_response(e.code, e.message, status_code=e.status_code)

    return success_response(result)
