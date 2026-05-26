"""Add last_error and last_error_at to sell_put_rules

Revision ID: 010_rule_last_error
Revises: 009_app_settings
Create Date: 2026-05-26
"""
from alembic import op
import sqlalchemy as sa

revision = '010_rule_last_error'
down_revision = '009_app_settings'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('sell_put_rules') as batch_op:
        batch_op.add_column(sa.Column('last_error', sa.String(500), nullable=True))
        batch_op.add_column(sa.Column('last_error_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('sell_put_rules') as batch_op:
        batch_op.drop_column('last_error_at')
        batch_op.drop_column('last_error')
