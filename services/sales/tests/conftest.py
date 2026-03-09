"""Test fixtures for sales service tests."""

import uuid
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from services.auth.models.models import Account, PlanTier, User, TeamRole
from services.inventory.models.models import Category, InventoryItem, ItemStatus
from services.sales.models.models import Order, OrderStatus, Show, ShowStatus
from services.shared.models import Base


@pytest.fixture(scope="session")
def db_engine() -> Any:
    """Create a test database engine using SQLite in-memory."""
    engine = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    from services.auth.models import models as _auth_models  # noqa: F401
    from services.inventory.models import models as _inv_models  # noqa: F401
    from services.sales.models import models as _sales_models  # noqa: F401

    Base.metadata.create_all(engine)
    return engine


@pytest.fixture()
def db_session(db_engine: Any) -> Generator[Session, None, None]:
    """Create a database session that rolls back after each test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection)
    session = factory()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def mock_event_publisher() -> MagicMock:
    publisher = MagicMock()
    publisher.publish = MagicMock(return_value=True)
    return publisher


@pytest.fixture()
def sample_account(db_session: Session) -> Account:
    """Create a sample account."""
    account = Account(name="Test Business", plan_tier=PlanTier.FREE)
    db_session.add(account)
    db_session.flush()
    return account


@pytest.fixture()
def sample_user(db_session: Session, sample_account: Account) -> User:
    """Create a sample owner user."""
    user = User(
        account_id=sample_account.id,
        email="owner@test.com",
        password_hash="",
        name="Test Owner",
        role=TeamRole.OWNER,
        is_verified=True,
        is_active=True,
    )
    user.set_password("StrongPass1")
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture()
def other_account(db_session: Session) -> Account:
    """Create another account for cross-account testing."""
    account = Account(name="Other Business", plan_tier=PlanTier.FREE)
    db_session.add(account)
    db_session.flush()
    return account


@pytest.fixture()
def sample_category(db_session: Session, sample_account: Account) -> Category:
    """Create a sample category."""
    cat = Category(account_id=sample_account.id, name="Electronics", description="Electronic items")
    db_session.add(cat)
    db_session.flush()
    return cat


@pytest.fixture()
def sample_item(db_session: Session, sample_account: Account, sample_category: Category) -> InventoryItem:
    """Create a sample inventory item."""
    item = InventoryItem(
        account_id=sample_account.id,
        name="Test Widget",
        description="A test widget",
        category_id=sample_category.id,
        cogs=10.50,
        quantity=1,
        status=ItemStatus.AVAILABLE,
    )
    db_session.add(item)
    db_session.flush()
    return item


@pytest.fixture()
def sample_item_no_cogs(db_session: Session, sample_account: Account) -> InventoryItem:
    """Create an item with zero COGS."""
    item = InventoryItem(
        account_id=sample_account.id,
        name="Free Item",
        description="No cost",
        cogs=0.0,
        quantity=1,
        status=ItemStatus.AVAILABLE,
    )
    db_session.add(item)
    db_session.flush()
    return item


@pytest.fixture()
def sample_show(db_session: Session, sample_account: Account) -> Show:
    """Create a sample show."""
    show = Show(
        account_id=sample_account.id,
        title="Friday Night Cards",
        platform="whatnot",
    )
    db_session.add(show)
    db_session.flush()
    return show


@pytest.fixture()
def sample_order(
    db_session: Session, sample_account: Account, sample_show: Show, sample_item: InventoryItem
) -> Order:
    """Create a sample order."""
    order = Order(
        account_id=sample_account.id,
        show_id=sample_show.id,
        inventory_item_id=sample_item.id,
        sale_price=25.00,
        platform_fees=2.50,
        shipping_cost=5.00,
        cost_basis=float(sample_item.cogs),
        profit=25.00 - 2.50 - 5.00 - float(sample_item.cogs),
    )
    sample_item.status = ItemStatus.SOLD
    db_session.add(order)
    db_session.flush()
    return order


@pytest.fixture()
def app(db_engine: Any) -> Flask:
    """Create a test Flask app."""
    test_app = Flask("test")
    test_app.config["TESTING"] = True
    test_app.config["SECRET_KEY"] = "test-secret"
    test_app.config["JWT_SECRET_KEY"] = "test-jwt-secret"
    test_app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 900
    test_app.config["JWT_REFRESH_TOKEN_EXPIRES"] = 604800
    test_app.config["_EVENT_PUBLISHER"] = None
    JWTManager(test_app)
    return test_app


def make_auth_headers(app: Flask, user: User, *, item_limit: int = 50) -> dict[str, str]:
    """Generate Authorization headers with a JWT for the given user."""
    with app.app_context():
        token = create_access_token(
            identity=str(user.id),
            additional_claims={
                "account_id": str(user.account_id),
                "role": user.role,
                "item_limit": item_limit,
            },
        )
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
