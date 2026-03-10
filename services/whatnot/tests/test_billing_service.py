"""Tests for billing service."""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from services.auth.models.models import Account, PlanTier
from services.auth.services.billing_service import BillingService, BillingServiceError


class TestBillingService:
    def test_get_subscription_status_free(self, db_session, sample_account):
        svc = BillingService(db_session)
        result = svc.get_subscription_status(sample_account.id)

        assert result["plan_tier"] == PlanTier.FREE
        assert result["inventory_item_limit"] == 50
        assert result["team_member_limit"] == 2

    def test_get_subscription_not_found(self, db_session):
        svc = BillingService(db_session)
        fake_id = uuid.uuid4()

        with pytest.raises(BillingServiceError, match="Account not found"):
            svc.get_subscription_status(fake_id)

    @patch("services.auth.services.billing_service.stripe")
    def test_create_checkout_already_paid(self, mock_stripe, db_session, sample_account):
        sample_account.plan_tier = PlanTier.PAID
        db_session.flush()

        svc = BillingService(db_session)
        with pytest.raises(BillingServiceError, match="already on paid plan"):
            svc.create_checkout_session(
                sample_account.id, "test@test.com",
                "http://localhost/success", "http://localhost/cancel",
            )

    @patch("services.auth.services.billing_service.stripe")
    def test_create_portal_no_customer(self, mock_stripe, db_session, sample_account):
        svc = BillingService(db_session)
        with pytest.raises(BillingServiceError, match="No billing account"):
            svc.create_portal_session(sample_account.id, "http://localhost/return")

    @patch("services.auth.services.billing_service.stripe")
    def test_handle_webhook_invalid_signature(self, mock_stripe, db_session):
        # Set up the mock so construct_event raises the right exception type
        sig_error_class = type("SignatureVerificationError", (Exception,), {})
        mock_stripe.SignatureVerificationError = sig_error_class
        mock_stripe.Webhook.construct_event.side_effect = sig_error_class("bad sig")

        svc = BillingService(db_session)
        with pytest.raises(BillingServiceError, match="Invalid Stripe signature"):
            svc.handle_webhook(b"payload", "bad_sig")
