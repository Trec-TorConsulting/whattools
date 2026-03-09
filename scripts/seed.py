"""Seed data script for development environment.

Creates a test account, test user, and sample categories.

Usage:
    uv run python -m scripts.seed
    # or
    make db-seed
"""

import uuid
from datetime import datetime, timezone

import bcrypt
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.shared.models import Base
from services.auth.models.models import Account, User, PlanTier, TeamRole
from services.inventory.models.models import Category

# Default database URL — override with DATABASE_URL env var
import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://whattools:whattools@localhost:5432/whattools"
)


def seed_database(db: Session) -> None:
    """Insert seed data into the database."""

    # Check if seed data already exists
    existing = db.execute(text("SELECT count(*) FROM accounts")).scalar()
    if existing and existing > 0:
        print("Seed data already exists — skipping.")
        return

    # --- Test Account ---
    account = Account(name="Demo Seller Shop", plan_tier=PlanTier.FREE)
    db.add(account)
    db.flush()

    # --- Test User (owner) ---
    password_hash = bcrypt.hashpw(b"Password123!", bcrypt.gensalt()).decode()
    owner = User(
        account_id=account.id,
        email="demo@whattools.dev",
        password_hash=password_hash,
        name="Demo Owner",
        role=TeamRole.OWNER,
        is_verified=True,
        is_active=True,
    )
    db.add(owner)

    # --- Test User (member) ---
    member_hash = bcrypt.hashpw(b"Member123!", bcrypt.gensalt()).decode()
    member = User(
        account_id=account.id,
        email="member@whattools.dev",
        password_hash=member_hash,
        name="Demo Member",
        role=TeamRole.MEMBER,
        is_verified=True,
        is_active=True,
    )
    db.add(member)

    # --- Sample Categories ---
    categories = [
        Category(account_id=account.id, name="Trading Cards", description="Sports and collectible trading cards"),
        Category(account_id=account.id, name="Vintage Toys", description="Vintage and retro toys"),
        Category(account_id=account.id, name="Comics", description="Comic books and graphic novels"),
        Category(account_id=account.id, name="Electronics", description="Consumer electronics and accessories"),
        Category(account_id=account.id, name="Clothing", description="Apparel and fashion items"),
    ]
    db.add_all(categories)

    db.commit()
    print(f"Seed data created successfully:")
    print(f"  Account: {account.name} (id: {account.id})")
    print(f"  Owner:   {owner.email} / Password123!")
    print(f"  Member:  {member.email} / Member123!")
    print(f"  Categories: {len(categories)} created")


def main() -> None:
    """Run the seed script."""
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as db:
        seed_database(db)


if __name__ == "__main__":
    main()
