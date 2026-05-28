"""Add strike range, max premium dollar, bid_ask_fill_pct, IV pct filters to rules

Revision ID: 011_rule_premium_strike_iv
Revises: 010_rule_last_error
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa

revision = '011_rule_premium_strike_iv'
down_revision = '010_rule_last_error'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('sell_put_rules') as batch_op:
        batch_op.add_column(sa.Column('strike_min', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('strike_max', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('max_premium_dollar', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('bid_ask_fill_pct', sa.Float(), nullable=False, server_default='0.5'))
        batch_op.add_column(sa.Column('min_iv_pct', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('max_iv_pct', sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('sell_put_rules') as batch_op:
        batch_op.drop_column('max_iv_pct')
        batch_op.drop_column('min_iv_pct')
        batch_op.drop_column('bid_ask_fill_pct')
        batch_op.drop_column('max_premium_dollar')
        batch_op.drop_column('strike_max')
        batch_op.drop_column('strike_min')
