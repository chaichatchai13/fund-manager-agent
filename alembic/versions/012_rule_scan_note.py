"""Add last_scan_note and last_scanned_at to sell_put_rules

Revision ID: 012_rule_scan_note
Revises: 011_rule_premium_strike_iv
Create Date: 2026-06-03
"""
from alembic import op
import sqlalchemy as sa

revision = '012_rule_scan_note'
down_revision = '011_rule_premium_strike_iv'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('sell_put_rules') as batch_op:
        batch_op.add_column(sa.Column('last_scan_note', sa.String(500), nullable=True))
        batch_op.add_column(sa.Column('last_scanned_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('sell_put_rules') as batch_op:
        batch_op.drop_column('last_scanned_at')
        batch_op.drop_column('last_scan_note')
