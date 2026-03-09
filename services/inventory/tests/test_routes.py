"""Integration tests for inventory routes."""

import io
import json
import uuid
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from services.auth.models.models import Account, PlanTier, User, TeamRole
from services.inventory.app import create_app
from services.inventory.models.models import Category, InventoryItem, ItemStatus
from services.inventory.tests.conftest import make_auth_headers
from services.shared.models import Base


@pytest.fixture(scope="module")
def route_engine():  # type: ignore[no-untyped-def]
    engine = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    from services.auth.models import models as _auth  # noqa: F401
    from services.inventory.models import models as _inv  # noqa: F401

    Base.metadata.create_all(engine)
    return engine


@pytest.fixture()
def route_session(route_engine):  # type: ignore[no-untyped-def]
    connection = route_engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection)
    session = factory()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def route_app(route_engine):  # type: ignore[no-untyped-def]
    app = create_app(config_overrides={
        "TESTING": True,
        "SECRET_KEY": "test-secret",
        "JWT_SECRET_KEY": "test-jwt-secret",
        "_EVENT_PUBLISHER": None,
    })
    return app


@pytest.fixture()
def route_fixtures(route_session):  # type: ignore[no-untyped-def]
    """Create account, user, category for route tests."""
    account = Account(name="Route Test Biz", plan_tier=PlanTier.FREE)
    route_session.add(account)
    route_session.flush()

    user = User(
        account_id=account.id,
        email="routetest@test.com",
        password_hash="",
        name="Route User",
        role=TeamRole.OWNER,
        is_verified=True,
        is_active=True,
    )
    user.set_password("StrongPass1")
    route_session.add(user)
    route_session.flush()

    cat = Category(account_id=account.id, name="Test Cat", description="Test category")
    route_session.add(cat)
    route_session.flush()

    return {"account": account, "user": user, "category": cat}


