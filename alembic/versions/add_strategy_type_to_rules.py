"""add strategy_type to sell_put_rules

Revision ID: 002_strategy_type
Revises:
Create Date: 2026-04-13

"""
from alembic import op
import sqlalchemy as sa

revision = '002_strategy_type'
down_revision = None  # set to the previous revision id if one exists
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use batch_alter_table for SQLite compatibility
    with op.batch_alter_table('sell_put_rules') as batch_op:
        batch_op.add_column(sa.Column('strategy_type', sa.String(20), nullable=False, server_default='SELL_PUT'))
        batch_op.add_column(sa.Column('min_strike_otm_pct', sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('sell_put_rules') as batch_op:
        batch_op.drop_column('strategy_type')
        batch_op.drop_column('min_strike_otm_pct')
