"""add price_alerts, social_watchlist, social_posts, push_subscriptions tables

Revision ID: 006_alerts_and_social
Revises: 005_schwab_tokens
Create Date: 2026-05-23
"""
from alembic import op
import sqlalchemy as sa

revision = '006_alerts_and_social'
down_revision = '005_schwab_tokens'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('price_alerts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('symbol', sa.String(20), nullable=False, index=True),
        sa.Column('condition', sa.String(20), nullable=False),
        sa.Column('threshold', sa.Float(), nullable=False),
        sa.Column('action', sa.String(30), nullable=False, server_default='notify_and_suggest'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cooldown_minutes', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table('social_watchlist',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('x_handle', sa.String(100), nullable=False, index=True),
        sa.Column('display_name', sa.String(200), nullable=True),
        sa.Column('stocks', sa.JSON(), nullable=False),
        sa.Column('added_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table('social_last_checked',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('x_handle', sa.String(100), nullable=False, index=True),
        sa.Column('stock', sa.String(20), nullable=False),
        sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table('social_posts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('post_id', sa.String(100), nullable=False, unique=True),
        sa.Column('x_handle', sa.String(100), nullable=False, index=True),
        sa.Column('stock', sa.String(20), nullable=False, index=True),
        sa.Column('content', sa.String(4000), nullable=False),
        sa.Column('summary', sa.String(2000), nullable=True),
        sa.Column('image_urls', sa.JSON(), nullable=True),
        sa.Column('referenced_post_id', sa.String(100), nullable=True),
        sa.Column('referenced_content', sa.String(4000), nullable=True),
        sa.Column('posted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table('push_subscriptions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('endpoint', sa.String(500), nullable=False, unique=True),
        sa.Column('keys', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('push_subscriptions')
    op.drop_table('social_posts')
    op.drop_table('social_last_checked')
    op.drop_table('social_watchlist')
    op.drop_table('price_alerts')
