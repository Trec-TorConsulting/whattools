"""add shows and orders tables

Revision ID: a2b3c4d5e6f7
Revises: f16695bf183e
Create Date: 2026-03-09 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, Sequence[str], None] = 'f16695bf183e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create shows and orders tables for the sales service."""

    # --- shows ---
    op.create_table(
        'shows',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('account_id', sa.Uuid(), sa.ForeignKey('accounts.id'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False, server_default='whatnot'),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='planned'),
        sa.Column('notes', sa.Text(), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_shows_account_id', 'shows', ['account_id'])
    op.create_index('ix_shows_status', 'shows', ['status'])

    # --- orders ---
    op.create_table(
        'orders',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('account_id', sa.Uuid(), sa.ForeignKey('accounts.id'), nullable=False),
        sa.Column('show_id', sa.Uuid(), sa.ForeignKey('shows.id'), nullable=False),
        sa.Column('inventory_item_id', sa.Uuid(), sa.ForeignKey('inventory_items.id'), nullable=False),
        sa.Column('sale_price', sa.Numeric(12, 2), nullable=False),
        sa.Column('platform_fees', sa.Numeric(12, 2), nullable=False, server_default=sa.text('0')),
        sa.Column('shipping_cost', sa.Numeric(12, 2), nullable=False, server_default=sa.text('0')),
        sa.Column('cost_basis', sa.Numeric(12, 2), nullable=False, server_default=sa.text('0')),
        sa.Column('profit', sa.Numeric(12, 2), nullable=False, server_default=sa.text('0')),
        sa.Column('buyer_username', sa.String(255), nullable=False, server_default=''),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('notes', sa.Text(), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_orders_account_id', 'orders', ['account_id'])
    op.create_index('ix_orders_show_id', 'orders', ['show_id'])
    op.create_index('ix_orders_inventory_item_id', 'orders', ['inventory_item_id'])
    op.create_index('ix_orders_status', 'orders', ['status'])


def downgrade() -> None:
    """Drop shows and orders tables."""
    op.drop_table('orders')
    op.drop_table('shows')
