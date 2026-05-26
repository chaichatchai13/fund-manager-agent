"""Create app_settings key/value table

Revision ID: 009_app_settings
Revises: 008_social_post_summary_language
Create Date: 2026-05-25
"""
from alembic import op
import sqlalchemy as sa

revision = '009_app_settings'
down_revision = '008_social_post_summary_language'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'app_settings',
        sa.Column('key', sa.String(100), primary_key=True),
        sa.Column('value', sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('app_settings')
