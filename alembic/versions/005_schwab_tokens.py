"""add schwab_tokens table

Revision ID: 005_schwab_tokens
Revises: 004_itm_roll_columns
Create Date: 2026-05-22
"""
from alembic import op
import sqlalchemy as sa

revision = '005_schwab_tokens'
down_revision = '004_itm_roll_columns'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'schwab_tokens',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('token_encrypted', sa.String(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('schwab_tokens')
