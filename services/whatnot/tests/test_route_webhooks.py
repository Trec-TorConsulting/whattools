"""Integration tests for webhook routes."""

import hashlib
import hmac
import json

import pytest
from flask import Flask

from services.shared.errors import register_error_handlers

TEST_ENCRYPTION_KEY = "I2z4QxvoJ-V-xCVM8R0gF8e0LJvQa6dKAnBUJbcvfwo="


@pytest.fixture(autouse=True)
def _set_env(monkeypatch):
    monkeypatch.setenv("WHATNOT_ENCRYPTION_KEY", TEST_ENCRYPTION_KEY)


@pytest.fixture()
def webhook_app(db_session):
    from services.whatnot.routes.webhook_routes import webhook_bp

    app = Flask("test")
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    app.config["_EVENT_PUBLISHER"] = None
    register_error_handlers(app)
    app.register_blueprint(webhook_bp, url_prefix="/api/v1/whatnot/webhooks")

    @app.before_request
    def inject_db():
        from flask import g
        g.db_session = db_session

    return app


@pytest.fixture()
def client(webhook_app):
    return webhook_app.test_client()


class TestWebhookRoutes:
    def test_missing_headers(self, client):
        resp = client.post(
            "/api/v1/whatnot/webhooks",
            data=json.dumps({"event": "test"}),
            content_type="application/json",
        )
        assert resp.status_code == 401
        data = resp.get_json()
        assert data["errors"][0]["code"] == "webhook_auth_failed"

    def test_missing_signature(self, client):
        resp = client.post(
            "/api/v1/whatnot/webhooks",
            data=json.dumps({"event": "test"}),
            content_type="application/json",
            headers={"X-Whatnot-Seller-Id": "seller_123"},
        )
        assert resp.status_code == 401

    def test_missing_seller_id(self, client):
        resp = client.post(
            "/api/v1/whatnot/webhooks",
            data=json.dumps({"event": "test"}),
            content_type="application/json",
            headers={"X-Whatnot-Webhook-Signature": "abc123"},
        )
        assert resp.status_code == 401

    def test_valid_webhook(self, client, sample_credential):
        payload = json.dumps({"product_id": "prod_1", "listing_id": "lst_1"})
        payload_bytes = payload.encode()
        secret = sample_credential.webhook_secret
        signature = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()

        resp = client.post(
            "/api/v1/whatnot/webhooks",
            data=payload,
            content_type="application/json",
            headers={
                "X-Whatnot-Webhook-Signature": signature,
                "X-Whatnot-Seller-Id": sample_credential.whatnot_user_id,
                "X-Whatnot-Webhook-Id": "evt_test_1",
                "X-Whatnot-Webhook-Topic": "listing/created",
            },
        )
        assert resp.status_code == 200

    def test_invalid_signature(self, client, sample_credential):
        payload = json.dumps({"product_id": "prod_1"})

        resp = client.post(
            "/api/v1/whatnot/webhooks",
            data=payload,
            content_type="application/json",
            headers={
                "X-Whatnot-Webhook-Signature": "invalid_sig",
                "X-Whatnot-Seller-Id": sample_credential.whatnot_user_id,
                "X-Whatnot-Webhook-Id": "evt_test_2",
                "X-Whatnot-Webhook-Topic": "listing/created",
            },
        )
        assert resp.status_code == 401

    def test_unknown_seller_id(self, client):
        payload = json.dumps({"product_id": "prod_1"})
        signature = hmac.new(b"some_secret", payload.encode(), hashlib.sha256).hexdigest()

        resp = client.post(
            "/api/v1/whatnot/webhooks",
            data=payload,
            content_type="application/json",
            headers={
                "X-Whatnot-Webhook-Signature": signature,
                "X-Whatnot-Seller-Id": "unknown_seller",
                "X-Whatnot-Webhook-Id": "evt_test_3",
                "X-Whatnot-Webhook-Topic": "listing/created",
            },
        )
        assert resp.status_code == 401

    def test_duplicate_event_idempotency(self, client, sample_credential):
        payload = json.dumps({"product_id": "prod_1", "listing_id": "lst_1"})
        payload_bytes = payload.encode()
        secret = sample_credential.webhook_secret
        signature = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()

        headers = {
            "X-Whatnot-Webhook-Signature": signature,
            "X-Whatnot-Seller-Id": sample_credential.whatnot_user_id,
            "X-Whatnot-Webhook-Id": "evt_duplicate_1",
            "X-Whatnot-Webhook-Topic": "listing/created",
        }

        # First call
        resp1 = client.post(
            "/api/v1/whatnot/webhooks",
            data=payload,
            content_type="application/json",
            headers=headers,
        )
        assert resp1.status_code == 200

        # Second call with same event ID — should still succeed (idempotent)
        resp2 = client.post(
            "/api/v1/whatnot/webhooks",
            data=payload,
            content_type="application/json",
            headers=headers,
        )
        assert resp2.status_code == 200
