"""add premium mode and position sizing mode columns

Revision ID: 003_premium_and_sizing_modes
Revises: 002_strategy_type
Create Date: 2026-04-12

"""
from alembic import op
import sqlalchemy as sa

revision = '003_premium_and_sizing_modes'
down_revision = '002_strategy_type'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('sell_put_rules') as batch_op:
        # Premium mode columns
        batch_op.add_column(sa.Column('min_premium_mode', sa.String(20), nullable=False, server_default='pct'))
        batch_op.add_column(sa.Column('min_premium_dollar', sa.Float(), nullable=True))
        # Position size mode columns
        batch_op.add_column(sa.Column('position_size_mode', sa.String(20), nullable=False, server_default='pct'))
        batch_op.add_column(sa.Column('position_size_contracts', sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('sell_put_rules') as batch_op:
        batch_op.drop_column('min_premium_mode')
        batch_op.drop_column('min_premium_dollar')
        batch_op.drop_column('position_size_mode')
        batch_op.drop_column('position_size_contracts')
