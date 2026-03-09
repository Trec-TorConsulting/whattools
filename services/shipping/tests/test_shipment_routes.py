"""Tests for shipment routes."""

import json
import uuid
from unittest.mock import patch

import pytest

from services.shipping.routes.shipment_routes import shipments_bp
from services.shared.errors import register_error_handlers


class TestShipmentRoutes:
    """Tests for shipment CRUD routes."""

    @pytest.fixture(autouse=True)
    def setup_app(self, app, db_session):
        register_error_handlers(app)
        app.register_blueprint(shipments_bp, url_prefix="/api/v1/shipments")
        self.client = app.test_client()
        self.app = app
        self.db_session = db_session

    def test_create_shipment(self, sample_user, sample_order):
        from services.shipping.tests.conftest import make_auth_headers

        headers = make_auth_headers(self.app, sample_user)
        with patch("services.shipping.routes.shipment_routes.get_db", return_value=self.db_session):
            resp = self.client.post(
                "/api/v1/shipments",
                headers=headers,
                data=json.dumps({"order_id": str(sample_order.id), "carrier": "usps"}),
            )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["data"]["carrier"] == "usps"
        assert data["data"]["status"] == "pending"

    def test_create_shipment_invalid_body(self, sample_user):
        from services.shipping.tests.conftest import make_auth_headers

        headers = make_auth_headers(self.app, sample_user)
        with patch("services.shipping.routes.shipment_routes.get_db", return_value=self.db_session):
            resp = self.client.post(
                "/api/v1/shipments",
                headers=headers,
                data=json.dumps({}),
            )
        assert resp.status_code == 422

    def test_list_shipments(self, sample_user, sample_shipment):
        from services.shipping.tests.conftest import make_auth_headers

        headers = make_auth_headers(self.app, sample_user)
        with patch("services.shipping.routes.shipment_routes.get_db", return_value=self.db_session):
            resp = self.client.get("/api/v1/shipments", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["total_count"] == 1

    def test_get_shipment(self, sample_user, sample_shipment):
        from services.shipping.tests.conftest import make_auth_headers

        headers = make_auth_headers(self.app, sample_user)
        with patch("services.shipping.routes.shipment_routes.get_db", return_value=self.db_session):
            resp = self.client.get(f"/api/v1/shipments/{sample_shipment.id}", headers=headers)
        assert resp.status_code == 200

    def test_get_shipment_invalid_id(self, sample_user):
        from services.shipping.tests.conftest import make_auth_headers

        headers = make_auth_headers(self.app, sample_user)
        with patch("services.shipping.routes.shipment_routes.get_db", return_value=self.db_session):
            resp = self.client.get("/api/v1/shipments/not-a-uuid", headers=headers)
        assert resp.status_code == 400

    def test_update_shipment(self, sample_user, sample_shipment):
        from services.shipping.tests.conftest import make_auth_headers

        headers = make_auth_headers(self.app, sample_user)
        with patch("services.shipping.routes.shipment_routes.get_db", return_value=self.db_session):
            resp = self.client.put(
                f"/api/v1/shipments/{sample_shipment.id}",
                headers=headers,
                data=json.dumps({"tracking_number": "NEWTRACK"}),
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["tracking_number"] == "NEWTRACK"

    def test_delete_shipment(self, sample_user, sample_shipment):
        from services.shipping.tests.conftest import make_auth_headers

        headers = make_auth_headers(self.app, sample_user)
        with patch("services.shipping.routes.shipment_routes.get_db", return_value=self.db_session):
            resp = self.client.delete(f"/api/v1/shipments/{sample_shipment.id}", headers=headers)
        assert resp.status_code == 200

    def test_mark_shipped(self, sample_user, sample_shipment):
        from services.shipping.tests.conftest import make_auth_headers
        from services.shipping.models.models import ShipmentStatus

        sample_shipment.status = ShipmentStatus.LABEL_CREATED
        self.db_session.flush()

        headers = make_auth_headers(self.app, sample_user)
        with patch("services.shipping.routes.shipment_routes.get_db", return_value=self.db_session):
            resp = self.client.post(f"/api/v1/shipments/{sample_shipment.id}/ship", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["status"] == "shipped"

    def test_mark_delivered(self, sample_user, sample_shipment):
        from services.shipping.tests.conftest import make_auth_headers
        from services.shipping.models.models import ShipmentStatus

        sample_shipment.status = ShipmentStatus.SHIPPED
        self.db_session.flush()

        headers = make_auth_headers(self.app, sample_user)
        with patch("services.shipping.routes.shipment_routes.get_db", return_value=self.db_session):
            resp = self.client.post(f"/api/v1/shipments/{sample_shipment.id}/deliver", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["status"] == "delivered"

    def test_cancel_shipment(self, sample_user, sample_shipment):
        from services.shipping.tests.conftest import make_auth_headers

        headers = make_auth_headers(self.app, sample_user)
        with patch("services.shipping.routes.shipment_routes.get_db", return_value=self.db_session):
            resp = self.client.post(f"/api/v1/shipments/{sample_shipment.id}/cancel", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["status"] == "cancelled"

    def test_create_label(self, sample_user, sample_shipment):
        from services.shipping.tests.conftest import make_auth_headers

        headers = make_auth_headers(self.app, sample_user)
        with patch("services.shipping.routes.shipment_routes.get_db", return_value=self.db_session):
            resp = self.client.post(f"/api/v1/shipments/{sample_shipment.id}/label", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["status"] == "label_created"

    def test_bulk_create(self, sample_user, sample_show, sample_order, sample_order2):
        from services.shipping.tests.conftest import make_auth_headers

        headers = make_auth_headers(self.app, sample_user)
        with patch("services.shipping.routes.shipment_routes.get_db", return_value=self.db_session):
            resp = self.client.post(
                "/api/v1/shipments/bulk",
                headers=headers,
                data=json.dumps({"show_id": str(sample_show.id)}),
            )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["data"]["summary"]["created_count"] == 2

    def test_bulk_create_invalid_body(self, sample_user):
        from services.shipping.tests.conftest import make_auth_headers

        headers = make_auth_headers(self.app, sample_user)
        with patch("services.shipping.routes.shipment_routes.get_db", return_value=self.db_session):
            resp = self.client.post(
                "/api/v1/shipments/bulk",
                headers=headers,
                data=json.dumps({}),
            )
        assert resp.status_code == 422

    def test_list_overdue(self, sample_user):
        from services.shipping.tests.conftest import make_auth_headers

        headers = make_auth_headers(self.app, sample_user)
        with patch("services.shipping.routes.shipment_routes.get_db", return_value=self.db_session):
            resp = self.client.get("/api/v1/shipments/overdue", headers=headers)
        assert resp.status_code == 200

    def test_list_deleted(self, sample_user):
        from services.shipping.tests.conftest import make_auth_headers

        headers = make_auth_headers(self.app, sample_user)
        with patch("services.shipping.routes.shipment_routes.get_db", return_value=self.db_session):
            resp = self.client.get("/api/v1/shipments/deleted", headers=headers)
        assert resp.status_code == 200

    def test_restore_shipment(self, sample_user, sample_shipment):
        from datetime import datetime, timezone
        from services.shipping.tests.conftest import make_auth_headers

        sample_shipment.deleted_at = datetime.now(timezone.utc)
        self.db_session.flush()

        headers = make_auth_headers(self.app, sample_user)
        with patch("services.shipping.routes.shipment_routes.get_db", return_value=self.db_session):
            resp = self.client.post(f"/api/v1/shipments/{sample_shipment.id}/restore", headers=headers)
        assert resp.status_code == 200

    def test_restore_invalid_id(self, sample_user):
        from services.shipping.tests.conftest import make_auth_headers

        headers = make_auth_headers(self.app, sample_user)
        with patch("services.shipping.routes.shipment_routes.get_db", return_value=self.db_session):
            resp = self.client.post("/api/v1/shipments/not-a-uuid/restore", headers=headers)
        assert resp.status_code == 400

    def test_no_auth_returns_401(self):
        resp = self.client.get("/api/v1/shipments")
        assert resp.status_code == 401

    def test_invalid_id_on_update(self, sample_user):
        from services.shipping.tests.conftest import make_auth_headers

        headers = make_auth_headers(self.app, sample_user)
        with patch("services.shipping.routes.shipment_routes.get_db", return_value=self.db_session):
            resp = self.client.put(
                "/api/v1/shipments/not-a-uuid",
                headers=headers,
                data=json.dumps({"carrier": "fedex"}),
            )
        assert resp.status_code == 400

    def test_invalid_id_on_delete(self, sample_user):
        from services.shipping.tests.conftest import make_auth_headers

        headers = make_auth_headers(self.app, sample_user)
        with patch("services.shipping.routes.shipment_routes.get_db", return_value=self.db_session):
            resp = self.client.delete("/api/v1/shipments/not-a-uuid", headers=headers)
        assert resp.status_code == 400

    def test_invalid_id_on_ship(self, sample_user):
        from services.shipping.tests.conftest import make_auth_headers

        headers = make_auth_headers(self.app, sample_user)
        with patch("services.shipping.routes.shipment_routes.get_db", return_value=self.db_session):
            resp = self.client.post("/api/v1/shipments/not-a-uuid/ship", headers=headers)
        assert resp.status_code == 400

    def test_invalid_id_on_deliver(self, sample_user):
        from services.shipping.tests.conftest import make_auth_headers

        headers = make_auth_headers(self.app, sample_user)
        with patch("services.shipping.routes.shipment_routes.get_db", return_value=self.db_session):
            resp = self.client.post("/api/v1/shipments/not-a-uuid/deliver", headers=headers)
        assert resp.status_code == 400

    def test_invalid_id_on_cancel(self, sample_user):
        from services.shipping.tests.conftest import make_auth_headers

        headers = make_auth_headers(self.app, sample_user)
        with patch("services.shipping.routes.shipment_routes.get_db", return_value=self.db_session):
            resp = self.client.post("/api/v1/shipments/not-a-uuid/cancel", headers=headers)
        assert resp.status_code == 400

    def test_invalid_id_on_label(self, sample_user):
        from services.shipping.tests.conftest import make_auth_headers

        headers = make_auth_headers(self.app, sample_user)
        with patch("services.shipping.routes.shipment_routes.get_db", return_value=self.db_session):
            resp = self.client.post("/api/v1/shipments/not-a-uuid/label", headers=headers)
        assert resp.status_code == 400
