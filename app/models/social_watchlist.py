"""Social intel watchlist — X accounts to monitor per stock."""
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Integer, String, Text, JSON
from app.database import Base


class SocialWatchlist(Base):
    __tablename__ = "social_watchlist"

    id = Column(Integer, primary_key=True)
    x_handle = Column(String(100), nullable=False, index=True)   # without @
    display_name = Column(String(200), nullable=True)
    stocks = Column(JSON, nullable=False, default=list)           # ["TSLA", "NVDA"]
    added_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class SocialLastChecked(Base):
    __tablename__ = "social_last_checked"

    id = Column(Integer, primary_key=True)
    x_handle = Column(String(100), nullable=False, index=True)
    stock = Column(String(20), nullable=False)
    last_checked_at = Column(DateTime(timezone=True), nullable=True)


class SocialPost(Base):
    """Cached posts to avoid re-fetching and support article-style rendering."""
    __tablename__ = "social_posts"

    id = Column(Integer, primary_key=True)
    post_id = Column(String(100), nullable=False, unique=True)    # X post ID
    x_handle = Column(String(100), nullable=False, index=True)
    stock = Column(String(20), nullable=False, index=True)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)                         # AI-generated summary
    image_urls = Column(JSON, nullable=True)                      # list of image URLs
    referenced_post_id = Column(String(100), nullable=True)      # one-level cross-reference
    referenced_content = Column(Text, nullable=True)
    posted_at = Column(DateTime(timezone=True), nullable=False)
    fetched_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
