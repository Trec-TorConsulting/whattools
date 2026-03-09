"""add shipments table

Revision ID: b3c4d5e6f7g8
Revises: a2b3c4d5e6f7
Create Date: 2026-03-10 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3c4d5e6f7g8'
down_revision: Union[str, Sequence[str], None] = 'a2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create shipments table for the shipping service."""

    op.create_table(
        'shipments',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('account_id', sa.Uuid(), sa.ForeignKey('accounts.id'), nullable=False),
        sa.Column('order_id', sa.Uuid(), sa.ForeignKey('orders.id'), nullable=False, unique=True),
        sa.Column('carrier', sa.String(100), nullable=False, server_default=''),
        sa.Column('tracking_number', sa.String(255), nullable=False, server_default=''),
        sa.Column('label_url', sa.String(1024), nullable=False, server_default=''),
        sa.Column('ship_by_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('shipped_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('weight_oz', sa.Numeric(8, 2), nullable=False, server_default=sa.text('0')),
        sa.Column('buyer_name', sa.String(255), nullable=False, server_default=''),
        sa.Column('address_line1', sa.String(255), nullable=False, server_default=''),
        sa.Column('address_line2', sa.String(255), nullable=False, server_default=''),
        sa.Column('city', sa.String(100), nullable=False, server_default=''),
        sa.Column('state', sa.String(50), nullable=False, server_default=''),
        sa.Column('zip_code', sa.String(20), nullable=False, server_default=''),
        sa.Column('country', sa.String(50), nullable=False, server_default='US'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('notes', sa.Text(), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_shipments_account_id', 'shipments', ['account_id'])
    op.create_index('ix_shipments_order_id', 'shipments', ['order_id'], unique=True)
    op.create_index('ix_shipments_status', 'shipments', ['status'])


def downgrade() -> None:
    """Drop shipments table."""
    op.drop_table('shipments')
