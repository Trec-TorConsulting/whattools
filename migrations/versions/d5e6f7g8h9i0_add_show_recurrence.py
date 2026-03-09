"""add show recurrence and scheduling fields

Revision ID: d5e6f7g8h9i0
Revises: c4d5e6f7g8h9
Create Date: 2026-03-09 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5e6f7g8h9i0'
down_revision: Union[str, None] = 'c4d5e6f7g8h9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('shows', sa.Column('scheduled_end_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('shows', sa.Column('recurrence_rule', sa.String(20), nullable=True))
    op.add_column('shows', sa.Column('recurrence_days', sa.String(100), nullable=True))
    op.add_column('shows', sa.Column('recurrence_weeks', sa.Integer(), nullable=True))
    op.add_column('shows', sa.Column('recurrence_group_id', sa.Uuid(), nullable=True))
    op.create_index('ix_shows_recurrence_group_id', 'shows', ['recurrence_group_id'])


def downgrade() -> None:
    op.drop_index('ix_shows_recurrence_group_id', table_name='shows')
    op.drop_column('shows', 'recurrence_group_id')
    op.drop_column('shows', 'recurrence_weeks')
    op.drop_column('shows', 'recurrence_days')
    op.drop_column('shows', 'recurrence_rule')
    op.drop_column('shows', 'scheduled_end_at')
