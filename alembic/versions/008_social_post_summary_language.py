"""Add summary_language column to social_posts

Revision ID: 008_social_post_summary_language
Revises: 007_social_posts_text_columns
Create Date: 2026-05-25
"""
from alembic import op
import sqlalchemy as sa

revision = '008_social_post_summary_language'
down_revision = '007_social_posts_text_columns'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('social_posts') as batch_op:
        batch_op.add_column(sa.Column('summary_language', sa.String(50), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('social_posts') as batch_op:
        batch_op.drop_column('summary_language')
