"""Stripe billing service — checkout, subscription management, webhook handling."""

import os
import uuid
from datetime import datetime, timezone
from typing import Any

import stripe
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.auth.models.models import Account, PlanTier
from services.shared.logging import get_logger

logger = get_logger("auth.billing")

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")

FREE_ITEM_LIMIT = 50
FREE_MEMBER_LIMIT = 2
PAID_PRICE_ID = os.environ.get("STRIPE_PAID_PRICE_ID", "")


class BillingServiceError(Exception):
    """Error during billing operations."""

    def __init__(self, message: str, code: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class BillingService:
    """Manages Stripe subscriptions, checkout, and portal sessions."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_checkout_session(
        self,
        account_id: uuid.UUID,
        user_email: str,
        success_url: str,
        cancel_url: str,
    ) -> dict[str, str]:
        """Create a Stripe Checkout session for upgrading to paid plan.

        Args:
            account_id: The WhatTools account.
            user_email: Email for the Stripe customer.
            success_url: URL to redirect on success.
            cancel_url: URL to redirect on cancellation.

        Returns:
            Dict with 'url' for the Stripe Checkout page.
        """
        account = self._get_account(account_id)

        if account.plan_tier == PlanTier.PAID:
            raise BillingServiceError("Account already on paid plan", "already_paid", 409)

        # Get or create Stripe customer
        customer_id = self._get_or_create_customer(account, user_email)

        try:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                mode="subscription",
                line_items=[{"price": PAID_PRICE_ID, "quantity": 1}],
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={"account_id": str(account_id)},
            )
        except stripe.StripeError as exc:
            logger.error("stripe_checkout_error", error=str(exc))
            raise BillingServiceError(
                "Failed to create checkout session", "stripe_error", 502
            ) from exc

        return {"url": session.url}

    def create_portal_session(
        self,
        account_id: uuid.UUID,
        return_url: str,
    ) -> dict[str, str]:
        """Create a Stripe Customer Portal session.

        Args:
            account_id: The WhatTools account.
            return_url: URL to redirect when the user leaves the portal.

        Returns:
            Dict with 'url' for the portal.
        """
        account = self._get_account(account_id)

        if not account.stripe_customer_id:
            raise BillingServiceError("No billing account found", "no_customer", 400)

        try:
            session = stripe.billing_portal.Session.create(
                customer=account.stripe_customer_id,
                return_url=return_url,
            )
        except stripe.StripeError as exc:
            logger.error("stripe_portal_error", error=str(exc))
            raise BillingServiceError(
                "Failed to create portal session", "stripe_error", 502
            ) from exc

        return {"url": session.url}

    def get_subscription_status(self, account_id: uuid.UUID) -> dict[str, Any]:
        """Get the current subscription status for an account.

        Args:
            account_id: The WhatTools account.

        Returns:
            Dict with plan details, limits, and usage.
        """
        account = self._get_account(account_id)

        return {
            "plan_tier": account.plan_tier,
            "subscription_status": account.subscription_status or "none",
            "stripe_customer_id": account.stripe_customer_id,
            "inventory_item_limit": account.inventory_item_limit,
            "team_member_limit": account.team_member_limit,
        }

    def handle_webhook(self, payload: bytes, sig_header: str) -> dict[str, Any]:
        """Process a Stripe webhook event.

        Args:
            payload: Raw request body bytes.
            sig_header: Stripe-Signature header value.

        Returns:
            Dict with the processing result.
        """
        webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except stripe.SignatureVerificationError as exc:
            raise BillingServiceError(
                "Invalid Stripe signature", "webhook_auth_failed", 401
            ) from exc

        event_type = event["type"]
        data = event["data"]["object"]

        handlers = {
            "checkout.session.completed": self._handle_checkout_completed,
            "customer.subscription.updated": self._handle_subscription_updated,
            "customer.subscription.deleted": self._handle_subscription_deleted,
        }

        handler = handlers.get(event_type)
        if handler:
            handler(data)
            self.db.commit()
            return {"handled": True, "event_type": event_type}

        return {"handled": False, "event_type": event_type}

    def _handle_checkout_completed(self, session: dict[str, Any]) -> None:
        """Upgrade account to paid after successful checkout."""
        account_id_str = session.get("metadata", {}).get("account_id")
        if not account_id_str:
            logger.warning("checkout_no_account_id")
            return

        account = self._get_account(uuid.UUID(account_id_str))
        account.plan_tier = PlanTier.PAID
        account.subscription_status = "active"
        if session.get("customer"):
            account.stripe_customer_id = session["customer"]
        account.updated_at = datetime.now(timezone.utc)
        self.db.flush()
        logger.info("account_upgraded", account_id=account_id_str)

    def _handle_subscription_updated(self, subscription: dict[str, Any]) -> None:
        """Update subscription status on change."""
        customer_id = subscription.get("customer")
        status = subscription.get("status")

        query = (
            select(Account)
            .where(Account.stripe_customer_id == customer_id)
            .where(Account.deleted_at.is_(None))
        )
        account = self.db.execute(query).scalar_one_or_none()
        if not account:
            logger.warning("subscription_update_no_account", customer_id=customer_id)
            return

        account.subscription_status = status
        if status in ("active", "trialing"):
            account.plan_tier = PlanTier.PAID
        account.updated_at = datetime.now(timezone.utc)
        self.db.flush()

    def _handle_subscription_deleted(self, subscription: dict[str, Any]) -> None:
        """Downgrade account when subscription is cancelled."""
        customer_id = subscription.get("customer")

        query = (
            select(Account)
            .where(Account.stripe_customer_id == customer_id)
            .where(Account.deleted_at.is_(None))
        )
        account = self.db.execute(query).scalar_one_or_none()
        if not account:
            return

        account.plan_tier = PlanTier.FREE
        account.subscription_status = "cancelled"
        account.updated_at = datetime.now(timezone.utc)
        self.db.flush()
        logger.info("account_downgraded", account_id=str(account.id))

    def _get_account(self, account_id: uuid.UUID) -> Account:
        """Fetch an account by ID or raise error."""
        query = (
            select(Account)
            .where(Account.id == account_id)
            .where(Account.deleted_at.is_(None))
        )
        account = self.db.execute(query).scalar_one_or_none()
        if not account:
            raise BillingServiceError("Account not found", "not_found", 404)
        return account

    def _get_or_create_customer(self, account: Account, email: str) -> str:
        """Get existing or create new Stripe customer."""
        if account.stripe_customer_id:
            return account.stripe_customer_id

        try:
            customer = stripe.Customer.create(
                email=email,
                name=account.name,
                metadata={"account_id": str(account.id)},
            )
        except stripe.StripeError as exc:
            raise BillingServiceError(
                "Failed to create Stripe customer", "stripe_error", 502
            ) from exc

        account.stripe_customer_id = customer.id
        account.updated_at = datetime.now(timezone.utc)
        self.db.flush()
        return customer.id
