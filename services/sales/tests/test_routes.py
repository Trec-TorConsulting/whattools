"""Integration tests for sales service API routes."""

import json
import uuid
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask
from sqlalchemy.orm import Session

from services.sales.routes.show_routes import shows_bp
from services.sales.routes.order_routes import orders_bp
from services.sales.tests.conftest import make_auth_headers
from services.shared.errors import register_error_handlers


@pytest.fixture()
def client(app: Flask, db_session: Session):  # type: ignore[no-untyped-def]
    """Create a test client with routes registered."""
    register_error_handlers(app)
    app.register_blueprint(shows_bp, url_prefix="/api/v1/shows")
    app.register_blueprint(orders_bp, url_prefix="/api/v1/orders")

    # Patch get_db to return our test session
    with patch("services.sales.routes.show_routes.get_db", return_value=db_session), \
         patch("services.sales.routes.order_routes.get_db", return_value=db_session):
        yield app.test_client()


class TestShowRoutes:
    def test_create_show(self, client, app, sample_user) -> None:  # type: ignore[no-untyped-def]
        headers = make_auth_headers(app, sample_user)
        resp = client.post("/api/v1/shows", headers=headers, json={"title": "My Show"})
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["data"]["title"] == "My Show"
        assert data["data"]["status"] == "planned"

    def test_create_show_no_title(self, client, app, sample_user) -> None:  # type: ignore[no-untyped-def]
        headers = make_auth_headers(app, sample_user)
        resp = client.post("/api/v1/shows", headers=headers, json={})
        assert resp.status_code == 422

    def test_list_shows(self, client, app, sample_user, sample_show) -> None:  # type: ignore[no-untyped-def]
        headers = make_auth_headers(app, sample_user)
        resp = client.get("/api/v1/shows", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["total_count"] >= 1

    def test_get_show(self, client, app, sample_user, sample_show) -> None:  # type: ignore[no-untyped-def]
        headers = make_auth_headers(app, sample_user)
        resp = client.get(f"/api/v1/shows/{sample_show.id}", headers=headers)
        assert resp.status_code == 200

    def test_get_show_invalid_id(self, client, app, sample_user) -> None:  # type: ignore[no-untyped-def]
        headers = make_auth_headers(app, sample_user)
        resp = client.get("/api/v1/shows/not-a-uuid", headers=headers)
        assert resp.status_code == 400

    def test_get_show_not_found(self, client, app, sample_user) -> None:  # type: ignore[no-untyped-def]
        headers = make_auth_headers(app, sample_user)
        resp = client.get(f"/api/v1/shows/{uuid.uuid4()}", headers=headers)
        assert resp.status_code == 404

    def test_update_show(self, client, app, sample_user, sample_show) -> None:  # type: ignore[no-untyped-def]
        headers = make_auth_headers(app, sample_user)
        resp = client.put(f"/api/v1/shows/{sample_show.id}", headers=headers, json={"title": "Updated"})
        assert resp.status_code == 200
        assert resp.get_json()["data"]["title"] == "Updated"

    def test_delete_show(self, client, app, sample_user, sample_show) -> None:  # type: ignore[no-untyped-def]
        headers = make_auth_headers(app, sample_user)
        resp = client.delete(f"/api/v1/shows/{sample_show.id}", headers=headers)
        assert resp.status_code == 200

    def test_start_show(self, client, app, sample_user, sample_show) -> None:  # type: ignore[no-untyped-def]
        headers = make_auth_headers(app, sample_user)
        resp = client.post(f"/api/v1/shows/{sample_show.id}/start", headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["status"] == "live"

    def test_complete_show(self, client, app, sample_user, sample_show) -> None:  # type: ignore[no-untyped-def]
        headers = make_auth_headers(app, sample_user)
        client.post(f"/api/v1/shows/{sample_show.id}/start", headers=headers)
        resp = client.post(f"/api/v1/shows/{sample_show.id}/complete", headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["status"] == "completed"

    def test_cancel_show(self, client, app, sample_user, sample_show) -> None:  # type: ignore[no-untyped-def]
        headers = make_auth_headers(app, sample_user)
        resp = client.post(f"/api/v1/shows/{sample_show.id}/cancel", headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["status"] == "cancelled"

    def test_invalid_transition(self, client, app, sample_user, sample_show) -> None:  # type: ignore[no-untyped-def]
        headers = make_auth_headers(app, sample_user)
        resp = client.post(f"/api/v1/shows/{sample_show.id}/complete", headers=headers)
        assert resp.status_code == 409

    def test_show_orders(self, client, app, sample_user, sample_show, sample_order) -> None:  # type: ignore[no-untyped-def]
        headers = make_auth_headers(app, sample_user)
        resp = client.get(f"/api/v1/shows/{sample_show.id}/orders", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["summary"]["order_count"] >= 1

    def test_no_auth(self, client) -> None:  # type: ignore[no-untyped-def]
        resp = client.get("/api/v1/shows")
        assert resp.status_code == 401


class TestOrderRoutes:
    def test_create_order(self, client, app, sample_user, sample_show, sample_item) -> None:  # type: ignore[no-untyped-def]
        headers = make_auth_headers(app, sample_user)
        resp = client.post("/api/v1/orders", headers=headers, json={
            "show_id": str(sample_show.id),
            "inventory_item_id": str(sample_item.id),
            "sale_price": 25.0,
            "platform_fees": 2.50,
            "shipping_cost": 5.0,
        })
        assert resp.status_code == 201
        data = resp.get_json()["data"]
        assert data["profit"] == 7.0

    def test_create_order_missing_fields(self, client, app, sample_user) -> None:  # type: ignore[no-untyped-def]
        headers = make_auth_headers(app, sample_user)
        resp = client.post("/api/v1/orders", headers=headers, json={})
        assert resp.status_code == 422

    def test_list_orders(self, client, app, sample_user, sample_order) -> None:  # type: ignore[no-untyped-def]
        headers = make_auth_headers(app, sample_user)
        resp = client.get("/api/v1/orders", headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["total_count"] >= 1

    def test_get_order(self, client, app, sample_user, sample_order) -> None:  # type: ignore[no-untyped-def]
        headers = make_auth_headers(app, sample_user)
        resp = client.get(f"/api/v1/orders/{sample_order.id}", headers=headers)
        assert resp.status_code == 200

    def test_get_order_invalid_id(self, client, app, sample_user) -> None:  # type: ignore[no-untyped-def]
        headers = make_auth_headers(app, sample_user)
        resp = client.get("/api/v1/orders/bad-id", headers=headers)
        assert resp.status_code == 400

    def test_update_order(self, client, app, sample_user, sample_order) -> None:  # type: ignore[no-untyped-def]
        headers = make_auth_headers(app, sample_user)
        resp = client.put(f"/api/v1/orders/{sample_order.id}", headers=headers, json={"sale_price": 30.0})
        assert resp.status_code == 200
        assert resp.get_json()["data"]["sale_price"] == 30.0

    def test_delete_order(self, client, app, sample_user, sample_order) -> None:  # type: ignore[no-untyped-def]
        headers = make_auth_headers(app, sample_user)
        resp = client.delete(f"/api/v1/orders/{sample_order.id}", headers=headers)
        assert resp.status_code == 200

    def test_cancel_order(self, client, app, sample_user, sample_order) -> None:  # type: ignore[no-untyped-def]
        headers = make_auth_headers(app, sample_user)
        resp = client.post(f"/api/v1/orders/{sample_order.id}/cancel", headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["status"] == "cancelled"

    def test_list_deleted_orders(self, client, app, sample_user, sample_order) -> None:  # type: ignore[no-untyped-def]
        headers = make_auth_headers(app, sample_user)
        client.delete(f"/api/v1/orders/{sample_order.id}", headers=headers)
        resp = client.get("/api/v1/orders/deleted", headers=headers)
        assert resp.status_code == 200

    def test_restore_order(self, client, app, sample_user, sample_order) -> None:  # type: ignore[no-untyped-def]
        headers = make_auth_headers(app, sample_user)
        client.delete(f"/api/v1/orders/{sample_order.id}", headers=headers)
        resp = client.post(f"/api/v1/orders/{sample_order.id}/restore", headers=headers)
        assert resp.status_code == 200

    def test_no_auth(self, client) -> None:  # type: ignore[no-untyped-def]
        resp = client.get("/api/v1/orders")
        assert resp.status_code == 401
