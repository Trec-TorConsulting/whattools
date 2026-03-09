"""Tests for packing list routes."""

import json
import uuid
from unittest.mock import patch

import pytest

from services.shipping.routes.packing_list_routes import packing_lists_bp
from services.shared.errors import register_error_handlers


class TestPackingListRoutes:
    """Tests for packing list generation routes."""

    @pytest.fixture(autouse=True)
    def setup_app(self, app, db_session):
        register_error_handlers(app)
        app.register_blueprint(packing_lists_bp, url_prefix="/api/v1/packing-lists")
        self.client = app.test_client()
        self.app = app
        self.db_session = db_session

    def test_get_packing_list(self, sample_user, sample_show, sample_order):
        from services.shipping.tests.conftest import make_auth_headers

        headers = make_auth_headers(self.app, sample_user)
        with patch("services.shipping.routes.packing_list_routes.get_db", return_value=self.db_session):
            resp = self.client.get(f"/api/v1/packing-lists/{sample_show.id}", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["show"]["id"] == str(sample_show.id)
        assert data["data"]["summary"]["total_buyers"] == 1

    def test_get_packing_list_invalid_id(self, sample_user):
        from services.shipping.tests.conftest import make_auth_headers

        headers = make_auth_headers(self.app, sample_user)
        with patch("services.shipping.routes.packing_list_routes.get_db", return_value=self.db_session):
            resp = self.client.get("/api/v1/packing-lists/not-a-uuid", headers=headers)
        assert resp.status_code == 400

    def test_get_packing_list_not_found(self, sample_user):
        from services.shipping.tests.conftest import make_auth_headers

        headers = make_auth_headers(self.app, sample_user)
        fake_id = str(uuid.uuid4())
        with patch("services.shipping.routes.packing_list_routes.get_db", return_value=self.db_session):
            resp = self.client.get(f"/api/v1/packing-lists/{fake_id}", headers=headers)
        assert resp.status_code == 404

    def test_get_packing_list_no_auth(self, sample_show):
        resp = self.client.get(f"/api/v1/packing-lists/{sample_show.id}")
        assert resp.status_code == 401
