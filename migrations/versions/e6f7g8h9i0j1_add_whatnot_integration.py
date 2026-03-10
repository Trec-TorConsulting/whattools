"""add whatnot integration tables and columns

Revision ID: e6f7g8h9i0j1
Revises: d5e6f7g8h9i0
Create Date: 2026-04-01 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6f7g8h9i0j1'
down_revision: Union[str, Sequence[str], None] = 'd5e6f7g8h9i0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create whatnot tables and add integration columns to existing tables."""

    # ── New tables ───────────────────────────────────────────────────

    op.create_table(
        'whatnot_credentials',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('account_id', sa.Uuid(), sa.ForeignKey('accounts.id'), nullable=False, unique=True),
        sa.Column('whatnot_user_id', sa.String(255), nullable=False, server_default=''),
        sa.Column('whatnot_username', sa.String(255), nullable=False, server_default=''),
        sa.Column('encrypted_access_token', sa.Text(), nullable=False, server_default=''),
        sa.Column('encrypted_refresh_token', sa.Text(), nullable=False, server_default=''),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scopes', sa.Text(), nullable=False, server_default=''),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('webhook_secret', sa.String(255), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_whatnot_credentials_account_id', 'whatnot_credentials', ['account_id'], unique=True)

    op.create_table(
        'sync_logs',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('account_id', sa.Uuid(), sa.ForeignKey('accounts.id'), nullable=False),
        sa.Column('sync_type', sa.String(30), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='running'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('items_synced', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('items_created', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('items_updated', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('items_failed', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_sync_logs_account_id', 'sync_logs', ['account_id'])
    op.create_index('ix_sync_logs_sync_type', 'sync_logs', ['sync_type'])

    op.create_table(
        'webhook_events',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('account_id', sa.Uuid(), sa.ForeignKey('accounts.id'), nullable=False),
        sa.Column('event_id', sa.String(255), nullable=False, unique=True),
        sa.Column('topic', sa.String(100), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_webhook_events_account_id', 'webhook_events', ['account_id'])
    op.create_index('ix_webhook_events_event_id', 'webhook_events', ['event_id'], unique=True)
    op.create_index('ix_webhook_events_status', 'webhook_events', ['status'])

    # ── Add columns to existing tables ───────────────────────────────

    # accounts: Stripe billing
    op.add_column('accounts', sa.Column('stripe_customer_id', sa.String(255), nullable=True))
    op.add_column('accounts', sa.Column('subscription_status', sa.String(50), nullable=True))

    # inventory_items: Whatnot integration
    op.add_column('inventory_items', sa.Column('whatnot_product_id', sa.String(255), nullable=True))
    op.add_column('inventory_items', sa.Column('whatnot_variant_id', sa.String(255), nullable=True))
    op.add_column('inventory_items', sa.Column('whatnot_listing_id', sa.String(255), nullable=True))
    op.add_column('inventory_items', sa.Column('image_urls', sa.JSON(), nullable=True))
    op.create_index('ix_inventory_items_whatnot_product_id', 'inventory_items', ['whatnot_product_id'])

    # orders: Whatnot integration
    op.add_column('orders', sa.Column('whatnot_order_id', sa.String(255), nullable=True))
    op.add_column('orders', sa.Column('whatnot_customer_id', sa.String(255), nullable=True))
    op.add_column('orders', sa.Column('sales_channel', sa.String(50), nullable=True))
    op.add_column('orders', sa.Column('is_giveaway', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('orders', sa.Column('is_pickup', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.create_index('ix_orders_whatnot_order_id', 'orders', ['whatnot_order_id'])

    # shows: Whatnot integration
    op.add_column('shows', sa.Column('whatnot_livestream_id', sa.String(255), nullable=True))
    op.create_index('ix_shows_whatnot_livestream_id', 'shows', ['whatnot_livestream_id'])


def downgrade() -> None:
    """Remove whatnot tables and columns."""

    # Drop added columns
    op.drop_index('ix_shows_whatnot_livestream_id', 'shows')
    op.drop_column('shows', 'whatnot_livestream_id')

    op.drop_index('ix_orders_whatnot_order_id', 'orders')
    op.drop_column('orders', 'is_pickup')
    op.drop_column('orders', 'is_giveaway')
    op.drop_column('orders', 'sales_channel')
    op.drop_column('orders', 'whatnot_customer_id')
    op.drop_column('orders', 'whatnot_order_id')

    op.drop_index('ix_inventory_items_whatnot_product_id', 'inventory_items')
    op.drop_column('inventory_items', 'image_urls')
    op.drop_column('inventory_items', 'whatnot_listing_id')
    op.drop_column('inventory_items', 'whatnot_variant_id')
    op.drop_column('inventory_items', 'whatnot_product_id')

    op.drop_column('accounts', 'subscription_status')
    op.drop_column('accounts', 'stripe_customer_id')

    # Drop new tables
    op.drop_table('webhook_events')
    op.drop_table('sync_logs')
    op.drop_table('whatnot_credentials')
