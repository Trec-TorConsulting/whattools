"""add export_jobs table

Revision ID: c4d5e6f7g8h9
Revises: b3c4d5e6f7g8
Create Date: 2026-03-10 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d5e6f7g8h9'
down_revision: Union[str, Sequence[str], None] = 'b3c4d5e6f7g8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create export_jobs table for async report generation."""

    op.create_table(
        'export_jobs',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('account_id', sa.Uuid(), sa.ForeignKey('accounts.id'), nullable=False),
        sa.Column('report_type', sa.String(20), nullable=False),
        sa.Column('format', sa.String(10), nullable=False),
        sa.Column('period', sa.String(10), nullable=False, server_default='30d'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('file_path', sa.String(1024), nullable=False, server_default=''),
        sa.Column('file_size', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('error_message', sa.Text(), nullable=False, server_default=''),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_export_jobs_account_id', 'export_jobs', ['account_id'])
    op.create_index('ix_export_jobs_status', 'export_jobs', ['status'])


def downgrade() -> None:
    """Drop export_jobs table."""
    op.drop_table('export_jobs')
