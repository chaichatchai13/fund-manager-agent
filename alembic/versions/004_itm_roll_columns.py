"""add itm_action, roll_when_dte, roll_target_weeks to sell_put_rules

Revision ID: 004_itm_roll_columns
Revises: 003_premium_and_sizing_modes
Create Date: 2026-05-10
"""
from alembic import op
import sqlalchemy as sa

revision = '004_itm_roll_columns'
down_revision = '003_premium_and_sizing_modes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('sell_put_rules') as batch_op:
        batch_op.add_column(sa.Column('itm_action', sa.String(20), nullable=False, server_default='let_assign'))
        batch_op.add_column(sa.Column('roll_when_dte', sa.Integer(), nullable=False, server_default='7'))
        batch_op.add_column(sa.Column('roll_target_weeks', sa.Integer(), nullable=False, server_default='4'))


def downgrade() -> None:
    with op.batch_alter_table('sell_put_rules') as batch_op:
        batch_op.drop_column('itm_action')
        batch_op.drop_column('roll_when_dte')
        batch_op.drop_column('roll_target_weeks')
