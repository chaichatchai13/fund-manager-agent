"""Widen social_posts content/summary/referenced_content to Text (unlimited)

Revision ID: 007_social_posts_text_columns
Revises: 006_alerts_and_social
Create Date: 2026-05-25
"""
from alembic import op
import sqlalchemy as sa

revision = '007_social_posts_text_columns'
down_revision = '006_alerts_and_social'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('social_posts') as batch_op:
        batch_op.alter_column('content',
                              existing_type=sa.String(4000),
                              type_=sa.Text(),
                              existing_nullable=False)
        batch_op.alter_column('summary',
                              existing_type=sa.String(2000),
                              type_=sa.Text(),
                              existing_nullable=True)
        batch_op.alter_column('referenced_content',
                              existing_type=sa.String(4000),
                              type_=sa.Text(),
                              existing_nullable=True)


def downgrade() -> None:
    with op.batch_alter_table('social_posts') as batch_op:
        batch_op.alter_column('referenced_content',
                              existing_type=sa.Text(),
                              type_=sa.String(4000),
                              existing_nullable=True)
        batch_op.alter_column('summary',
                              existing_type=sa.Text(),
                              type_=sa.String(2000),
                              existing_nullable=True)
        batch_op.alter_column('content',
                              existing_type=sa.Text(),
                              type_=sa.String(4000),
                              existing_nullable=False)