class TestItemRoutes:
    def test_create_item(self, route_app, route_session, route_fixtures):  # type: ignore[no-untyped-def]
        user = route_fixtures["user"]
        headers = make_auth_headers(route_app, user)

        with route_app.test_client() as client:
            with patch("services.inventory.routes.item_routes.get_db", return_value=route_session):
                resp = client.post(
                    "/api/v1/items",
                    headers=headers,
                    json={"name": "New Widget", "cogs": 15.0, "quantity": 3},
                )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["data"]["name"] == "New Widget"

    def test_create_item_validation_error(self, route_app, route_session, route_fixtures):  # type: ignore[no-untyped-def]
        user = route_fixtures["user"]
        headers = make_auth_headers(route_app, user)

        with route_app.test_client() as client:
            with patch("services.inventory.routes.item_routes.get_db", return_value=route_session):
                resp = client.post(
                    "/api/v1/items",
                    headers=headers,
                    json={},  # Missing name
                )
        assert resp.status_code == 422

    def test_get_item(self, route_app, route_session, route_fixtures):  # type: ignore[no-untyped-def]
        user = route_fixtures["user"]
        account = route_fixtures["account"]
        headers = make_auth_headers(route_app, user)

        item = InventoryItem(account_id=account.id, name="Get Me", cogs=5.0)
        route_session.add(item)
        route_session.flush()

        with route_app.test_client() as client:
            with patch("services.inventory.routes.item_routes.get_db", return_value=route_session):
                resp = client.get(f"/api/v1/items/{item.id}", headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["name"] == "Get Me"

    def test_get_item_invalid_id(self, route_app, route_session, route_fixtures):  # type: ignore[no-untyped-def]
        user = route_fixtures["user"]
        headers = make_auth_headers(route_app, user)

        with route_app.test_client() as client:
            with patch("services.inventory.routes.item_routes.get_db", return_value=route_session):
                resp = client.get("/api/v1/items/not-a-uuid", headers=headers)
        assert resp.status_code == 400

    def test_get_item_not_found(self, route_app, route_session, route_fixtures):  # type: ignore[no-untyped-def]
        user = route_fixtures["user"]
        headers = make_auth_headers(route_app, user)

        with route_app.test_client() as client:
            with patch("services.inventory.routes.item_routes.get_db", return_value=route_session):
                resp = client.get(f"/api/v1/items/{uuid.uuid4()}", headers=headers)
        assert resp.status_code == 404

    def test_list_items(self, route_app, route_session, route_fixtures):  # type: ignore[no-untyped-def]
        user = route_fixtures["user"]
        account = route_fixtures["account"]
        headers = make_auth_headers(route_app, user)

        for i in range(3):
            route_session.add(InventoryItem(account_id=account.id, name=f"List Item {i}"))
        route_session.flush()

        with route_app.test_client() as client:
            with patch("services.inventory.routes.item_routes.get_db", return_value=route_session):
                resp = client.get("/api/v1/items", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert len(data["items"]) >= 3

    def test_update_item(self, route_app, route_session, route_fixtures):  # type: ignore[no-untyped-def]
        user = route_fixtures["user"]
        account = route_fixtures["account"]
        headers = make_auth_headers(route_app, user)

        item = InventoryItem(account_id=account.id, name="Before Update")
        route_session.add(item)
        route_session.flush()

        with route_app.test_client() as client:
            with patch("services.inventory.routes.item_routes.get_db", return_value=route_session):
                resp = client.put(
                    f"/api/v1/items/{item.id}",
                    headers=headers,
                    json={"name": "After Update"},
                )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["name"] == "After Update"

    def test_delete_item(self, route_app, route_session, route_fixtures):  # type: ignore[no-untyped-def]
        user = route_fixtures["user"]
        account = route_fixtures["account"]
        headers = make_auth_headers(route_app, user)

        item = InventoryItem(account_id=account.id, name="To Delete")
        route_session.add(item)
        route_session.flush()

        with route_app.test_client() as client:
            with patch("services.inventory.routes.item_routes.get_db", return_value=route_session):
                resp = client.delete(f"/api/v1/items/{item.id}", headers=headers)
        assert resp.status_code == 200

    def test_list_deleted(self, route_app, route_session, route_fixtures):  # type: ignore[no-untyped-def]
        user = route_fixtures["user"]
        headers = make_auth_headers(route_app, user)

        with route_app.test_client() as client:
            with patch("services.inventory.routes.item_routes.get_db", return_value=route_session):
                resp = client.get("/api/v1/items/deleted", headers=headers)
        assert resp.status_code == 200

    def test_restore_item(self, route_app, route_session, route_fixtures):  # type: ignore[no-untyped-def]
        user = route_fixtures["user"]
        account = route_fixtures["account"]
        headers = make_auth_headers(route_app, user)

        item = InventoryItem(account_id=account.id, name="Restore Me")
        route_session.add(item)
        route_session.flush()

        with route_app.test_client() as client:
            with patch("services.inventory.routes.item_routes.get_db", return_value=route_session):
                # Delete first
                client.delete(f"/api/v1/items/{item.id}", headers=headers)
                # Restore
                resp = client.post(f"/api/v1/items/{item.id}/restore", headers=headers)
        assert resp.status_code == 200

    def test_unauthenticated_rejected(self, route_app):  # type: ignore[no-untyped-def]
        with route_app.test_client() as client:
            resp = client.get("/api/v1/items")
        assert resp.status_code == 401


class TestCategoryRoutes:
    def test_create_category(self, route_app, route_session, route_fixtures):  # type: ignore[no-untyped-def]
        user = route_fixtures["user"]
        headers = make_auth_headers(route_app, user)

        with route_app.test_client() as client:
            with patch("services.inventory.routes.category_routes.get_db", return_value=route_session):
                resp = client.post(
                    "/api/v1/categories",
                    headers=headers,
                    json={"name": "New Category"},
                )
        assert resp.status_code == 201

    def test_create_category_validation_error(self, route_app, route_session, route_fixtures):  # type: ignore[no-untyped-def]
        user = route_fixtures["user"]
        headers = make_auth_headers(route_app, user)

        with route_app.test_client() as client:
            with patch("services.inventory.routes.category_routes.get_db", return_value=route_session):
                resp = client.post(
                    "/api/v1/categories",
                    headers=headers,
                    json={},
                )
        assert resp.status_code == 422

    def test_list_categories(self, route_app, route_session, route_fixtures):  # type: ignore[no-untyped-def]
        user = route_fixtures["user"]
        headers = make_auth_headers(route_app, user)

        with route_app.test_client() as client:
            with patch("services.inventory.routes.category_routes.get_db", return_value=route_session):
                resp = client.get("/api/v1/categories", headers=headers)
        assert resp.status_code == 200

    def test_get_category(self, route_app, route_session, route_fixtures):  # type: ignore[no-untyped-def]
        user = route_fixtures["user"]
        cat = route_fixtures["category"]
        headers = make_auth_headers(route_app, user)

        with route_app.test_client() as client:
            with patch("services.inventory.routes.category_routes.get_db", return_value=route_session):
                resp = client.get(f"/api/v1/categories/{cat.id}", headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["name"] == "Test Cat"

    def test_update_category(self, route_app, route_session, route_fixtures):  # type: ignore[no-untyped-def]
        user = route_fixtures["user"]
        cat = route_fixtures["category"]
        headers = make_auth_headers(route_app, user)

        with route_app.test_client() as client:
            with patch("services.inventory.routes.category_routes.get_db", return_value=route_session):
                resp = client.put(
                    f"/api/v1/categories/{cat.id}",
                    headers=headers,
                    json={"name": "Updated Cat"},
                )
        assert resp.status_code == 200

    def test_delete_category(self, route_app, route_session, route_fixtures):  # type: ignore[no-untyped-def]
        user = route_fixtures["user"]
        account = route_fixtures["account"]
        headers = make_auth_headers(route_app, user)

        cat = Category(account_id=account.id, name="Delete Me Cat")
        route_session.add(cat)
        route_session.flush()

        with route_app.test_client() as client:
            with patch("services.inventory.routes.category_routes.get_db", return_value=route_session):
                resp = client.delete(f"/api/v1/categories/{cat.id}", headers=headers)
        assert resp.status_code == 200

    def test_invalid_category_id(self, route_app, route_session, route_fixtures):  # type: ignore[no-untyped-def]
        user = route_fixtures["user"]
        headers = make_auth_headers(route_app, user)

        with route_app.test_client() as client:
            with patch("services.inventory.routes.category_routes.get_db", return_value=route_session):
                resp = client.get("/api/v1/categories/bad-uuid", headers=headers)
        assert resp.status_code == 400


class TestCSVRoutes:
    def test_upload_csv(self, route_app, route_session, route_fixtures):  # type: ignore[no-untyped-def]
        user = route_fixtures["user"]
        headers = make_auth_headers(route_app, user)
        # Remove Content-Type for multipart
        headers.pop("Content-Type", None)

        csv_data = b"Name,Price,Qty\nWidget,10.00,5\nGadget,20.00,3\n"

        with route_app.test_client() as client:
            with patch("services.inventory.routes.csv_routes.get_db", return_value=route_session):
                resp = client.post(
                    "/api/v1/csv/upload",
                    headers=headers,
                    data={"file": (io.BytesIO(csv_data), "test.csv")},
                    content_type="multipart/form-data",
                )
        assert resp.status_code == 201
        data = resp.get_json()["data"]
        assert data["headers"] == ["Name", "Price", "Qty"]

    def test_upload_csv_no_file(self, route_app, route_session, route_fixtures):  # type: ignore[no-untyped-def]
        user = route_fixtures["user"]
        headers = make_auth_headers(route_app, user)
        headers.pop("Content-Type", None)

        with route_app.test_client() as client:
            with patch("services.inventory.routes.csv_routes.get_db", return_value=route_session):
                resp = client.post(
                    "/api/v1/csv/upload",
                    headers=headers,
                    content_type="multipart/form-data",
                )
        assert resp.status_code == 400

    def test_upload_csv_wrong_extension(self, route_app, route_session, route_fixtures):  # type: ignore[no-untyped-def]
        user = route_fixtures["user"]
        headers = make_auth_headers(route_app, user)
        headers.pop("Content-Type", None)

        with route_app.test_client() as client:
            with patch("services.inventory.routes.csv_routes.get_db", return_value=route_session):
                resp = client.post(
                    "/api/v1/csv/upload",
                    headers=headers,
                    data={"file": (io.BytesIO(b"data"), "test.xlsx")},
                    content_type="multipart/form-data",
                )
        assert resp.status_code == 400

    def test_get_job_status(self, route_app, route_session, route_fixtures):  # type: ignore[no-untyped-def]
        user = route_fixtures["user"]
        headers = make_auth_headers(route_app, user)
        headers_multipart = {k: v for k, v in headers.items() if k != "Content-Type"}

        csv_data = b"Name\nWidget\n"

        with route_app.test_client() as client:
            with patch("services.inventory.routes.csv_routes.get_db", return_value=route_session):
                upload_resp = client.post(
                    "/api/v1/csv/upload",
                    headers=headers_multipart,
                    data={"file": (io.BytesIO(csv_data), "test.csv")},
                    content_type="multipart/form-data",
                )
                job_id = upload_resp.get_json()["data"]["job_id"]

                resp = client.get(f"/api/v1/csv/{job_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["status"] == "pending_mapping"

    def test_get_job_invalid_id(self, route_app, route_session, route_fixtures):  # type: ignore[no-untyped-def]
        user = route_fixtures["user"]
        headers = make_auth_headers(route_app, user)

        with route_app.test_client() as client:
            with patch("services.inventory.routes.csv_routes.get_db", return_value=route_session):
                resp = client.get("/api/v1/csv/bad-id", headers=headers)
        assert resp.status_code == 400


class TestPurgeTask:
    def test_purge_integration(self, db_session, sample_account):  # type: ignore[no-untyped-def]
        from datetime import timedelta

        from services.inventory.tasks.purge_task import run_purge

        # Create an expired item
        item = InventoryItem(account_id=sample_account.id, name="Expired")
        db_session.add(item)
        db_session.flush()

        from datetime import datetime, timezone
        item.deleted_at = datetime.now(timezone.utc) - timedelta(days=31)
        db_session.flush()

        result = run_purge(lambda: db_session)
        assert result["items_purged"] >= 1
