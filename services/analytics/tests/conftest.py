"""Test fixtures for analytics service tests."""

import uuid
from collections.abc import Generator
from datetime import datetime, timedelta, timezone
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
def sample_account(db_session: Session) -> Account:
    account = Account(name="Test Business", plan_tier=PlanTier.FREE)
    db_session.add(account)
    db_session.flush()
    return account


@pytest.fixture()
def sample_user(db_session: Session, sample_account: Account) -> User:
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
    account = Account(name="Other Business", plan_tier=PlanTier.FREE)
    db_session.add(account)
    db_session.flush()
    return account


@pytest.fixture()
def other_user(db_session: Session, other_account: Account) -> User:
    user = User(
        account_id=other_account.id,
        email="other@test.com",
        password_hash="",
        name="Other Owner",
        role=TeamRole.OWNER,
        is_verified=True,
        is_active=True,
    )
    user.set_password("StrongPass1")
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture()
def sample_category(db_session: Session, sample_account: Account) -> Category:
    cat = Category(account_id=sample_account.id, name="Electronics", description="Electronic items")
    db_session.add(cat)
    db_session.flush()
    return cat


@pytest.fixture()
def second_category(db_session: Session, sample_account: Account) -> Category:
    cat = Category(account_id=sample_account.id, name="Cards", description="Trading cards")
    db_session.add(cat)
    db_session.flush()
    return cat


@pytest.fixture()
def sample_item(db_session: Session, sample_account: Account, sample_category: Category) -> InventoryItem:
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
def sold_item(db_session: Session, sample_account: Account, sample_category: Category) -> InventoryItem:
    item = InventoryItem(
        account_id=sample_account.id,
        name="Sold Widget",
        description="A sold widget",
        category_id=sample_category.id,
        cogs=8.00,
        quantity=1,
        status=ItemStatus.SOLD,
    )
    db_session.add(item)
    db_session.flush()
    return item


@pytest.fixture()
def card_item(db_session: Session, sample_account: Account, second_category: Category) -> InventoryItem:
    item = InventoryItem(
        account_id=sample_account.id,
        name="Rare Card",
        description="A rare trading card",
        category_id=second_category.id,
        cogs=5.00,
        quantity=1,
        status=ItemStatus.SOLD,
    )
    db_session.add(item)
    db_session.flush()
    return item


@pytest.fixture()
def sample_show(db_session: Session, sample_account: Account) -> Show:
    show = Show(
        account_id=sample_account.id,
        title="Friday Night Cards",
        platform="whatnot",
    )
    db_session.add(show)
    db_session.flush()
    return show


@pytest.fixture()
def completed_show(db_session: Session, sample_account: Account) -> Show:
    show = Show(
        account_id=sample_account.id,
        title="Saturday Auction",
        platform="whatnot",
        status=ShowStatus.COMPLETED,
        started_at=datetime.now(timezone.utc) - timedelta(hours=3),
        ended_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    db_session.add(show)
    db_session.flush()
    return show


@pytest.fixture()
def sample_order(
    db_session: Session, sample_account: Account, sample_show: Show, sold_item: InventoryItem,
) -> Order:
    order = Order(
        account_id=sample_account.id,
        show_id=sample_show.id,
        inventory_item_id=sold_item.id,
        sale_price=25.00,
        platform_fees=2.50,
        shipping_cost=5.00,
        cost_basis=float(sold_item.cogs),
        profit=25.00 - 2.50 - 5.00 - float(sold_item.cogs),
    )
    db_session.add(order)
    db_session.flush()
    return order


@pytest.fixture()
def card_order(
    db_session: Session, sample_account: Account, sample_show: Show, card_item: InventoryItem,
) -> Order:
    order = Order(
        account_id=sample_account.id,
        show_id=sample_show.id,
        inventory_item_id=card_item.id,
        sale_price=50.00,
        platform_fees=5.00,
        shipping_cost=3.00,
        cost_basis=float(card_item.cogs),
        profit=50.00 - 5.00 - 3.00 - float(card_item.cogs),
    )
    db_session.add(order)
    db_session.flush()
    return order


@pytest.fixture()
def cancelled_order(
    db_session: Session, sample_account: Account, sample_show: Show, sample_item: InventoryItem,
) -> Order:
    order = Order(
        account_id=sample_account.id,
        show_id=sample_show.id,
        inventory_item_id=sample_item.id,
        sale_price=15.00,
        platform_fees=1.50,
        shipping_cost=2.00,
        cost_basis=float(sample_item.cogs),
        profit=0.0,
        status=OrderStatus.CANCELLED,
    )
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
    test_app.config["_REDIS_CLIENT"] = None
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
