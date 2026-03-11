"""add_platform_admin_and_suspension

Revision ID: g7h8i9j0k1l2
Revises: e6f7g8h9i0j1_add_whatnot_integration
Create Date: 2026-03-10 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g7h8i9j0k1l2'
down_revision: Union[str, Sequence[str], None] = 'e6f7g8h9i0j1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add platform admin and suspension fields, create admin_audit_logs table."""

    # Add is_platform_admin to users
    op.add_column('users', sa.Column('is_platform_admin', sa.Boolean(), nullable=False, server_default=sa.text('false')))

    # Add is_suspended to accounts
    op.add_column('accounts', sa.Column('is_suspended', sa.Boolean(), nullable=False, server_default=sa.text('false')))

    # Create admin_audit_logs table
    op.create_table(
        'admin_audit_logs',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('admin_id', sa.Uuid(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('target_type', sa.String(100), nullable=False),
        sa.Column('target_id', sa.Uuid(), nullable=True),
        sa.Column('changes', sa.JSON(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_admin_audit_logs_admin_id', 'admin_audit_logs', ['admin_id'])
    op.create_index('ix_admin_audit_logs_target_type', 'admin_audit_logs', ['target_type'])
    op.create_index('ix_admin_audit_logs_target_id', 'admin_audit_logs', ['target_id'])


def downgrade() -> None:
    """Remove platform admin fields and admin_audit_logs table."""
    op.drop_index('ix_admin_audit_logs_target_id', table_name='admin_audit_logs')
    op.drop_index('ix_admin_audit_logs_target_type', table_name='admin_audit_logs')
    op.drop_index('ix_admin_audit_logs_admin_id', table_name='admin_audit_logs')
    op.drop_table('admin_audit_logs')
    op.drop_column('accounts', 'is_suspended')
    op.drop_column('users', 'is_platform_admin')
